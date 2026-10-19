"""核实映射的原子性与变体归属测试；仅合成测试数据。"""
from app.catalog import CatalogImport, import_catalog, stable_id
from app.main import app
from app.models import Item, Mapping, Variant
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.test_catalog import BATCH, approve
from tests.test_prices import setup_market

client = TestClient(app)
HEADERS = {'Authorization': 'Bearer test-only-secret'}


def setup_mapping(db, monkeypatch):
    item = setup_market(db, monkeypatch)
    approve(db, 'mapped-test-source')
    return item, {'source_code': 'mapped-test-source', 'verified_at': '2026-01-01T00:00:00Z',
                  'dataset_revision': 'test-only', 'evidence_url': 'https://example.invalid/test-only',
                  'mappings': [{'external_key': 'test-platform-key', 'item_id': item}]}


def test_mapping_batch_rolls_back_and_rejects_wrong_variant_parent(db, monkeypatch):
    item, payload = setup_mapping(db, monkeypatch)
    batch = {**BATCH, 'items': [{'external_key': 'another-test-item', 'category': 'skin', 'name_en': 'TEST ONLY Another'}]}
    import_catalog(db, CatalogImport.model_validate(batch))
    db.commit()
    other = db.scalar(select(Item).where(Item.id != item))
    variant = db.scalar(select(Variant).where(Variant.item_id == item))
    payload['mappings'].append({'external_key': 'wrong-parent', 'item_id': other.id, 'variant_id': variant.id})
    assert client.post('/internal/import/mappings', json=payload, headers=HEADERS).status_code == 409
    assert db.scalars(select(Mapping).where(Mapping.source_id == stable_id('source:mapped-test-source'))).all() == []


def test_mapping_stale_proof_and_future_verification_rejected(db, monkeypatch):
    _, payload = setup_mapping(db, monkeypatch)
    assert client.post('/internal/import/mappings', json=payload, headers=HEADERS).status_code == 200
    stale = {**payload, 'verified_at': '2025-01-01T00:00:00Z', 'dataset_revision': 'bad-old'}
    assert client.post('/internal/import/mappings', json=stale, headers=HEADERS).status_code == 409
    row = db.scalar(select(Mapping).where(Mapping.source_id == stable_id('source:mapped-test-source')))
    assert row.dataset_revision == 'test-only'
    future = {**payload, 'verified_at': '2099-01-01T00:00:00Z'}
    assert client.post('/internal/import/mappings', json=future, headers=HEADERS).status_code == 422
