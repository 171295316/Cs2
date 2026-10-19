import csv
import io
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, ValidationError, model_validator
from sqlalchemy import func, select

from app.catalog import ImportConflict, Key, stable_id
from app.jobs import run_import
from app.models import Source, SourceGrant, Supply
from app.observations import Count, authorized, resolve_mapping, utc
from app.prices import Range, interval, validate_variant
from app.routes import DB, authenticate, item_or_404

Metric = Literal['observed_distinct_instances', 'public_inventory_units', 'listed_units', 'estimated_total_units']
DEFINITIONS = {'observed_distinct_instances': '已发现独立实例数，不等于总存世量',
               'public_inventory_units': '公开库存可见样本，不等于全市场总量',
               'listed_units': '平台在售数量，不等于总存世量',
               'estimated_total_units': '基于明确模型和区间的估算总量，不是直接观测值'}
router = APIRouter()


class SupplyInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    external_key: Key
    source_record_key: str = Field(min_length=1, max_length=250)
    measured_at: AwareDatetime
    metric_type: Metric
    quantity: Count
    methodology_version: str = Field(min_length=1, max_length=100)
    coverage_note: str = Field(min_length=1, max_length=2000)
    sampling_method: str = Field(min_length=1, max_length=2000)
    evidence_url: HttpUrl
    confidence_low: Count | None = None
    confidence_high: Count | None = None
    model_evidence_url: HttpUrl | None = None

    @model_validator(mode='after')
    def valid_evidence(self):
        self.measured_at = utc(self.measured_at)
        if self.measured_at > datetime.now(timezone.utc):
            raise ValueError('不允许未来快照')
        if self.metric_type == 'estimated_total_units':
            if self.confidence_low is None or self.confidence_high is None or self.model_evidence_url is None:
                raise ValueError('估算必须提供模型证据与上下界')
            if not self.confidence_low <= self.quantity <= self.confidence_high:
                raise ValueError('估算值必须在上下界内')
        elif any(value is not None for value in [self.confidence_low, self.confidence_high, self.model_evidence_url]):
            raise ValueError('非估算口径不能携带估算区间')
        return self


class SupplyBatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source_code: Key
    records: list[SupplyInput] = Field(min_length=1, max_length=1000)


def import_supply(db, batch: SupplyBatch):
    source = authorized(db, batch.source_code, 'supply')
    inserted = 0
    for record in batch.records:
        mapping = resolve_mapping(db, source, record.external_key)
        values = record.model_dump(exclude={'external_key'})
        values['evidence_url'] = str(record.evidence_url)
        values['model_evidence_url'] = str(record.model_evidence_url) if record.model_evidence_url else None
        values.update(item_id=mapping.item_id, variant_id=mapping.variant_id, mapping_id=mapping.id)
        existing = db.scalar(select(Supply).where(Supply.source_id == source.id,
                                                 Supply.source_record_key == record.source_record_key))
        if existing:
            for field, value in values.items():
                previous = getattr(existing, field)
                if isinstance(previous, datetime):
                    previous = utc(previous)
                if previous != value:
                    raise ImportConflict('快照记录与已有原始记录冲突')
            continue
        db.add(Supply(id=stable_id('supply:' + source.id + ':' + record.source_record_key),
                      source_id=source.id, **values))
        db.flush()
        inserted += 1
    return {'status': 'ok', 'inserted': inserted, 'processed': len(batch.records), 'source': source.code}


def transact(db, batch):
    return run_import(db, batch.source_code, 'supply', lambda: import_supply(db, batch))


@router.post('/internal/import/supply', dependencies=[Depends(authenticate)])
def ingest(batch: SupplyBatch, db: DB):
    return transact(db, batch)


@router.post('/internal/import/supply/csv', dependencies=[Depends(authenticate)])
def ingest_csv(db: DB, source_code: str = Query(max_length=90),
               body: bytes = Body(media_type='text/csv')):
    try:
        reader = csv.DictReader(io.StringIO(body.decode('utf-8-sig')))
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)) or any(h not in SupplyInput.model_fields for h in headers):
            raise ValueError('CSV 表头重复或含未知字段')
        rows: list[dict] = []
        for raw in reader:
            if len(rows) >= 1000 or None in raw or any(v is None for v in raw.values()):
                raise ValueError('CSV 行数或列数不合法')
            record = {k: v for k, v in raw.items() if v != ''}
            for key in ['quantity', 'confidence_low', 'confidence_high']:
                if key in record:
                    value = record[key]
                    if len(value) > 19 or not value.isascii() or not value.isdecimal():
                        raise ValueError('数量必须是非负整数')
                    record[key] = int(value)
            rows.append(record)
        batch = SupplyBatch.model_validate({'source_code': source_code, 'records': rows})
    except (ValueError, UnicodeError, csv.Error, ValidationError):
        raise HTTPException(422, 'CSV 格式或快照证据不合法，请参照导入模板') from None
    return transact(db, batch)


@router.get('/v1/items/{item_id}/supply')
def supply(item_id: UUID, db: DB, variant_id: UUID | None = None,
           source: str | None = Query(None, max_length=100), metric_type: Metric = 'observed_distinct_instances',
           methodology_version: str | None = Query(None, max_length=100), range: Range = 'ALL',
           from_at: Annotated[AwareDatetime | None, Query(alias='from')] = None,
           to_at: Annotated[AwareDatetime | None, Query(alias='to')] = None):
    item = item_or_404(db, item_id)
    validate_variant(db, item.id, variant_id)
    start, end = interval(from_at, to_at, range)
    base = select(Supply).join(Source, Supply.source_id == Source.id).join(SourceGrant, SourceGrant.source_id == Source.id).where(
        Supply.item_id == item.id, Supply.variant_id == (str(variant_id) if variant_id else None),
        Source.license_status == 'approved', Source.redistribution_allowed.is_(True),
        SourceGrant.dataset == 'supply', SourceGrant.enabled.is_(True))
    options = db.execute(base.with_only_columns(Source.code, Supply.metric_type, Supply.methodology_version).distinct()).all()
    eligible = [(s, m) for s, t, m in options if t == metric_type and (not source or s == source)
                and (not methodology_version or m == methodology_version)]
    result: dict = {'status': 'unavailable', 'series': [], 'source': source, 'metric_kind': metric_type,
                    'metric_definition': DEFINITIONS[metric_type], 'as_of': None,
                    'earliest_available_at': None, 'latest_at': None, 'coverage': None,
                    'methodology': methodology_version, 'gaps': [],
                    'options': [{'source': s, 'metric_type': t, 'methodology_version': m} for s, t, m in options],
                    'reason': '请选择唯一来源和方法版本' if len(eligible) > 1 else '暂无可核实数据'}
    if len(eligible) != 1:
        return result
    selected, version = eligible[0]
    filtered = base.where(Source.code == selected, Supply.metric_type == metric_type,
                          Supply.methodology_version == version)
    earliest, latest = db.execute(filtered.with_only_columns(func.min(Supply.measured_at), func.max(Supply.measured_at))).one()
    query = filtered.where(Supply.measured_at <= end)
    if start:
        query = query.where(Supply.measured_at >= start)
    rows = db.scalars(query.order_by(Supply.measured_at).limit(20001)).all()
    if len(rows) > 20000:
        raise HTTPException(413, '快照过多，请缩小时间范围')
    result.update(status='ok' if rows else 'unavailable', reason=None if rows else '暂无可核实数据',
        source=selected, methodology=version, as_of=utc(latest) if latest else None, earliest_available_at=utc(earliest) if earliest else None, latest_at=utc(latest) if latest else None,
        coverage=sorted({r.coverage_note for r in rows}),
        series=[{'as_of': utc(r.measured_at), 'quantity': str(r.quantity), 'coverage': r.coverage_note,
                 'sampling_method': r.sampling_method, 'methodology_version': r.methodology_version,
                 'confidence_low': str(r.confidence_low) if r.confidence_low is not None else None,
                 'confidence_high': str(r.confidence_high) if r.confidence_high is not None else None,
                 'model_evidence_url': r.model_evidence_url, 'evidence_url': r.evidence_url,
                 'source_record_key': r.source_record_key} for r in rows])
    # 任意采样时间的原始快照不假定每日一次；只展示实际时间，不补造每日/历史数据。
    return result
