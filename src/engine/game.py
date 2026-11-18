from typing import Any, Literal, Self

from engine.board import Board


class Game:
    def __init__(self, width: int = 7, height: int = 6, modifiers: dict | None = None) -> None:
        if modifiers is None:
            modifiers = {}
        self.board = Board(width, height, modifiers)
        self.current_player: Literal[1, 2] = 1
        self.finished: bool = False
        self.winner: Literal[0, 1, 2] = 0
        self.draw_offer: Literal[0, 1, 2] = 0

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

        if self.draw_offer not in (0, self.current_player):
            self.draw_offer = 0

        if self.current_player == 1:
            self.current_player = 2
        else:
            self.current_player = 1

        return True

    def resign(self, player: Literal[1, 2]) -> bool:
        if self.finished:
            return False

        self.finished = True
        self.winner = 2 if player == 1 else 1

        return True

    def offer_draw(self, player: Literal[1, 2]):
        if self.finished:
            return False

        if self.draw_offer != 0:
            return False

        self.draw_offer = player

        return True

    def accept_draw(self, player: Literal[1, 2]):
        if self.finished:
            return False

        if self.draw_offer in (0, player):
            return False

        self.finished = True

        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "board": {
                "width": self.board.width,
                "height": self.board.height,
                "modifiers": self.board.modifiers,
                "cells": [column.copy() for column in self.board.cells],
            },
            "current_player": self.current_player,
            "finished": self.finished,
            "winner": self.winner,
            "draw_offer": self.draw_offer,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        game = cls(data["board"]["width"], data["board"]["height"], data["board"]["modifiers"])
        game.board.cells = [column.copy() for column in data["board"]["cells"]]
        game.current_player = data["current_player"]
        game.finished = data["finished"]
        game.winner = data["winner"]
        game.draw_offer = data["draw_offer"]

        return game
