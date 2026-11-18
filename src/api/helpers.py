from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    BoardState,
    GameList,
    GameMeta,
    GameStateResponse,
    GameStatus,
    GameSummary,
    PlayerOut,
)
from db.db import GameRecord, MoveRecord, User
from engine.game import Game


async def load_player(db: AsyncSession, player_id: int | None) -> PlayerOut | None:
    if player_id is None:
        return None

    user = await db.get(User, player_id)
    if user is None:
        return None

    return PlayerOut(id=player_id, username=user.username)


def get_board(record: GameRecord) -> BoardState:
    board = Game.from_dict(record.game_data).board
    return BoardState(
        width=board.width, height=board.height, modifiers=board.modifiers, cells=board.cells
    )


def get_status(record: GameRecord) -> GameStatus:
    game = Game.from_dict(record.game_data)
    if record.player2_id is None:
        return GameStatus.WAITING
    if game.finished:
        return GameStatus.FINISHED
    return GameStatus.IN_PROGRESS


def get_meta(record: GameRecord) -> GameMeta:
    game = Game.from_dict(record.game_data)
    return GameMeta(
        status=get_status(record),
        current_player=game.current_player,
        winner=game.winner,
        draw_offer=game.draw_offer,
    )


async def load_summary(db: AsyncSession, record: GameRecord) -> GameSummary:
    return GameSummary(
        game_id=record.id,
        game_meta=get_meta(record),
        board=get_board(record),
        player1=await load_player(db, record.player1_id),
        player2=await load_player(db, record.player2_id),
    )


async def load_moves(db: AsyncSession, game_id: int) -> list[int]:
    result = await db.scalars(
        select(MoveRecord.column)
        .where(MoveRecord.game_id == game_id)
        .order_by(MoveRecord.move_number)
    )
    return list(result)


async def load_state(db: AsyncSession, record: GameRecord) -> GameStateResponse:
    moves = await load_moves(db, record.id)
    return GameStateResponse(**(await load_summary(db, record)).model_dump(), moves=moves)


async def load_list(db: AsyncSession, user_id: int) -> GameList:
    waiting_records = (
        await db.scalars(
            select(GameRecord)
            .where(GameRecord.player2_id.is_(None))
            .order_by(GameRecord.creation_time.desc())
            .limit(50)
        )
    ).all()

    my_records = (
        await db.scalars(
            select(GameRecord)
            .where(or_(GameRecord.player1_id == user_id, GameRecord.player2_id == user_id))
            .order_by(GameRecord.creation_time.desc())
            .limit(50)
        )
    ).all()

    return GameList(
        waiting_games=[await load_summary(db, record) for record in waiting_records],
        my_games=[await load_summary(db, record) for record in my_records],
    )
