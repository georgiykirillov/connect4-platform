class Cell:
    def __init__(self, player: int = 0) -> None:
        self.player = player


class Board:
    def __init__(self, width: int = 7, height: int = 6) -> None:
        self.width = width
        self.height = height

        self.cells = [[Cell() for _ in range(height)] for _ in range(width)]

        self.vertical_walls: set[tuple[int, int]] = set()
        self.horizontal_walls: set[tuple[int, int]] = set()

    def drop_piece(self, column: int, player: int) -> bool:
        if column < 0 or column >= self.width:
            return False

        for y in range(self.height):
            if self.cells[column][y].player == 0:
                self.cells[column][y].player = player
                return True

        return False

    def is_full(self) -> bool:
        for x in range(self.width):
            if self.cells[x][self.height - 1].player == 0:
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
                if self.cells[x][y].player != player:
                    continue

                for dx, dy in directions:
                    count = 0

                    for i in range(4):
                        nx = x + dx * i
                        ny = y + dy * i

                        if (
                            0 <= nx < self.width
                            and 0 <= ny < self.height
                            and self.cells[nx][ny].player == player
                        ):
                            count += 1
                        else:
                            break

                    if count == 4:
                        return True

        return False
