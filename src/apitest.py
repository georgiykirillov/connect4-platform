
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from engine.game import Game

app = FastAPI()


class Move(BaseModel):
    column: int


@app.get("/", response_class=HTMLResponse)
async def hello():
    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Connect Four</title>
    </head>
    <body>
        <h1>Connect Four</h1>

        <div>
            <button onclick="makeMove(0)">1</button>
            <button onclick="makeMove(1)">2</button>
            <button onclick="makeMove(2)">3</button>
            <button onclick="makeMove(3)">4</button>
            <button onclick="makeMove(4)">5</button>
            <button onclick="makeMove(5)">6</button>
            <button onclick="makeMove(6)">7</button>
        </div>

        <p id="status">Нажми на номер колонки.</p>

        <script>
            async function makeMove(column) {
                const response = await fetch("/api/move", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        column: column
                    })
                });

                const data = await response.json();

                document.getElementById("status").textContent = data.message;
            }
        </script>
    </body>
    </html>
    """


@app.post("/api/move")
async def make_move(move: Move):
    print(f"Получен ход в колонку {move.column}")
    game = Game()
    game.make_move(move.column)
    return {"message": f"Сервер получил ход в колонку {move.column + 1}"}
