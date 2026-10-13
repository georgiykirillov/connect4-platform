from engine.board import Board


class Game:
    def __init__(self) -> None:
        self.board = Board()
        self.current_player: int = 1
        self.finished: bool = False
        self.winner: int = 0

    def make_move(self, column: int) -> bool:
        if self.finished:
            return False

        if not self.board.drop_piece(column, self.current_player):
            return False

        if self.board.check_win(self.current_player):
            self.finished = True
            self.winner = self.current_player

        if self.board.is_full():
            self.finished = True

        if self.current_player == 1:
            self.current_player = 2
        else:
            self.current_player = 1

        return True
