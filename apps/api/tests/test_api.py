from app.main import app
from fastapi.testclient import TestClient

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


def test_docs_and_openapi():
    assert client.get('/docs').status_code == 200
    assert '/healthz' in client.get('/openapi.json').json()['paths']


def test_readiness_fails_closed(monkeypatch):
    from app import main
    def fail():
        raise RuntimeError('dependency offline')
    monkeypatch.setattr(main.engine, 'connect', fail)
    assert client.get('/readyz').status_code == 503
