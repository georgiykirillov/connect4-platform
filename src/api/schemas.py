from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel


class GameStatus(str, Enum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


class PlayerRequest(BaseModel):
    player_id: str


class MoveRequest(BaseModel):
    column: int
    game_id: str = "main"
    player_id: str


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
