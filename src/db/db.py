import os
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy import JSON, DateTime, ForeignKey, SmallInteger, String, UniqueConstraint, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

engine = create_async_engine(os.environ["DATABASE_URL"])
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    creation_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class GameRecord(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    player1_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    player2_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    game_data: Mapped[dict] = mapped_column(JSON)
    creation_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MoveRecord(Base):
    __tablename__ = "moves"
    __table_args__ = (UniqueConstraint("game_id", "move_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), index=True)
    move_number: Mapped[int]
    player: Mapped[int] = mapped_column(SmallInteger)
    column: Mapped[int] = mapped_column(SmallInteger)
    move_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


DB = Annotated[AsyncSession, Depends(get_db)]
