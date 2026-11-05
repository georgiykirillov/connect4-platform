from typing import Literal


class Board:
    def __init__(self, width: int, height: int, modifiers: dict) -> None:
        self.width = width
        self.height = height
        self.modifiers = modifiers
        self.cells: list[list[Literal[0, 1, 2]]] = [
            [0 for _ in range(height)] for _ in range(width)
        ]

    def drop_piece(self, column: int, player: Literal[1, 2]) -> bool:
        if column < 0 or column >= self.width:
            return False

        for y in range(self.height):
            if self.cells[column][y] == 0:
                self.cells[column][y] = player
                return True

        return False

    def is_full(self) -> bool:
        for x in range(self.width):
            if self.cells[x][self.height - 1] == 0:
                return False

        return True

    def check_win(self, player: int) -> bool:
        directions = [
            (1, 0),
            (0, 1),
            (1, 1),
            (1, -1),
        ]

        for x in range(self.width):
            for y in range(self.height):
                if self.cells[x][y] != player:
                    continue

                for dx, dy in directions:
                    count = 0

                    for i in range(1, 4):
                        nx = x + dx * i
                        ny = y + dy * i

                        if (
                            nx < self.width
                            and 0 <= ny < self.height
                            and self.cells[nx][ny] == player
                        ):
                            count += 1
                        else:
                            break

                    if count == 3:
                        return True

        return False
