import asyncio
from asyncio import Lock
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from api.schemas import (
    BoardState,
    GameMeta,
    GameStateResponse,
    GameStatus,
)
from api.tables import Player, Table, TableManager, TableStatus


async def cleanup_tables() -> None:
    while True:
        await asyncio.sleep(10)
        table_manager.remove_expired_tables()


@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_task = asyncio.create_task(cleanup_tables())

    yield

    cleanup_task.cancel()

    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title="Connect Four",
    lifespan=lifespan,
)
BASE_DIR = Path(__file__).resolve().parent

table_manager = TableManager()
manager_lock = Lock()
table_locks: dict[str, Lock] = {}


class PlayerRequest(BaseModel):
    player_id: str
    username: str = Field(min_length=1, max_length=24)


class MoveRequest(BaseModel):
    player_id: str
    column: int = Field(ge=0, le=6)


def get_table_lock(table_id: str) -> Lock:
    if table_id not in table_locks:
        table_locks[table_id] = Lock()

    return table_locks[table_id]


def get_table_state(table: Table) -> GameStateResponse:
    game = table.game
    width = game.board.width
    height = game.board.height

    cells = [
        [game.board.cells[x][y] for x in range(width)]
        for y in range(height)
    ]

    if table.status == TableStatus.WAITING:
        status = GameStatus.WAITING
    elif not game.finished:
        status = GameStatus.IN_PROGRESS
    elif game.winner in (1, 2):
        status = GameStatus.FINISHED
    else:
        status = GameStatus.DRAW

    return GameStateResponse(
        game=GameMeta(
            status=status,
            current_player=game.current_player,
            winner=game.winner if game.winner in (1, 2) else None,
        ),
        board=BoardState(
            width=width,
            height=height,
            cells=cells,
        ),
        game_id=table.table_id,
        modifiers={},
    )


def serialize_table(table: Table) -> dict:
    return {
        "table_id": table.table_id,
        "name": table.name,
        "host": {
            "id": table.host.id,
            "username": table.host.username,
        },
        "guest": (
            {
                "id": table.guest.id,
                "username": table.guest.username,
            }
            if table.guest is not None
            else None
        ),
        "status": table.status.value,
    }


async def broadcast_state(table: Table) -> None:
    state = get_table_state(table).model_dump(mode="json")
    disconnected: list[str] = []

    for player_id, connection in list(table.connections.items()):
        if not isinstance(connection, WebSocket):
            continue

        try:
            await connection.send_json(
                {
                    "type": "state",
                    "state": state,
                    "player": table.player_numbers.get(player_id),
                }
            )
        except Exception:
            disconnected.append(player_id)

    for player_id in disconnected:
        table.connections.pop(player_id, None)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "index.html")


@app.get("/style.css", include_in_schema=False)
def stylesheet() -> FileResponse:
    return FileResponse(
        BASE_DIR / "style.css",
        media_type="text/css",
    )


@app.get("/script.js", include_in_schema=False)
def javascript() -> FileResponse:
    return FileResponse(
        BASE_DIR / "script.js",
        media_type="text/javascript",
    )


@app.get("/api/tables")
async def get_open_tables() -> list[dict]:
    return [
        serialize_table(table)
        for table in table_manager.get_open_tables()
    ]


@app.post("/api/tables")
async def create_table(request: PlayerRequest) -> dict:
    username = request.username.strip()

    if not username:
        raise HTTPException(
            status_code=422,
            detail="Имя игрока не может быть пустым.",
        )

    async with manager_lock:
        player = Player(
            id=request.player_id,
            username=username,
        )
        table = table_manager.create_table(player)
        table_locks[table.table_id] = Lock()

    return serialize_table(table)


@app.get("/api/tables/{table_id}")
async def get_table(table_id: str) -> dict:
    table = table_manager.get_table(table_id)

    if table is None:
        raise HTTPException(
            status_code=404,
            detail="Стол не найден.",
        )

    return {
        **serialize_table(table),
        "state": get_table_state(table).model_dump(mode="json"),
    }


@app.post("/api/tables/{table_id}/join")
async def join_table(table_id: str, request: PlayerRequest) -> dict:
    username = request.username.strip()

    if not username:
        raise HTTPException(
            status_code=422,
            detail="Имя игрока не может быть пустым.",
        )

    async with manager_lock:
        player = Player(
            id=request.player_id,
            username=username,
        )
        table = table_manager.join_table(table_id, player)

    if table is None:
        raise HTTPException(
            status_code=400,
            detail="Невозможно присоединиться к этому столу.",
        )

    async with get_table_lock(table_id):
        await broadcast_state(table)

    return {
        **serialize_table(table),
        "state": get_table_state(table).model_dump(mode="json"),
        "player": table.player_numbers.get(request.player_id),
    }


@app.post("/api/tables/{table_id}/move")
async def make_move(
    table_id: str,
    request: MoveRequest,
) -> GameStateResponse:
    table = table_manager.get_table(table_id)

    if table is None:
        raise HTTPException(
            status_code=404,
            detail="Стол не найден.",
        )

    async with get_table_lock(table_id):
        player = table.player_numbers.get(request.player_id)

        if player not in (1, 2):
            raise HTTPException(
                status_code=403,
                detail="Ты не являешься игроком этого стола.",
            )

        if table.status != TableStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=400,
                detail="Игра сейчас не идёт.",
            )

        if table.game.current_player != player:
            raise HTTPException(
                status_code=403,
                detail="Сейчас ход другого игрока.",
            )

        if not table.game.make_move(request.column):
            raise HTTPException(
                status_code=400,
                detail="Сюда нельзя поставить фишку.",
            )

        if table.game.finished:
            table.status = TableStatus.FINISHED

        await broadcast_state(table)

        return get_table_state(table)


@app.websocket("/ws/table/{table_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    table_id: str,
    player_id: str,
) -> None:
    table = table_manager.get_table(table_id)

    if table is None or player_id not in table.player_numbers:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    table.connections[player_id] = websocket

    try:
        await websocket.send_json(
            {
                "type": "init",
                "state": get_table_state(table).model_dump(mode="json"),
                "player": table.player_numbers.get(player_id),
            }
        )

        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        pass

    finally:
        if table.connections.get(player_id) is websocket:
            table.connections.pop(player_id, None)
