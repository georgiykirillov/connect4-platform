from enum import Enum

from typing import Literal

from pydantic import BaseModel, Field


class GameStatus(str, Enum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"
    DRAW = "draw"


class MoveRequest(BaseModel):
    column: int = Field(ge=0, le=6)
    game_id: str = "main"
    player_id: str


class BoardState(BaseModel):
    width: int = 7
    height: int = 6
    cells: list[list[Literal[0, 1, 2]]]


class GameMeta(BaseModel):
    status: GameStatus
    current_player: Literal[1, 2]
    winner: Literal[1, 2] | None


class GameStateResponse(BaseModel):
    game: GameMeta
    board: BoardState
    game_id: str = "main"
    modifiers: dict[str, int] = Field(default_factory=dict[str, int])
