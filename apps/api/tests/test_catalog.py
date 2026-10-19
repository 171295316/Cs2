"""Synthetic catalog fixtures ONLY; never bundled in production or market observations."""
import copy

import pytest
from app.bymykel import normalize
from app.catalog import CatalogImport, import_catalog, stable_id
from app.main import app
from app.models import Item, Mapping, Source, Variant
from fastapi.testclient import TestClient
from sqlalchemy import func, select

client = TestClient(app)
BATCH = {
    'source_code': 'test-fixture', 'dataset_revision': 'synthetic-test-v1',
    'evidence_url': 'https://example.invalid/test-only', 'verified_at': '2026-01-01T00:00:00Z',
    'items': [{'external_key': 'test-skin', 'category': 'skin', 'name_en': 'TEST ONLY Skin',
               'name_zh': '测试专用皮肤', 'variants': [
                   {'external_key': 'test-skin-wear', 'wear': 'test-wear', 'stattrak': True,
                    'souvenir': False, 'paint_index': 1, 'market_hash_name': 'TEST ONLY Variant'}]}]
}


def approve(db, code='test-fixture'):
    db.add(Source(id=stable_id('source:' + code), code=code, name='TEST ONLY', homepage='https://example.invalid',
                  license_status='approved', license_reference='synthetic test fixture', redistribution_allowed=True))
    db.commit()


def submit(monkeypatch, batch=None):
    monkeypatch.setenv('IMPORT_TOKEN', 'test-only-secret')
    return client.post('/internal/import/catalog', json=batch or BATCH,
                       headers={'Authorization': 'Bearer test-only-secret'})


def test_import_idempotence_mapping_and_bilingual_search(db, monkeypatch):
    approve(db)
    assert submit(monkeypatch).status_code == 200
    first = client.get('/v1/items', params={'query': '皮肤'}).json()['items'][0]
    assert submit(monkeypatch).status_code == 200
    assert db.scalar(select(func.count()).select_from(Item)) == 1
    assert db.scalar(select(func.count()).select_from(Variant)) == 1
    assert db.scalar(select(func.count()).select_from(Mapping)) == 2
    detail = client.get('/v1/items/' + first['id']).json()
    assert len(detail['provenance']) == 2
    assert detail['provenance'][0]['dataset_revision'] == 'synthetic-test-v1'
    variants = client.get('/v1/items/' + first['id'] + '/variants').json()['items']
    assert variants[0]['stattrak'] is True
    assert variants[0]['souvenir'] is False
    assert first['tradable'] is None  # Unknown upstream flags must stay unknown.
    changed = copy.deepcopy(BATCH)
    changed['items'][0]['name_en'] = 'TEST ONLY Renamed'
    assert submit(monkeypatch, changed).status_code == 200
    assert client.get('/v1/items', params={'query': 'Renamed'}).json()['items'][0]['id'] == first['id']


def test_authentication_and_approval_fail_closed(db, monkeypatch):
    monkeypatch.delenv('IMPORT_TOKEN', raising=False)
    assert client.post('/internal/import/catalog', json=BATCH).status_code == 503
    monkeypatch.setenv('IMPORT_TOKEN', 'test-only-secret')
    assert client.post('/internal/import/catalog', json=BATCH).status_code == 401
    assert submit(monkeypatch).status_code == 403
    assert db.scalar(select(func.count()).select_from(Item)) == 0


def test_pagination_filters_and_literal_search(db, monkeypatch):
    approve(db)
    batch = copy.deepcopy(BATCH)
    batch['items'] += [{'external_key': 'test-case', 'category': 'case', 'name_en': 'TEST ONLY Case'},
                       {'external_key': 'test-agent', 'category': 'agent', 'name_en': 'TEST ONLY Agent'}]
    assert submit(monkeypatch, batch).status_code == 200
    page = client.get('/v1/items?limit=1').json()
    ids = [page['items'][0]['id']]
    while page['next_cursor']:
        page = client.get('/v1/items', params={'limit': 1, 'cursor': page['next_cursor']}).json()
        ids += [page['items'][0]['id']]
    assert len(set(ids)) == 3
    assert len(client.get('/v1/items?category=case').json()['items']) == 1
    cursor = client.get('/v1/items?limit=1').json()['next_cursor']
    assert client.get('/v1/items', params={'query': 'changed', 'cursor': cursor}).status_code == 422
    assert client.get('/v1/items?cursor=%%%').status_code == 422
    assert client.get('/v1/items?limit=101').status_code == 422
    assert client.get('/v1/items?category=bogus').status_code == 422
    assert client.get('/v1/items?query=%25').json()['items'] == []
    assert client.get('/v1/items?query=_').json()['items'] == []


def test_external_keys_cannot_be_reassigned_and_batch_is_atomic(db, monkeypatch):
    approve(db)
    assert submit(monkeypatch).status_code == 200
    batch = copy.deepcopy(BATCH)
    batch['items'][0]['external_key'] = 'new-base'
    assert submit(monkeypatch, batch).status_code == 409
    assert db.scalar(select(func.count()).select_from(Item)) == 1


def test_stale_import_rolls_back_updates(db, monkeypatch):
    approve(db)
    assert submit(monkeypatch).status_code == 200
    batch = copy.deepcopy(BATCH)
    batch['verified_at'] = '2025-01-01T00:00:00Z'
    batch['items'][0]['name_en'] = 'BAD STALE UPDATE'
    assert submit(monkeypatch, batch).status_code == 409
    assert db.scalar(select(Item)).name_en == 'TEST ONLY Skin'


@pytest.mark.parametrize('field,value', [('verified_at', '2026-01-01'),
                                        ('verified_at', '2099-01-01T00:00:00Z'),
                                        ('evidence_url', 'javascript:bad')])
def test_invalid_provenance(db, monkeypatch, field, value):
    batch = copy.deepcopy(BATCH)
    batch[field] = value
    assert submit(monkeypatch, batch).status_code == 422


def test_missing_and_unknown_items(db):
    assert client.get('/v1/items').json()['status'] == 'unavailable'
    assert client.get('/v1/items/not-a-uuid').status_code == 422
    assert client.get('/v1/items/00000000-0000-0000-0000-000000000000').status_code == 404


def test_sources_never_merge_by_display_name(db, monkeypatch):
    approve(db)
    approve(db, 'second-source')
    assert submit(monkeypatch).status_code == 200
    batch = copy.deepcopy(BATCH)
    batch['source_code'] = 'second-source'
    assert submit(monkeypatch, batch).status_code == 200
    assert db.scalar(select(func.count()).select_from(Item)) == 2


def test_duplicate_source_keys_rejected():
    batch = copy.deepcopy(BATCH)
    batch['items'] += batch['items']
    with pytest.raises(ValueError, match='duplicate'):
        CatalogImport.model_validate(batch)


def test_offline_adapter_matches_translations_by_id():
    from datetime import datetime, timezone
    en = [{'id': 'test-v', 'skin_id': 'test-base', 'name': 'TEST ONLY Variant', 'stattrak': False,
           'souvenir': True, 'wear': {'id': 'test-wear'}, 'paint_index': '1'}]
    zh = [{'id': 'different-id', 'name': '不应匹配'}]
    batch = normalize(en, zh, 'skin', 'test-only', datetime(2026, 1, 1, tzinfo=timezone.utc),
                      'https://example.invalid/fixture')
    assert batch.items[0].name_zh is None
    assert batch.items[0].external_key == 'test-base'
    assert batch.items[0].variants[0].external_key == 'test-v'
    assert batch.items[0].image_url is None


def test_database_unique_constraint(db):
    from sqlalchemy.exc import IntegrityError
    approve(db)
    import_catalog(db, CatalogImport.model_validate(BATCH))
    db.commit()
    mapping = db.scalar(select(Mapping))
    db.add(Mapping(id=stable_id('duplicate'), item_id=mapping.item_id, source_id=mapping.source_id,
                   external_key=mapping.external_key, verified_at=mapping.verified_at,
                   dataset_revision='duplicate', evidence_url='https://example.invalid'))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_oversized_import_rejected_before_json_parse(monkeypatch):
    monkeypatch.setenv('IMPORT_TOKEN', 'test-only-secret')
    response = client.post('/internal/import/catalog', content=b'x' * (2 * 1024 * 1024 + 1),
                           headers={'Content-Type': 'application/json'})
    assert response.status_code == 413


def test_delimiter_characters_cannot_collide_stable_ids(db, monkeypatch):
    approve(db)
    batch = copy.deepcopy(BATCH)
    batch['items'] = [
        {'external_key': 'a:b', 'category': 'skin', 'name_en': 'TEST ONLY A',
         'variants': [{'external_key': 'c'}]},
        {'external_key': 'a', 'category': 'skin', 'name_en': 'TEST ONLY B',
         'variants': [{'external_key': 'b:c'}]}]
    assert submit(monkeypatch, batch).status_code == 200
    rows = db.scalars(select(Variant)).all()
    assert len({row.id for row in rows}) == 2
    assert len({row.item_id for row in rows}) == 2


def test_all_supported_categories_and_nullable_flags(db, monkeypatch):
    from typing import get_args

    from app.catalog import Category
    approve(db)
    batch = copy.deepcopy(BATCH)
    batch['items'] = [{'external_key': 'test-' + category, 'category': category,
                       'name_en': 'TEST ONLY ' + category} for category in get_args(Category)]
    assert submit(monkeypatch, batch).status_code == 200
    for category in get_args(Category):
        response = client.get('/v1/items', params={'category': category}).json()
        assert len(response['items']) == 1
        assert response['items'][0]['tradable'] is None
        assert response['items'][0]['marketable'] is None
