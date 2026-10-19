"""合成测试快照，非真实市场数据，不进入生产。"""
import csv
import io

import pytest
from app.catalog import stable_id
from app.main import app
from app.models import SourceGrant, Supply
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.test_prices import setup_market

client = TestClient(app)
SNAPSHOT = {'external_key': 'test-skin', 'source_record_key': 'test-supply-1',
            'measured_at': '2026-01-01T00:00:00Z', 'metric_type': 'listed_units', 'quantity': 12,
            'methodology_version': 'test-v1', 'coverage_note': 'TEST ONLY one mock marketplace',
            'sampling_method': 'TEST ONLY synthetic snapshot', 'evidence_url': 'https://example.invalid/test-only'}


def setup_supply(db, monkeypatch):
    item = setup_market(db, monkeypatch)
    db.add(SourceGrant(id=stable_id('test-grant-supply'), source_id=stable_id('source:test-fixture'),
                       dataset='supply', license_reference='TEST ONLY', enabled=True))
    db.commit()
    return item


def post(records):
    return client.post('/internal/import/supply', headers={'Authorization': 'Bearer test-only-secret'},
                       json={'source_code': 'test-fixture', 'records': records})


def csv_post(records):
    text = io.StringIO()
    writer = csv.DictWriter(text, fieldnames=list(records[0]))
    writer.writeheader()
    writer.writerows(records)
    return client.post('/internal/import/supply/csv?source_code=test-fixture',
                       headers={'Authorization': 'Bearer test-only-secret', 'Content-Type': 'text/csv'},
                       content=text.getvalue().encode())


def test_json_csv_idempotence_and_source_proof(db, monkeypatch):
    item = setup_supply(db, monkeypatch)
    assert post([SNAPSHOT]).json()['inserted'] == 1
    assert csv_post([SNAPSHOT]).json()['inserted'] == 0
    assert post([SNAPSHOT]).json()['inserted'] == 0
    result = client.get(f'/v1/items/{item}/supply?metric_type=listed_units').json()
    assert result['series'][0]['quantity'] == '12'
    assert '不等于总存世量' in result['metric_definition']
    assert result['series'][0]['evidence_url'].startswith('https://example.invalid')
    assert result['source'] == 'test-fixture'
    assert result['methodology'] == 'test-v1'


def test_metric_method_and_variant_isolation(db, monkeypatch):
    item = setup_supply(db, monkeypatch)
    records = [SNAPSHOT, {**SNAPSHOT, 'source_record_key': 'test-sample', 'metric_type': 'public_inventory_units'},
               {**SNAPSHOT, 'source_record_key': 'test-method', 'methodology_version': 'test-v2'},
               {**SNAPSHOT, 'source_record_key': 'test-variant', 'external_key': 'test-skin-wear'}]
    assert post(records).status_code == 200
    assert client.get(f'/v1/items/{item}/supply?metric_type=observed_distinct_instances').json()['series'] == []
    assert client.get(f'/v1/items/{item}/supply?metric_type=listed_units').json()['status'] == 'unavailable'
    result = client.get(f'/v1/items/{item}/supply?metric_type=listed_units&methodology_version=test-v1').json()
    assert len(result['series']) == 1
    assert len(client.get(f'/v1/items/{item}/supply?metric_type=public_inventory_units').json()['series']) == 1


def test_no_backcast_and_actual_zero_is_distinct_from_missing(db, monkeypatch):
    item = setup_supply(db, monkeypatch)
    assert post([{**SNAPSHOT, 'quantity': 0}]).status_code == 200
    result = client.get(f'/v1/items/{item}/supply?metric_type=listed_units').json()
    assert result['status'] == 'ok'
    assert result['series'][0]['quantity'] == '0'
    earlier = client.get(f'/v1/items/{item}/supply?metric_type=listed_units&to=2025-12-01T00:00:00Z').json()
    assert earlier['status'] == 'unavailable'
    assert earlier['series'] == []
    assert earlier['earliest_available_at'].startswith('2026-01-01')


def test_conflict_atomic_and_supply_grant_is_separate(db, monkeypatch):
    setup_supply(db, monkeypatch)
    assert post([SNAPSHOT, {**SNAPSHOT, 'quantity': 99}]).status_code == 409
    assert db.scalars(select(Supply)).all() == []
    grant = db.scalar(select(SourceGrant).where(SourceGrant.dataset == 'supply'))
    grant.enabled = False
    db.commit()
    assert post([SNAPSHOT]).status_code == 403


@pytest.mark.parametrize('change', [
    {'quantity': -1}, {'quantity': 1.2}, {'quantity': None}, {'quantity': True},
    {'measured_at': '2099-01-01T00:00:00Z'}, {'measured_at': '2026-01-01'},
    {'metric_type': 'estimated_total_units'}, {'coverage_note': ''}, {'sampling_method': ''},
    {'methodology_version': ''}, {'confidence_low': 1}, {'evidence_url': 'javascript:bad'}])
def test_invalid_supply_rejected(db, monkeypatch, change):
    setup_supply(db, monkeypatch)
    assert post([{**SNAPSHOT, **change}]).status_code == 422


def test_estimation_requires_model_bounds_and_version(db, monkeypatch):
    item = setup_supply(db, monkeypatch)
    estimate = {**SNAPSHOT, 'metric_type': 'estimated_total_units', 'quantity': 100,
                'confidence_low': 80, 'confidence_high': 120,
                'model_evidence_url': 'https://example.invalid/test-only-model'}
    assert post([{**estimate, 'confidence_high': 90}]).status_code == 422
    assert post([estimate]).status_code == 200
    result = client.get(f'/v1/items/{item}/supply?metric_type=estimated_total_units').json()
    assert result['series'][0]['confidence_low'] == '80'
    assert result['series'][0]['confidence_high'] == '120'


@pytest.mark.parametrize('quantity', ['1.5', '-1', '1e5', '9223372036854775808', ''])
def test_csv_invalid_quantities(db, monkeypatch, quantity):
    setup_supply(db, monkeypatch)
    assert csv_post([{**SNAPSHOT, 'quantity': quantity}]).status_code == 422
