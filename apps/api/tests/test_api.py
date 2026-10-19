from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/healthz").json()["status"] == "ok"


def test_no_fabricated_prices():
    result = client.get("/v1/items/example/prices").json()
    assert result["status"] == "unavailable"
    assert result["series"] == []


def test_supply_not_fake_zero():
    result = client.get("/v1/items/example/supply").json()
    assert result["status"] == "unavailable"
    assert result["series"] == []
