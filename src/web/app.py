from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from engine.game import Game

app = FastAPI(title="Connect Four")
BASE_DIR = Path(__file__).resolve().parent

game = Game()


class MoveRequest(BaseModel):
    column: int = Field(ge=0, le=6)


def get_state() -> dict[str, object]:
    return {
        "board": game.board.cells,
        "width": game.board.width,
        "height": game.board.height,
        "current_player": game.current_player,
        "finished": game.finished,
        "winner": game.winner,
        "draw": game.finished and game.winner == 0,
    }


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "index.html")


@app.get("/api/state")
def read_state() -> dict[str, object]:
    return get_state()


@app.post("/api/move")
def make_move(request: MoveRequest) -> dict[str, object]:
    if not game.make_move(request.column):
        raise HTTPException(status_code=400, detail="В эту колонку нельзя поставить фишку.")
    return get_state()


@app.post("/api/reset")
def reset_game() -> dict[str, object]:
    global game
    game = Game()
    return get_state()
