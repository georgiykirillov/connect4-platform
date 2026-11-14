from engine.board import Board


class Game:
    def __init__(self, starting_player: int = 1) -> None:
        if starting_player not in (1, 2):
            raise ValueError("Starting player must be 1 or 2.")

        self.board = Board()
        self.current_player: int = starting_player
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