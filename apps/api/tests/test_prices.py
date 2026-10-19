"""仅测试用合成记录，绝不导入生产行情。"""
import copy

import pytest
from app.catalog import CatalogImport, import_catalog, stable_id
from app.main import app
from app.models import Item, Price, SourceGrant
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.test_catalog import BATCH, approve

client = TestClient(app)
RECORD = {'external_key': 'test-skin', 'source_record_key': 'test-observation-1',
          'observed_at': '2026-01-01T00:00:00Z', 'bucket_duration': '1d', 'price_kind': 'sale_median',
          'currency': 'USD', 'minor_units': 12345, 'evidence_url': 'https://example.invalid/test-only',
          'coverage': 'TEST ONLY synthetic record', 'methodology': 'TEST ONLY; not market evidence'}


def setup_market(db, monkeypatch):
    monkeypatch.setenv('IMPORT_TOKEN', 'test-only-secret')
    approve(db)
    import_catalog(db, CatalogImport.model_validate(BATCH))
    db.commit()
    source_id = stable_id('source:test-fixture')
    db.add(SourceGrant(id=stable_id('test-grant-prices'), source_id=source_id, dataset='prices',
                       license_reference='TEST ONLY', enabled=True))
    db.commit()
    return db.scalar(select(Item)).id


def post(records, source='test-fixture'):
    return client.post('/internal/import/prices', headers={'Authorization': 'Bearer test-only-secret'},
                       json={'source_code': source, 'records': records})


def test_price_idempotence_and_immutable_records(db, monkeypatch):
    item = setup_market(db, monkeypatch)
    assert post([RECORD]).json()['inserted'] == 1
    assert post([RECORD]).json()['inserted'] == 0
    changed = {**RECORD, 'minor_units': 9}
    assert post([changed]).status_code == 409
    data = client.get(f'/v1/items/{item}/prices').json()
    assert data['series'][0]['minor_units'] == '12345'
    assert data['metric_kind'] == 'sale_median'
    assert data['source'] == 'test-fixture'
    assert data['series'][0]['volume'] is None
    assert data['earliest_available_at'].startswith('2026-01-01')


def test_gaps_kind_currency_resolution_and_variant_isolation(db, monkeypatch):
    item = setup_market(db, monkeypatch)
    records = [RECORD, {**RECORD, 'source_record_key': 'test-day3', 'observed_at': '2026-01-03T00:00:00Z'},
               {**RECORD, 'source_record_key': 'test-ask', 'price_kind': 'ask_min', 'minor_units': 200},
               {**RECORD, 'source_record_key': 'test-jpy', 'currency': 'JPY', 'minor_units': 300},
               {**RECORD, 'source_record_key': 'test-variant', 'external_key': 'test-skin-wear'},
               {**RECORD, 'source_record_key': 'test-hour', 'bucket_duration': '1h'}]
    assert post(records).status_code == 200
    data = client.get(f'/v1/items/{item}/prices').json()
    assert len(data['series']) == 2
    assert len(data['gaps']) == 1
    assert len(client.get(f'/v1/items/{item}/prices?price_kind=ask_min').json()['series']) == 1
    assert client.get(f'/v1/items/{item}/prices?currency=JPY').json()['minor_unit_exponent'] == 0
    assert len(client.get(f'/v1/items/{item}/prices?resolution=1h').json()['series']) == 1
    variant_id = client.get(f'/v1/items/{item}/variants').json()['items'][0]['id']
    assert len(client.get(f'/v1/items/{item}/prices?variant_id={variant_id}').json()['series']) == 1
    assert client.get(f'/v1/items/{item}/prices?range=7D').json()['status'] == 'unavailable'
    window = client.get(f'/v1/items/{item}/prices', params={'from': '2026-01-02T00:00:00Z'}).json()
    assert len(window['series']) == 1
    assert window['earliest_available_at'].startswith('2026-01-01')


def test_price_grant_required_and_revocation_hides_observations(db, monkeypatch):
    item = setup_market(db, monkeypatch)
    assert post([RECORD]).status_code == 200
    grant = db.scalar(select(SourceGrant))
    grant.enabled = False
    db.commit()
    assert post([RECORD]).status_code == 403
    assert client.get(f'/v1/items/{item}/prices').json()['series'] == []


def test_unknown_mapping_rolls_back_whole_price_batch(db, monkeypatch):
    setup_market(db, monkeypatch)
    assert post([RECORD, {**RECORD, 'source_record_key': 'unknown', 'external_key': 'unknown'}]).status_code == 409
    assert db.scalars(select(Price)).all() == []


@pytest.mark.parametrize('field,value', [('minor_units', 1.5), ('minor_units', True), ('minor_units', -1),
    ('minor_units', None), ('minor_units', 9223372036854775808), ('observed_at', '2099-01-01T00:00:00Z'),
    ('observed_at', '2026-01-01'), ('currency', 'XYZ'), ('price_kind', 'fake'), ('coverage', '')])
def test_invalid_observations(db, monkeypatch, field, value):
    setup_market(db, monkeypatch)
    record = copy.deepcopy(RECORD)
    record[field] = value
    assert post([record]).status_code == 422


def test_second_source_never_merged_and_missing_not_zero(db, monkeypatch):
    item = setup_market(db, monkeypatch)
    assert client.get(f'/v1/items/{item}/prices').json()['series'] == []
    assert post([RECORD]).status_code == 200
    assert client.get(f'/v1/items/{item}/prices?source=another').json()['series'] == []
    assert client.get(f'/v1/items/{item}/prices?from=2026-02-01T00:00:00Z&to=2026-01-01T00:00:00Z').status_code == 422


def test_import_jobs_record_success_and_failure_without_raw_payload(db, monkeypatch):
    from app.models import ImportJob
    setup_market(db, monkeypatch)
    response = post([RECORD])
    job = db.get(ImportJob, response.json()['job_id'])
    assert job.status == 'completed'
    assert job.job_type == 'prices'
    assert post([{**RECORD, 'minor_units': 999}]).status_code == 409
    failed = db.scalar(select(ImportJob).where(ImportJob.status == 'failed'))
    assert '冲突' in failed.error_summary
    assert 'minor_units' not in failed.error_summary
