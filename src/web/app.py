from asyncio import Lock
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from api.schemas import (
    BoardState,
    GameMeta,
    GameStateResponse,
    GameStatus,
    MoveRequest,
    PlayerRequest,
)
from engine.game import Game

app = FastAPI(title="Connect Four")
BASE_DIR = Path(__file__).resolve().parent

game = Game()
connections: dict[WebSocket, str] = {}
players: dict[str, int] = {}
join_queue: dict[str, bool] = {}
game_lock = Lock()


def assign_player(player_id: str) -> int | None:
    if player_id in players:
        return players[player_id]

    for number in (1, 2):
        if number not in players.values():
            players[player_id] = number
            return number

    if player_id not in join_queue:
        join_queue[player_id] = True

    return None


def get_state() -> GameStateResponse:
    if not game.finished:
        status = GameStatus.IN_PROGRESS
    else:
        status = GameStatus.FINISHED

    return GameStateResponse(
        game=GameMeta(
            status=status,
            current_player=game.current_player,
            winner=game.winner,
        ),
        board=BoardState(
            width=game.board.width,
            height=game.board.height,
            cells=game.board.cells,
            modifiers=game.board.modifiers,
        ),
        game_id="main",
    )


async def broadcast_state() -> None:
    for websocket, player_id in list(connections.items()):
        try:
            await websocket.send_json(
                {
                    "type": "state",
                    "state": get_state().model_dump(mode="json"),
                    "player": players.get(player_id),
                }
            )

        except Exception:
            pass


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


@app.get("/api/state", response_model=GameStateResponse)
async def read_state() -> GameStateResponse:
    return get_state()


@app.post("/api/move", response_model=GameStateResponse)
async def make_move(request: MoveRequest) -> GameStateResponse:
    async with game_lock:
        if request.game_id != "main":
            raise HTTPException(
                status_code=404,
                detail="Игра не найдена.",
            )

        player = players.get(request.player_id)

        if player not in (1, 2):
            raise HTTPException(
                status_code=403,
                detail="Ты не занял место игрока.",
            )

        if game.finished:
            raise HTTPException(
                status_code=400,
                detail="Игра уже завершена.",
            )

        if game.current_player != player:
            raise HTTPException(
                status_code=403,
                detail="Сейчас ход другого игрока.",
            )

        if not game.make_move(request.column):
            raise HTTPException(
                status_code=400,
                detail="Сюда нельзя поставить фишку.",
            )

        await broadcast_state()
        return get_state()


@app.post("/api/reset", response_model=GameStateResponse)
async def reset_game(request: PlayerRequest) -> GameStateResponse:
    global game

    async with game_lock:
        if players.get(request.player_id) not in (1, 2):
            raise HTTPException(
                status_code=403,
                detail="Начать новую игру может игрок за столом.",
            )

        game = Game()

        await broadcast_state()
        return get_state()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, player_id: str) -> None:
    await websocket.accept()

    async with game_lock:
        player = assign_player(player_id)
        connections[websocket] = player_id

    if player in (1, 2):
        await broadcast_state()

    try:
        await websocket.send_json(
            {
                "type": "init",
                "state": get_state().model_dump(mode="json"),
                "player": player,
            }
        )

        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        async with game_lock:
            connections.pop(websocket, None)

            if players[player_id] in (1, 2):
                await reset_game(PlayerRequest(player_id=player_id))
            else:
                join_queue.pop(player_id, None)

            players.pop(player_id, None)

            if len(join_queue) > 0:
                next_player_id = next(iter(join_queue))
                assign_player(next_player_id)
                join_queue.pop(next_player_id, None)

    finally:
        await broadcast_state()
