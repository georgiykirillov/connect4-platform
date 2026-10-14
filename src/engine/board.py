class Board:
    def __init__(self, width: int = 7, height: int = 6) -> None:
        self.width = width
        self.height = height

        self.cells = [[0 for _ in range(height)] for _ in range(width)]

        self.vertical_walls: set[tuple[int, int]] = set()
        self.horizontal_walls: set[tuple[int, int]] = set()

    def drop_piece(self, column: int, player: int) -> bool:
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
