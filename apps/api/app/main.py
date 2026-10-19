import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis import Redis
from sqlalchemy import text

from app.db import engine
from app.http import RequestProtection
from app.limits import ImportBodyLimit
from app.mappings import router as mappings_router
from app.prices import router as prices_router
from app.rankings import router as rankings_router
from app.routes import router
from app.supply import router as supply_router

logging.basicConfig(level=logging.INFO, format="%(message)s")

app = FastAPI(title="CS2 Market Intelligence API", version="0.1.0")
app.add_middleware(ImportBodyLimit)
app.add_middleware(RequestProtection)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_credentials=False, allow_methods=["GET"], allow_headers=["*"])


@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "cs2-api"}


@app.get("/readyz")
def readyz():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            revisions: set[str] = set(connection.execute(text("SELECT version_num FROM alembic_version")).scalars())
            if revisions != {"0005"}:
                return JSONResponse(status_code=503, content={"status": "unavailable"})
        with Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"), socket_connect_timeout=2, socket_timeout=2) as cache:
            cache.ping()
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ok", "database": "ok", "redis": "ok"}


app.include_router(router)
app.include_router(prices_router)
app.include_router(supply_router)
app.include_router(rankings_router)
app.include_router(mappings_router)
