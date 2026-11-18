from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers import (
    get_status,
    load_list,
    load_moves,
    load_state,
)
from api.schemas import (
    GameList,
    GameStateResponse,
    GameStatus,
    MoveRequest,
)
from db.db import DB, GameRecord, MoveRecord, SessionLocal, User
from db.security import decode_token
from engine.game import Game
from web.auth import COOKIE_NAME, CurrentUser

ALLOWED_ORIGINS = {"http://localhost:8000"}

games_router = APIRouter(prefix="/api/games")
ws_router = APIRouter()

connections: dict[int, set[WebSocket]] = {}


async def load_record(db: AsyncSession, game_id: int, lock: bool = False) -> GameRecord:
    query = select(GameRecord).where(GameRecord.id == game_id)
    if lock:
        query = query.with_for_update()

    record = await db.scalar(query)
    if record is None:
        raise HTTPException(status_code=404, detail="Игра не найдена.")

    return record


def get_seat(record: GameRecord, user_id: int) -> Literal[1, 2] | None:
    if record.player1_id == user_id:
        return 1
    if record.player2_id == user_id:
        return 2
    return None


async def load_active_game(db: AsyncSession, user_id: int) -> GameRecord | None:
    return await db.scalar(
        select(GameRecord).where(
            GameRecord.finished_time.is_(None),
            or_(GameRecord.player1_id == user_id, GameRecord.player2_id == user_id),
        )
    )


async def load_running(
    db: AsyncSession, game_id: int, user_id: int
) -> tuple[GameRecord, Game, Literal[1, 2]]:
    record = await load_record(db, game_id, lock=True)
    game = Game.from_dict(record.game_data)
    seat = get_seat(record, user_id)
    status = get_status(record)

    if seat is None:
        raise HTTPException(status_code=403, detail="Вы не участвуете в этой игре.")
    if status == GameStatus.WAITING:
        raise HTTPException(status_code=400, detail="Ожидание второго игрока.")
    if status == GameStatus.FINISHED:
        raise HTTPException(status_code=400, detail="Игра завершена.")

    return record, game, seat


async def broadcast(game_id: int, state: GameStateResponse) -> None:
    payload = {"type": "state", "state": state.model_dump(mode="json")}
    for websocket in connections.get(game_id, set()):
        try:
            await websocket.send_json(payload)
        except Exception:
            connections.get(game_id, set()).discard(websocket)


async def save_state(db: AsyncSession, record: GameRecord, game: Game) -> GameStateResponse:
    record.game_data = game.to_dict()
    if game.finished:
        record.finished_time = datetime.now(UTC)

    await db.commit()

    state = await load_state(db, record)
    await broadcast(record.id, state)
    return state


async def lock_user(db: AsyncSession, user_id: int) -> None:
    await db.execute(select(User.id).where(User.id == user_id).with_for_update())


@games_router.post("", response_model=GameStateResponse)
async def create_game(db: DB, user: CurrentUser):
    await lock_user(db, user.id)

    record = await load_active_game(db, user.id)
    if record is None:
        record = GameRecord(player1_id=user.id, game_data=Game().to_dict())
        db.add(record)
        await db.commit()

    return await load_state(db, record)


@games_router.get("", response_model=GameList)
async def list_games(db: DB, user: CurrentUser):
    return await load_list(db, user.id)


@games_router.get("/{game_id}", response_model=GameStateResponse)
async def read_game(db: DB, user: CurrentUser, game_id: int):
    return await load_state(db, await load_record(db, game_id))


@games_router.post("/{game_id}/join", response_model=GameStateResponse)
async def join_game(db: DB, user: CurrentUser, game_id: int):
    await lock_user(db, user.id)

    record = await load_record(db, game_id, lock=True)

    if record.player1_id == user.id:
        raise HTTPException(status_code=400, detail="Нельзя играть против себя.")
    if record.player2_id is not None:
        raise HTTPException(
            status_code=409, detail="Эта комната уже заполнена, вы можете наблюдать."
        )
    if await load_active_game(db, user.id) is not None:
        raise HTTPException(status_code=409, detail="Сначала закончите текущую игру.")

    record.player2_id = user.id
    await db.commit()

    state = await load_state(db, record)
    await broadcast(game_id, state)
    return state


@games_router.post("/{game_id}/move", response_model=GameStateResponse)
async def make_move(db: DB, user: CurrentUser, game_id: int, request: MoveRequest):
    record, game, seat = await load_running(db, game_id, user.id)

    if game.current_player != seat:
        raise HTTPException(status_code=403, detail="Сейчас ход другого игрока.")
    if not game.make_move(request.column):
        raise HTTPException(status_code=400, detail="Сюда нельзя поставить фишку.")

    moves = await load_moves(db, game_id)
    db.add(
        MoveRecord(game_id=game_id, move_number=len(moves) + 1, player=seat, column=request.column)
    )
    return await save_state(db, record, game)


@games_router.post("/{game_id}/resign", response_model=GameStateResponse)
async def resign_game(db: DB, user: CurrentUser, game_id: int):
    record, game, seat = await load_running(db, game_id, user.id)

    game.resign(seat)
    return await save_state(db, record, game)


@games_router.post("/{game_id}/draw", response_model=GameStateResponse)
async def offer_draw(db: DB, user: CurrentUser, game_id: int):
    record, game, seat = await load_running(db, game_id, user.id)

    if game.draw_offer == seat:
        raise HTTPException(status_code=409, detail="Вы уже предложили ничью.")
    if game.draw_offer != 0:
        raise HTTPException(status_code=409, detail="Соперник уже предложил ничью, прими её.")

    game.offer_draw(seat)
    return await save_state(db, record, game)


@games_router.post("/{game_id}/draw/accept", response_model=GameStateResponse)
async def accept_draw(db: DB, user: CurrentUser, game_id: int):
    record, game, seat = await load_running(db, game_id, user.id)

    if game.draw_offer in (0, seat):
        raise HTTPException(status_code=409, detail="Соперник не предлагал ничью.")

    game.accept_draw(seat)
    return await save_state(db, record, game)


@games_router.delete("/{game_id}", status_code=204)
async def cancel_game(db: DB, user: CurrentUser, game_id: int):
    record = await load_record(db, game_id, lock=True)
    status = get_status(record)

    if record.player1_id != user.id:
        raise HTTPException(status_code=403, detail="Отменить можно только свою игру.")
    if status != GameStatus.IN_PROGRESS:
        raise HTTPException(status_code=409, detail="Игра уже началась.")

    await db.delete(record)
    await db.commit()


@ws_router.websocket("/ws/games/{game_id}")
async def game_ws(websocket: WebSocket, game_id: int):
    user_id = decode_token(websocket.cookies.get(COOKIE_NAME, ""))

    if user_id is None or websocket.headers.get("origin") not in ALLOWED_ORIGINS:
        await websocket.close(code=4401)
        return

    await websocket.accept()

    try:
        connections.setdefault(game_id, set()).add(websocket)

        async with SessionLocal() as db:
            record = await db.get(GameRecord, game_id)

            if record is None:
                await websocket.close(code=4404)
                return

            state = await load_state(db, record)

        await websocket.send_json({"type": "init", "state": state.model_dump(mode="json")})

        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        pass

    finally:
        group = connections.get(game_id)
        if group is not None:
            group.discard(websocket)
            if not group:
                connections.pop(game_id)
