import os

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from redis import Redis
from sqlalchemy import text

from app.db import engine

app = FastAPI(title="CS2 Market Intelligence API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_credentials=False, allow_methods=["GET"], allow_headers=["*"])


class UnavailableSeries(BaseModel):
    status: str = "unavailable"
    series: list = []
    reason: str = "尚未接入经过授权且可核实的数据源"


@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "cs2-api"}


@app.get("/readyz")
def readyz():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            connection.execute(text("SELECT version_num FROM alembic_version"))
        with Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"), socket_connect_timeout=2, socket_timeout=2) as cache:
            cache.ping()
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ok", "database": "ok", "redis": "ok"}


@app.get("/v1/items")
def list_items(query: str = "", category: str | None = None, limit: int = Query(20, ge=1, le=100)):
    return {"items": [], "next_cursor": None, "status": "catalog_not_imported"}


@app.get("/v1/items/{item_id}/prices", response_model=UnavailableSeries)
def prices(item_id: str):
    return UnavailableSeries()


@app.get("/v1/items/{item_id}/supply", response_model=UnavailableSeries)
def supply(item_id: str):
    return UnavailableSeries(reason="尚无可以核实的存世量数据；在售数量不等于总存世量")
