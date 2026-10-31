import re
from time import monotonic

from api.tables import Player, TableManager, TableStatus


def test_01_create_table():
    manager = TableManager()
    host = Player(id="player1", username="Alex")

    table = manager.create_table(host)

    assert table.table_id in manager.tables
    assert len(table.table_id) == 6
    assert re.fullmatch(r"[0-9A-F]{6}", table.table_id)
    assert table.host == host
    assert table.guest is None
    assert table.status == TableStatus.WAITING


def test_02_create_table_name():
    manager = TableManager()
    host = Player(id="player1", username="Alex")

    table = manager.create_table(host)

    assert table.name == "Стол игрока Alex"


def test_03_create_multiple_tables():
    manager = TableManager()
    host1 = Player(id="player1", username="Alex")
    host2 = Player(id="player2", username="Max")

    table1 = manager.create_table(host1)
    table2 = manager.create_table(host2)

    assert table1.table_id != table2.table_id
    assert len(manager.tables) == 2


def test_04_get_open_tables():
    manager = TableManager()
    host1 = Player(id="player1", username="Alex")
    host2 = Player(id="player2", username="Max")

    table1 = manager.create_table(host1)
    table2 = manager.create_table(host2)

    open_tables = manager.get_open_tables()

    assert len(open_tables) == 2
    assert table1 in open_tables
    assert table2 in open_tables


def test_05_join_table():
    manager = TableManager()
    host = Player(id="player1", username="Alex")
    guest = Player(id="player2", username="Max")

    table = manager.create_table(host)
    result = manager.join_table(table.table_id, guest)

    assert result is table
    assert table.guest == guest
    assert table.status == TableStatus.IN_PROGRESS


def test_06_random_starting_player():
    manager = TableManager()
    host = Player(id="player1", username="Alex")
    guest = Player(id="player2", username="Max")

    table = manager.create_table(host)
    manager.join_table(table.table_id, guest)

    assert table.game.current_player in (1, 2)


def test_07_cannot_join_full_table():
    manager = TableManager()
    host = Player(id="player1", username="Alex")
    guest1 = Player(id="player2", username="Max")
    guest2 = Player(id="player3", username="Sam")

    table = manager.create_table(host)

    manager.join_table(table.table_id, guest1)
    result = manager.join_table(table.table_id, guest2)

    assert result is None
    assert table.guest == guest1


def test_08_host_cannot_join_own_table():
    manager = TableManager()
    host = Player(id="player1", username="Alex")

    table = manager.create_table(host)
    result = manager.join_table(table.table_id, host)

    assert result is None
    assert table.guest is None
    assert table.status == TableStatus.WAITING


def test_09_join_nonexistent_table():
    manager = TableManager()
    guest = Player(id="player2", username="Max")

    result = manager.join_table("ABC123", guest)

    assert result is None


def test_10_joined_table_is_not_open():
    manager = TableManager()
    host = Player(id="player1", username="Alex")
    guest = Player(id="player2", username="Max")

    table = manager.create_table(host)
    manager.join_table(table.table_id, guest)

    assert table not in manager.get_open_tables()


def test_11_games_are_independent():
    manager = TableManager()
    host1 = Player(id="player1", username="Alex")
    host2 = Player(id="player2", username="Max")

    table1 = manager.create_table(host1)
    table2 = manager.create_table(host2)

    assert table1.game is not table2.game
    assert table1.game.board is not table2.game.board

def test_12_game_move_does_not_affect_another_table():
    manager = TableManager()
    host1 = Player(id="player1", username="Alex")
    host2 = Player(id="player2", username="Max")

    table1 = manager.create_table(host1)
    table2 = manager.create_table(host2)

    table2_board = [
        column.copy() for column in table2.game.board.cells
    ]

    result = table1.game.make_move(0)

    assert result is True
    assert table2.game.board.cells == table2_board

def test_13_expired_waiting_table_is_removed():
    manager = TableManager()
    player = Player(id="1", username="Alex")

    table = manager.create_table(player)
    table.created_at = monotonic() - 301

    manager.remove_expired_tables()

    assert manager.get_table(table.table_id) is None


def test_14_started_game_is_not_removed():
    manager = TableManager()
    host = Player(id="1", username="Alex")
    guest = Player(id="2", username="Max")

    table = manager.create_table(host)
    manager.join_table(table.table_id, guest)
    table.created_at = monotonic() - 301

    manager.remove_expired_tables()

    assert manager.get_table(table.table_id) is table