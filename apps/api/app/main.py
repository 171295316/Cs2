from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
    # Liveness-only for now; database readiness must be added in P0 follow-up.
    return {"status": "ok", "db_check": "not_implemented"}


@app.get("/v1/items")
def list_items(query: str = "", category: str | None = None, limit: int = Query(20, ge=1, le=100)):
    return {"items": [], "next_cursor": None, "status": "catalog_not_imported"}


@app.get("/v1/items/{item_id}/prices", response_model=UnavailableSeries)
def prices(item_id: str):
    return UnavailableSeries()


@app.get("/v1/items/{item_id}/supply", response_model=UnavailableSeries)
def supply(item_id: str):
    return UnavailableSeries(reason="尚无可以核实的存世量数据；在售数量不等于总存世量")
