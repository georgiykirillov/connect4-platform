from engine.game import Game


def test_smoke() -> None:
    """Временный тест-заглушка, чтобы проверить работу CI."""
    game = Game()
    success = game.make_move(column=3)
    assert success is True
    assert game.board.cells[3][0].player == 1
    assert game.board.cells[3][1].player == 0
