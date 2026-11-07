import os
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

hasher = PasswordHash.recommended()

SECRET_KEY = os.environ["SECRET_KEY"]
TOKEN_LIFE = timedelta(days=30)
DUMMY_HASH = hasher.hash("correcthorsebatterystaple")


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return hasher.verify(password, hashed)


def create_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + TOKEN_LIFE
    return jwt.encode({"sub": str(user_id), "exp": exp}, SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
