from engine.game import Game


def test_diag_down() -> None:
    game = Game()

    success = game.make_move(column=4)
    assert success
    success = game.make_move(column=3)
    assert success
    success = game.make_move(column=3)
    assert success
    success = game.make_move(column=2)
    assert success
    success = game.make_move(column=2)
    assert success
    success = game.make_move(column=1)
    assert success
    success = game.make_move(column=2)
    assert success
    success = game.make_move(column=1)
    assert success
    success = game.make_move(column=1)
    assert success
    success = game.make_move(column=6)
    assert success
    success = game.make_move(column=1)
    assert success
    success = game.make_move(column=6)
    assert not success

    player_1 = [(4, 0), (3, 1), (2, 1), (2, 2), (1, 2), (1, 3)]
    player_2 = [(3, 0), (2, 0), (1, 0), (1, 1), (6, 0)]
    for x in range(game.board.width):
        for y in range(game.board.height):
            if (x, y) in player_1:
                assert game.board.cells[x][y] == 1
            elif (x, y) in player_2:
                assert game.board.cells[x][y] == 2
            else:
                assert game.board.cells[x][y] == 0

    assert game.finished
    assert game.winner == 1
