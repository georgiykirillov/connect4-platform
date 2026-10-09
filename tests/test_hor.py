from engine.game import Game


def test_horizontal() -> None:
    # 1. Arrange: создаем чистую доску
    game = Game()

    success = game.make_move(column=1)
    assert success is True
    success = game.make_move(column=1)
    assert success is True

    success = game.make_move(column=2)
    assert success is True
    success = game.make_move(column=2)
    assert success is True

    success = game.make_move(column=3)
    assert success is True
    success = game.make_move(column=3)
    assert success is True

    success = game.make_move(column=4)
    assert success is True
    success = game.make_move(column=4)
    assert success is False

    # 3. Assert: ход удался, фишка на строке 0, а строка 1 пустая
    assert game.board.cells[1][0].player == 1
    assert game.board.cells[1][1].player == 2

    assert game.board.cells[2][0].player == 1
    assert game.board.cells[2][1].player == 2

    assert game.board.cells[3][0].player == 1
    assert game.board.cells[3][1].player == 2

    assert game.board.cells[4][0].player == 1
    assert game.board.cells[4][1].player == 0
