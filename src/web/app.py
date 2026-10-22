from asyncio import Lock
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel

from api.schemas import (
    BoardState,
    Field,
    GameMeta,
    GameStateResponse,
    GameStatus,
    MoveRequest,
)
from engine.game import Game
from typing import Optional
app = FastAPI(title="Connect Four")
BASE_DIR = Path(__file__).resolve().parent

game = Game()
connections: dict[WebSocket, str] = {}
players: dict[str, int] = {}
game_lock = Lock()


#class MoveRequest(BaseModel):
#    column: int = Field(ge=0, le=6)
class PlayerRequest(BaseModel):
    player_id: str


def assign_player(player_id: str) -> Optional[int]:
    if player_id in players:
        return players[player_id]

    occupied = set(players.values())

    for number in (1, 2):
        if number not in occupied:
            players[player_id] = number
            return number

    return None


def get_state() -> GameStateResponse:
    width = game.board.width
    height = game.board.height

    cells = [
        [game.board.cells[x][y] for x in range(width)]
        for y in range(height)
    ]

    if not game.finished:
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
        board=BoardState(width=width, height=height, cells=cells),
        game_id="main",
        modifiers={},
    )


async def broadcast_state() -> None:
    state = get_state().model_dump(mode="json")
    disconnected = set()
    Field(ge=0, lt=game.board.width)

    for connection, player_id in list(connections.items()):
        try:
            await connection.send_json({
                "type": "state",
                "state": state,
                "player": players.get(player_id),
            })
        except Exception:
            disconnected.add(connection)

    for connection in disconnected:
        connections.pop(connection, None)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "index.html")


@app.get("/style.css", include_in_schema=False)
def stylesheet() -> FileResponse:
    return FileResponse(BASE_DIR / "style.css", media_type="text/css")


@app.get("/script.js", include_in_schema=False)
def javascript() -> FileResponse:
    return FileResponse(BASE_DIR / "script.js", media_type="text/javascript")


@app.get("/api/state", response_model=GameStateResponse)
async def read_state() -> GameStateResponse:
    return get_state()


@app.post("/api/move", response_model=GameStateResponse)
async def make_move(request: MoveRequest) -> GameStateResponse:
    async with game_lock:
        if request.game_id != "main":
            raise HTTPException(status_code=404, detail="Игра не найдена.")

        player = players.get(request.player_id)

        if player not in (1, 2):
            raise HTTPException(
                status_code=403,
                detail="Ты не занял место игрока.",
            )

        if game.finished:
            raise HTTPException(status_code=400, detail="Игра уже завершена.")

        if game.current_player != player:
            raise HTTPException(
                status_code=403,
                detail="Сейчас ход другого игрока.",
            )

        if not game.make_move(request.column):
            raise HTTPException(status_code=400, detail="Сюда нельзя поставить фишку.")

        await broadcast_state()
        return get_state()


@app.post("/api/reset", response_model=GameStateResponse)
async def reset_game(request: PlayerRequest) -> GameStateResponse:
    global game

    async with game_lock:
        if players.get(request.player_id) != 1:
            raise HTTPException(
                status_code=403,
                detail="Начать новую игру может только игрок 1.",
            )

        game = Game()
        await broadcast_state()
        return get_state()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, player_id: str) -> None:
    await websocket.accept()
    player = assign_player(player_id)
    connections[websocket] = player_id

    try:
        await websocket.send_json({
            "type": "init",
            "state": get_state().model_dump(mode="json"),
            "player": player,
        })

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        connections.pop(websocket, None)
