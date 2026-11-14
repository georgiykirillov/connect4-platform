from dataclasses import dataclass, field
from enum import Enum
from time import monotonic
from uuid import uuid4

from engine.game import Game


class TableStatus(str, Enum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


@dataclass
class Player:
    id: str
    username: str


@dataclass
class Table:
    table_id: str
    host: Player
    game: Game
    created_at: float = field(default_factory=monotonic)
    guest: Player | None = None
    player_numbers: dict[str, int] = field(default_factory=dict)
    status: TableStatus = TableStatus.WAITING
    connections: dict[str, object] = field(default_factory=dict)
    rematch_votes: set[str] = field(default_factory=set)

    @property
    def name(self) -> str:
        return f"Стол игрока {self.host.username}"


class TableManager:
    def __init__(self) -> None:
        self.tables: dict[str, Table] = {}

    def create_table(self, host: Player) -> Table:
        table_id = uuid4().hex[:6].upper()

        while table_id in self.tables:
            table_id = uuid4().hex[:6].upper()

        table = Table(
            table_id=table_id,
            host=host,
            game=Game(),
            player_numbers={host.id: 1},
        )

        self.tables[table_id] = table
        return table

    def get_open_tables(self) -> list[Table]:
        return [
            table
            for table in self.tables.values()
            if table.status == TableStatus.WAITING
        ]

    def get_table(self, table_id: str) -> Table | None:
        return self.tables.get(table_id)

    def join_table(self, table_id: str, guest: Player) -> Table | None:
        table = self.get_table(table_id)

        if table is None:
            return None

        if table.status != TableStatus.WAITING:
            return None

        if guest.id == table.host.id:
            return None

        starting_player = uuid4().int % 2 + 1

        table.guest = guest
        table.game = Game(starting_player=starting_player)

        table.player_numbers = {
            table.host.id: 1 if starting_player == 1 else 2,
            guest.id: 2 if starting_player == 1 else 1,
        }

        table.status = TableStatus.IN_PROGRESS

        return table
    def remove_expired_tables(self) -> None:
        now = monotonic()

        expired_tables = [
            table_id
            for table_id, table in self.tables.items()
            if (
                table.status == TableStatus.WAITING
                and now - table.created_at >= 300
            )
        ]

        for table_id in expired_tables:
            del self.tables[table_id]