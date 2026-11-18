from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from db.db import Base, engine
from web.auth import auth_router
from web.tables import games_router, ws_router


@asynccontextmanager
async def lifespan(app):
    async with engine.begin() as con:
        await con.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Connect Four", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(games_router)
app.include_router(ws_router)

BASE_DIR = Path(__file__).resolve().parent


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "index.html")


@app.get("/style.css", include_in_schema=False)
def stylesheet() -> FileResponse:
    return FileResponse(
        BASE_DIR / "style.css",
        media_type="text/css",
    )


@app.get("/script.js", include_in_schema=False)
def javascript() -> FileResponse:
    return FileResponse(
        BASE_DIR / "script.js",
        media_type="text/javascript",
    )
