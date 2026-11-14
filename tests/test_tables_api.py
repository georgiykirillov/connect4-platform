import pytest
from fastapi.testclient import TestClient

from web.app import app, table_locks, table_manager


@pytest.fixture
def client():
    table_manager.tables.clear()
    table_locks.clear()

    with TestClient(app) as test_client:
        yield test_client


def create_table(client, player_id, username):
    return client.post(
        "/api/tables",
        json={
            "player_id": player_id,
            "username": username,
        },
    )


def join_table(client, table_id, player_id, username):
    return client.post(
        f"/api/tables/{table_id}/join",
        json={
            "player_id": player_id,
            "username": username,
        },
    )


def test_01_create_table(client):
    response = create_table(client, "player1", "Alex")

    assert response.status_code == 200
    assert response.json()["host"]["username"] == "Alex"
    assert response.json()["guest"] is None
    assert response.json()["status"] == "waiting"


def test_02_get_open_tables(client):
    create_table(client, "player1", "Alex")
    create_table(client, "player2", "Max")

    response = client.get("/api/tables")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_03_join_table(client):
    created = create_table(client, "player1", "Alex").json()

    response = join_table(
        client,
        created["table_id"],
        "player2",
        "Max",
    )

    assert response.status_code == 200
    assert response.json()["guest"]["username"] == "Max"
    assert response.json()["status"] == "in_progress"
    assert response.json()["player"] in (1, 2)


def test_04_cannot_join_full_table(client):
    created = create_table(client, "player1", "Alex").json()
    table_id = created["table_id"]

    first_join = join_table(
        client,
        table_id,
        "player2",
        "Max",
    )

    second_join = join_table(
        client,
        table_id,
        "player3",
        "Sam",
    )

    assert first_join.status_code == 200
    assert second_join.status_code == 400


def test_05_get_nonexistent_table(client):
    response = client.get("/api/tables/ABC123")

    assert response.status_code == 404


def test_06_games_are_independent(client):
    first_table = create_table(
        client,
        "player1",
        "Alex",
    ).json()

    second_table = create_table(
        client,
        "player2",
        "Max",
    ).json()

    first_id = first_table["table_id"]
    second_id = second_table["table_id"]

    join_table(client, first_id, "player3", "Sam")
    join_table(client, second_id, "player4", "John")

    first_state = client.get(
        f"/api/tables/{first_id}"
    ).json()["state"]

    second_state = client.get(
        f"/api/tables/{second_id}"
    ).json()["state"]

    current_player = first_state["game"]["current_player"]
    first_guest = client.get(
        f"/api/tables/{first_id}"
    ).json()["guest"]["id"]

    first_join = table_manager.get_table(first_id)
    assert first_join is not None

    if first_join.player_numbers[first_guest] == current_player:
        player_id = first_guest
    else:
        player_id = first_join.host.id

    move_response = client.post(
        f"/api/tables/{first_id}/move",
        json={
            "player_id": player_id,
            "column": 0,
        },
    )

    assert move_response.status_code == 200

    first_state_after = client.get(
        f"/api/tables/{first_id}"
    ).json()["state"]

    second_state_after = client.get(
        f"/api/tables/{second_id}"
    ).json()["state"]

    assert first_state_after["board"]["cells"] != (
        first_state["board"]["cells"]
    )

    assert second_state_after["board"]["cells"] == (
        second_state["board"]["cells"]
    )


def test_07_cannot_move_out_of_turn(client):
    created = create_table(
        client,
        "player1",
        "Alex",
    ).json()

    table_id = created["table_id"]

    join_table(client, table_id, "player2", "Max")

    table = table_manager.get_table(table_id)
    assert table is not None

    current_player = table.game.current_player

    wrong_player_id = (
        table.guest.id
        if table.player_numbers[table.guest.id] != current_player
        else table.host.id
    )

    response = client.post(
        f"/api/tables/{table_id}/move",
        json={
            "player_id": wrong_player_id,
            "column": 0,
        },
    )

    assert response.status_code == 403
