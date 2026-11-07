import os
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import Credentials, UserOut
from db.db import User, get_db
from db.security import (
    DUMMY_HASH,
    TOKEN_LIFE,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)

COOKIE_NAME = "session"
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "1") == "1"

router = APIRouter(prefix="/api/auth")


def set_session(response: Response, user_id: int) -> None:
    response.set_cookie(
        COOKIE_NAME,
        create_token(user_id),
        max_age=int(TOKEN_LIFE.total_seconds()),
        httponly=True,
        secure=COOKIE_SECURE,
    )


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> User:
    user_id = decode_token(token) if token is not None else None
    user = await db.get(User, user_id) if user_id is not None else None

    if user is None:
        raise HTTPException(status_code=401, detail="Не авторизован.")

    return user


@router.post("/register", response_model=UserOut, status_code=201)
async def register(
    db: Annotated[AsyncSession, Depends(get_db)],
    creds: Credentials,
    response: Response,
):
    user = User(username=creds.username.lower(), password_hash=hash_password(creds.password))
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Имя уже занято.") from None
    set_session(response, user.id)
    return user


@router.post("/login", response_model=UserOut)
async def login(
    db: Annotated[AsyncSession, Depends(get_db)],
    creds: Credentials,
    response: Response,
):
    user = await db.scalar(select(User).where(User.username == creds.username.lower()))
    password_correct = verify_password(creds.password, user.password_hash if user else DUMMY_HASH)

    if user is None or not password_correct:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль.")

    set_session(response, user.id)
    return user


@router.post("/logout", status_code=204)
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)


@router.get("/me", response_model=UserOut)
async def me(response: Response, user: Annotated[User, Depends(get_current_user)]):
    set_session(response, user.id)
    return user
