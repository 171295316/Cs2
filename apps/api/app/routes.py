import base64
import hashlib
import json
import os
import secrets
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.catalog import CatalogImport, Category, import_catalog
from app.db import SessionLocal
from app.jobs import run_import
from app.models import Item, Mapping, Source, SourceGrant, Variant
from app.observations import utc

router = APIRouter()


def database():
    with SessionLocal() as db:
        yield db


DB = Annotated[Session, Depends(database)]


def catalog_access():
    return select(Mapping.item_id).join(Source).where(Source.license_status == 'approved',
                                                     Source.redistribution_allowed.is_(True))


def item_or_404(db: Session, item_id: UUID) -> Item:
    item = db.scalar(select(Item).where(Item.id == str(item_id), Item.id.in_(catalog_access())))
    if item is None:
        raise HTTPException(404, 'Item not found')
    return item


def provenance(db: Session, item_id: str) -> list[dict]:
    rows = db.execute(select(Mapping, Source).join(Source).where(Mapping.item_id == item_id)
                      .order_by(Source.code, Mapping.external_key)).all()
    return [{'source': source.code, 'name': source.name, 'external_key': mapping.external_key,
             'variant_id': mapping.variant_id, 'as_of': utc(mapping.verified_at),
             'dataset_revision': mapping.dataset_revision, 'evidence_url': mapping.evidence_url,
             'license_reference': source.license_reference} for mapping, source in rows]


def item_json(item: Item) -> dict:
    return {field: utc(item.updated_at) if field == 'updated_at' else getattr(item, field) for field in ['id', 'canonical_key', 'category', 'name_en', 'name_zh',
            'market_hash_name', 'image_url', 'tradable', 'marketable', 'attributes_json', 'updated_at']}


@router.get('/v1/items')
def items(db: DB, query: str = Query('', max_length=200), category: Category | None = None,
          cursor: str | None = Query(None, max_length=1000), limit: int = Query(20, ge=1, le=100),
          sort: str = Query('id', pattern='^id$')):
    query = query.strip()
    scope = hashlib.sha256(json.dumps([query, category, sort]).encode()).hexdigest()
    stmt = select(Item).where(Item.id.in_(catalog_access()))
    if query:
        escaped = query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        pattern = '%' + escaped + '%'
        stmt = stmt.where(or_(Item.name_en.ilike(pattern, escape='\\'),
                              Item.name_zh.ilike(pattern, escape='\\'),
                              Item.market_hash_name.ilike(pattern, escape='\\')))
    if category:
        stmt = stmt.where(Item.category == category)
    if cursor:
        try:
            token = json.loads(base64.urlsafe_b64decode(cursor.encode()))
            if token['scope'] != scope:
                raise ValueError('scope mismatch')
            after = str(UUID(token['after']))
        except (ValueError, KeyError, TypeError, UnicodeError):
            raise HTTPException(422, 'Invalid cursor or changed filters') from None
        stmt = stmt.where(Item.id > after)
    rows = db.scalars(stmt.order_by(Item.id).limit(limit + 1)).all()
    next_cursor = None
    if len(rows) > limit:
        next_cursor = base64.urlsafe_b64encode(json.dumps({'scope': scope, 'after': rows[limit - 1].id}).encode()).decode()
    return {'status': 'ok' if rows else 'unavailable', 'items': [item_json(i) for i in rows[:limit]],
            'next_cursor': next_cursor, 'reason': None if rows else '暂无可核实数据'}


@router.get('/v1/items/{item_id}')
def detail(item_id: UUID, db: DB):
    item = item_or_404(db, item_id)
    return {**item_json(item), 'provenance': provenance(db, item.id)}


@router.get('/v1/items/{item_id}/variants')
def variants(item_id: UUID, db: DB):
    item = item_or_404(db, item_id)
    rows = db.scalars(select(Variant).where(Variant.item_id == item.id).order_by(Variant.id)).all()
    return {'items': [{field: getattr(v, field) for field in ['id', 'item_id', 'variant_key', 'wear',
                      'stattrak', 'souvenir', 'paint_index', 'market_hash_name', 'attributes_json']} for v in rows]}


@router.get('/v1/sources')
def sources(db: DB):
    rows = db.scalars(select(Source).order_by(Source.code)).all()
    return {'items': [{**{field: utc(s.updated_at) if field == 'updated_at' else getattr(s, field) for field in ['code', 'name', 'homepage', 'license_status',
                     'license_reference', 'redistribution_allowed', 'updated_at']},
                     'grants': [{'dataset': g.dataset, 'license_reference': g.license_reference,
                                 'approved_at': utc(g.approved_at), 'enabled': g.enabled}
                                for g in db.scalars(select(SourceGrant).where(SourceGrant.source_id == s.id)).all()]}
                     for s in rows]}



def authenticate(authorization: Annotated[str | None, Header()] = None):
    token = os.environ.get('IMPORT_TOKEN', '')
    if not token:
        raise HTTPException(503, 'Imports are disabled')
    if not authorization or not secrets.compare_digest(authorization.encode(), ('Bearer ' + token).encode()):
        raise HTTPException(401, 'Authentication required', headers={'WWW-Authenticate': 'Bearer'})


@router.post('/internal/import/catalog', dependencies=[Depends(authenticate)])
def import_items(batch: CatalogImport, db: DB):
    return run_import(db, batch.source_code, 'catalog', lambda: import_catalog(db, batch))
