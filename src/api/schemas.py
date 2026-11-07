from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    username: str


class GameStatus(str, Enum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


class MoveRequest(BaseModel):
    column: int
    game_id: str = "main"


class BoardState(BaseModel):
    width: int
    height: int
    cells: list[list[Literal[0, 1, 2]]]
    modifiers: dict[str, Any]


class GameMeta(BaseModel):
    status: GameStatus
    current_player: Literal[1, 2]
    winner: Literal[0, 1, 2]


class GameStateResponse(BaseModel):
    game: GameMeta
    board: BoardState
    game_id: str = "main"
