from datetime import datetime, timedelta, timezone

from app.http import RequestProtection
from app.main import app
from app.models import SourceGrant
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.test_prices import RECORD, post, setup_market

client = TestClient(app)


def test_rankings_use_fresh_latest_record_and_exact_scope(db, monkeypatch):
    item = setup_market(db, monkeypatch)
    now = datetime.now(timezone.utc)
    records = [{**RECORD, 'observed_at': (now - timedelta(days=2)).isoformat(), 'minor_units': 99999},
               {**RECORD, 'source_record_key': 'fresh-latest', 'observed_at': (now - timedelta(days=1)).isoformat(), 'minor_units': 123},
               {**RECORD, 'source_record_key': 'other-currency', 'observed_at': now.isoformat(), 'currency': 'JPY', 'minor_units': 999999},
               {**RECORD, 'source_record_key': 'variant', 'observed_at': now.isoformat(), 'external_key': 'test-skin-wear'}]
    assert post(records).status_code == 200
    result = client.get('/v1/rankings?source=test-fixture').json()
    assert result['items'][0]['item_id'] == item
    assert result['items'][0]['value'] == '123'
    assert result['currency'] == 'USD'
    assert client.get('/v1/rankings?source=other').json()['items'] == []
    assert client.get('/v1/rankings?source=test-fixture&category=case').json()['items'] == []
    grant = db.scalar(select(SourceGrant))
    grant.enabled = False
    db.commit()
    assert client.get('/v1/rankings?source=test-fixture').json()['items'] == []


def test_stale_data_never_in_rankings(db, monkeypatch):
    setup_market(db, monkeypatch)
    assert post([RECORD]).status_code == 200
    assert client.get('/v1/rankings?source=test-fixture').json()['status'] == 'unavailable'
    assert client.get('/v1/rankings?metric=estimated_total_units&source=test-fixture').json()['items'] == []
    assert client.get('/v1/rankings?max_age_days=999').status_code == 422


def test_process_rate_limit_and_health_exemption():
    small = FastAPI()
    small.add_middleware(RequestProtection, max_requests=2)
    @small.get('/test')
    def route():
        return {'ok': True}
    @small.get('/healthz')
    def health():
        return {'ok': True}
    c = TestClient(small)
    assert c.get('/test').status_code == 200
    assert c.get('/test').status_code == 200
    response = c.get('/test')
    assert response.status_code == 429
    assert response.headers['retry-after'] == '60'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert response.headers['x-request-id']
    assert c.get('/healthz').status_code == 200


def test_unauthorized_market_imports_and_security_headers(monkeypatch):
    monkeypatch.setenv('IMPORT_TOKEN', 'test-only-secret')
    for path in ['/internal/import/prices', '/internal/import/supply']:
        response = client.post(path, json={'source_code': 'x', 'records': []})
        assert response.status_code == 401
    result = client.get('/healthz')
    assert result.headers['x-frame-options'] == 'DENY'
