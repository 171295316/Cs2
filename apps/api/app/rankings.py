from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.catalog import Category
from app.models import Item, Price, Source, SourceGrant, Supply
from app.observations import Currency, utc
from app.routes import DB
from app.supply import DEFINITIONS

router = APIRouter()
RankingMetric = Literal['sale_median', 'ask_min', 'bid_max', 'observed_distinct_instances',
                        'public_inventory_units', 'listed_units', 'estimated_total_units']


@router.get('/v1/rankings')
def rankings(db: DB, metric: RankingMetric = 'sale_median', source: str | None = Query(None, max_length=100),
             category: Category | None = None, currency: Currency = 'USD',
             methodology_version: str | None = Query(None, max_length=100),
             max_age_days: int = Query(7, ge=1, le=30), limit: int = Query(10, ge=1, le=50)):
    result: dict = {'status': 'unavailable', 'items': [], 'source': source, 'metric_kind': metric,
                    'currency': currency if metric not in DEFINITIONS else None,
                    'max_age_days': max_age_days, 'reason': '暂无可核实数据'}
    if metric == 'estimated_total_units':
        result['reason'] = '估算总量需同时展示模型和区间，暂不提供单值排行'
        return result
    if not source or (metric in DEFINITIONS and not methodology_version):
        result['reason'] = '排行需明确来源，供给排行还需明确方法版本'
        return result
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max_age_days)
    is_supply = metric in DEFINITIONS
    model = Supply if is_supply else Price
    time = Supply.measured_at if is_supply else Price.observed_at
    value = Supply.quantity if is_supply else Price.minor_units
    methodology = Supply.methodology_version if is_supply else Price.methodology
    coverage = Supply.coverage_note if is_supply else Price.coverage
    dataset = 'supply' if is_supply else 'prices'
    query = select(model.item_id.label('item_id'), value.label('value'), time.label('as_of'),
                   coverage.label('coverage'), methodology.label('methodology'), model.evidence_url.label('evidence_url'),
                   func.row_number().over(partition_by=model.item_id, order_by=time.desc()).label('rn')).join(
        Source, model.source_id == Source.id).join(SourceGrant, SourceGrant.source_id == Source.id).join(
        Item, model.item_id == Item.id).where(Source.code == source, Source.license_status == 'approved',
        Source.redistribution_allowed.is_(True), SourceGrant.dataset == dataset, SourceGrant.enabled.is_(True),
        model.variant_id.is_(None), time >= cutoff, time <= now)
    if is_supply:
        query = query.where(Supply.metric_type == metric, Supply.methodology_version == methodology_version)
    else:
        query = query.where(Price.price_kind == metric, Price.currency == currency, Price.bucket_duration == '1d')
    if category:
        query = query.where(Item.category == category)
    sub = query.subquery()
    rows: Any = db.execute(select(Item, sub.c.value, sub.c.as_of, sub.c.coverage, sub.c.methodology, sub.c.evidence_url)
                      .join(sub, Item.id == sub.c.item_id).where(sub.c.rn == 1)
                      .order_by(sub.c.value.desc(), Item.id).limit(limit)).all()
    result.update(status='ok' if rows else 'unavailable', reason=None if rows else '暂无可核实数据',
                  metric_definition=DEFINITIONS.get(metric, metric),
                  methodology_version=methodology_version if is_supply else None,
                  minor_unit_exponent=None if is_supply else (0 if currency == 'JPY' else 2),
                  items=[{'item_id': item.id, 'name_zh': item.name_zh, 'name_en': item.name_en,
                          'value': str(number), 'as_of': utc(at), 'coverage': cov, 'methodology': method,
                          'evidence_url': proof} for item, number, at, cov, method, proof in rows])
    return result
