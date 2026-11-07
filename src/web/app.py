from asyncio import Lock
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from api.schemas import (
    BoardState,
    GameMeta,
    GameStateResponse,
    GameStatus,
    MoveRequest,
)
from db.db import Base, User, engine
from db.security import decode_token
from engine.game import Game
from web.auth import COOKIE_NAME, get_current_user, router


@asynccontextmanager
async def lifespan(app):
    async with engine.begin() as con:
        await con.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Connect Four", lifespan=lifespan)
app.include_router(router)
BASE_DIR = Path(__file__).resolve().parent
ALLOWED_ORIGINS = {"http://localhost:8000"}

game = Game()
connections: dict[WebSocket, int] = {}
players: dict[int, int] = {}
join_queue: dict[int, bool] = {}
game_lock = Lock()


def assign_player(user_id: int) -> int | None:
    if user_id in players:
        return players[user_id]

    for number in (1, 2):
        if number not in players.values():
            players[user_id] = number
            return number

    if user_id not in join_queue:
        join_queue[user_id] = True

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
    for websocket, user_id in list(connections.items()):
        try:
            await websocket.send_json(
                {
                    "type": "state",
                    "state": get_state().model_dump(mode="json"),
                    "player": players.get(user_id),
                }
            )

        except Exception:
            pass


def reset() -> None:
    global game
    game = Game()


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
async def make_move(
    request: MoveRequest, user: Annotated[User, Depends(get_current_user)]
) -> GameStateResponse:
    async with game_lock:
        if request.game_id != "main":
            raise HTTPException(
                status_code=404,
                detail="Игра не найдена.",
            )

        player = players.get(user.id)

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
async def reset_game(user: Annotated[User, Depends(get_current_user)]) -> GameStateResponse:
    async with game_lock:
        if players.get(user.id) not in (1, 2):
            raise HTTPException(
                status_code=403,
                detail="Начать новую игру может только игрок за столом.",
            )

        reset()

        await broadcast_state()
        return get_state()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    user_id = decode_token(websocket.cookies.get(COOKIE_NAME, ""))

    if user_id is None or websocket.headers.get("origin") not in ALLOWED_ORIGINS:
        await websocket.close(code=4401)
        return

    await websocket.accept()

    async with game_lock:
        player = assign_player(user_id)
        connections[websocket] = user_id

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

            if user_id not in connections.values():
                if players.get(user_id) in (1, 2):
                    reset()
                else:
                    join_queue.pop(user_id, None)

                players.pop(user_id, None)

                if join_queue:
                    next_user_id = next(iter(join_queue))
                    assign_player(next_user_id)
                    join_queue.pop(next_user_id, None)

    finally:
        await broadcast_state()
