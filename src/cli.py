from engine.board import Board
from engine.game import Game


def render_board(board: Board) -> None:
    """Функция отрисовки поля в консоли (перенесена из board.py)."""
    print()

    for y in range(board.height - 1, -1, -1):
        for x in range(board.width):
            cell = board.cells[x][y]

            if cell == 0:
                symbol = "."
            elif cell == 1:
                symbol = "X"
            else:
                symbol = "O"

            print(symbol, end=("   " if x < board.width - 1 else "\n"))

        print()

    for x in range(board.width):
        print(f"{x + 1}   ", end="")

    print()


def main() -> None:
    game = Game()

    print("CONNECT FOUR")
    print(f"Введите номер колонки от 1 до {game.board.width}.")
    print("Игрок 1 — X")
    print("Игрок 2 — O")

    while not game.finished:
        render_board(game.board)

        print()
        print(f"Ход игрока {game.current_player}")

        try:
            column = int(input("Колонка: ")) - 1
        except ValueError:
            print(f"Введите целое число от 1 до {game.board.width}.")
            continue

        if not game.make_move(column):
            print("Нельзя поставить фишку в эту колонку.")
            continue

    render_board(game.board)

    print()

    if game.winner != 0:
        print(f"Игрок {game.winner} победил!")
    else:
        print("Ничья!")


if __name__ == "__main__":
    main()
