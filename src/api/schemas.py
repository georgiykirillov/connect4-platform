from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    username: str


class PlayerOut(BaseModel):
    id: int
    username: str


class MoveRequest(BaseModel):
    column: int


class BoardState(BaseModel):
    width: int
    height: int
    modifiers: dict[str, Any]
    cells: list[list[Literal[0, 1, 2]]]


class GameStatus(str, Enum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


class GameMeta(BaseModel):
    status: GameStatus
    current_player: Literal[1, 2]
    winner: Literal[0, 1, 2]
    draw_offer: Literal[0, 1, 2]


class GameSummary(BaseModel):
    game_id: int
    game_meta: GameMeta
    board: BoardState
    player1: PlayerOut | None
    player2: PlayerOut | None


class GameStateResponse(GameSummary):
    moves: list[int]


class GameList(BaseModel):
    waiting_games: list[GameSummary]
    my_games: list[GameSummary]
