from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import AwareDatetime
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.catalog import ImportConflict
from app.models import Price, Source, SourceGrant, Variant
from app.observations import Currency, PriceBatch, PriceKind, Resolution, import_prices, utc
from app.routes import DB, authenticate, item_or_404

router = APIRouter()
Range = Literal['7D', '30D', '1Y', 'ALL']


def interval(from_at: datetime | None, to_at: datetime | None, period: str):
    end = to_at or datetime.now(timezone.utc)
    if from_at and from_at > end:
        raise HTTPException(422, 'from must precede to')
    days = {'7D': 7, '30D': 30, '1Y': 365}.get(period)
    start = max(from_at, end - timedelta(days=days)) if from_at and days else (
        from_at or (end - timedelta(days=days) if days else None))
    return start, end


def validate_variant(db, item_id: str, variant_id: UUID | None):
    if variant_id:
        variant = db.get(Variant, str(variant_id))
        if variant is None or variant.item_id != item_id:
            raise HTTPException(404, 'Variant does not belong to item')


@router.post('/internal/import/prices', dependencies=[Depends(authenticate)])
def ingest(batch: PriceBatch, db: DB):
    try:
        result = import_prices(db, batch)
        db.commit()
        return result
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(403, str(exc)) from None
    except (ImportConflict, IntegrityError):
        db.rollback()
        raise HTTPException(409, 'Conflicting observation or unknown mapping; batch rolled back') from None


@router.get('/v1/items/{item_id}/prices')
def prices(item_id: UUID, db: DB, variant_id: UUID | None = None,
           source: str | None = Query(None, max_length=100), price_kind: PriceKind = 'sale_median',
           currency: Currency = 'USD', resolution: Resolution = '1d', range: Range = 'ALL',
           from_at: Annotated[AwareDatetime | None, Query(alias='from')] = None,
           to_at: Annotated[AwareDatetime | None, Query(alias='to')] = None):
    item = item_or_404(db, item_id)
    validate_variant(db, item.id, variant_id)
    start, end = interval(from_at, to_at, range)
    base = select(Price).join(Source, Price.source_id == Source.id).join(SourceGrant, SourceGrant.source_id == Source.id).where(
        Price.item_id == item.id, Price.variant_id == (str(variant_id) if variant_id else None),
        Source.license_status == 'approved', Source.redistribution_allowed.is_(True),
        SourceGrant.dataset == 'prices', SourceGrant.enabled.is_(True))
    options = db.execute(base.with_only_columns(Source.code, Price.currency, Price.price_kind,
                                                Price.bucket_duration).distinct()).all()
    filtered = base.where(Price.currency == currency, Price.price_kind == price_kind, Price.bucket_duration == resolution)
    available = db.scalars(filtered.with_only_columns(Source.code).distinct()).all()
    selected = source or (available[0] if len(available) == 1 else None)
    result: dict = {'status': 'unavailable', 'series': [], 'source': selected, 'currency': currency,
              'price_kind': price_kind, 'metric_kind': price_kind, 'resolution': resolution,
              'minor_unit_exponent': 0 if currency == 'JPY' else 2,
              'earliest_available_at': None, 'latest_at': None, 'as_of': None, 'gaps': [],
              'options': [{'source': r[0], 'currency': r[1], 'price_kind': r[2], 'resolution': r[3]} for r in options],
              'reason': '请选择唯一来源' if len(available) > 1 and not selected else '暂无可核实数据'}
    if selected is None:
        return result
    filtered = filtered.where(Source.code == selected)
    earliest, latest = db.execute(filtered.with_only_columns(func.min(Price.observed_at), func.max(Price.observed_at))).one()
    result.update(earliest_available_at=earliest, latest_at=latest, as_of=latest)
    query = filtered.where(Price.observed_at <= end)
    if start:
        query = query.where(Price.observed_at >= start)
    rows = db.scalars(query.order_by(Price.observed_at).limit(20001)).all()
    if len(rows) > 20000:
        raise HTTPException(413, 'Too many observations; choose daily resolution or a shorter range')
    seconds = 3600 if resolution == '1h' else 86400
    gaps = [{'from': utc(a.observed_at), 'to': utc(b.observed_at)} for a, b in zip(rows, rows[1:])
            if (utc(b.observed_at) - utc(a.observed_at)).total_seconds() > seconds]
    result.update(status='ok' if rows else 'unavailable', gaps=gaps,
                  reason=None if rows else '暂无可核实数据',
                  series=[{'as_of': utc(r.observed_at), 'minor_units': str(r.minor_units),
                           'volume': str(r.volume) if r.volume is not None else None,
                           'evidence_url': r.evidence_url, 'coverage': r.coverage,
                           'methodology': r.methodology, 'source_record_key': r.source_record_key} for r in rows])
    return result
