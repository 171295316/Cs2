"""Authorized immutable observations; no provider requests or inferred history."""
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog import ImportConflict, Key, stable_id
from app.models import Mapping, Price, Source, SourceGrant

Count = Annotated[int, Field(strict=True, ge=0, le=9223372036854775807)]
PriceKind = Literal['sale_median', 'ask_min', 'bid_max']
Currency = Literal['USD', 'CNY', 'JPY', 'EUR', 'GBP']
Resolution = Literal['1h', '1d']


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class PriceInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    external_key: Key
    source_record_key: str = Field(min_length=1, max_length=250)
    observed_at: AwareDatetime
    bucket_duration: Resolution
    price_kind: PriceKind
    currency: Currency
    minor_units: Count
    volume: Count | None = None
    evidence_url: HttpUrl
    coverage: str = Field(min_length=1, max_length=2000)
    methodology: str = Field(min_length=1, max_length=2000)

    @model_validator(mode='after')
    def time_valid(self):
        self.observed_at = utc(self.observed_at)
        if self.observed_at > datetime.now(timezone.utc):
            raise ValueError('Future observations are not evidence')
        return self


class PriceBatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source_code: Key
    records: list[PriceInput] = Field(min_length=1, max_length=1000)


def authorized(db: Session, code: str, dataset: str) -> Source:
    source = db.scalar(select(Source).join(SourceGrant).where(
        Source.code == code, Source.redistribution_allowed.is_(True), Source.license_status == 'approved',
        SourceGrant.dataset == dataset, SourceGrant.enabled.is_(True)))
    if source is None:
        raise PermissionError('An explicit redistribution grant for this dataset is required')
    return source


def resolve_mapping(db: Session, source: Source, external_key: str) -> Mapping:
    mapping = db.scalar(select(Mapping).where(Mapping.source_id == source.id, Mapping.external_key == external_key))
    if mapping is None:
        raise ImportConflict('Unknown source item key; import verified catalog mapping first')
    return mapping


def import_prices(db: Session, batch: PriceBatch) -> dict:
    source = authorized(db, batch.source_code, 'prices')
    inserted = 0
    for record in batch.records:
        mapping = resolve_mapping(db, source, record.external_key)
        values = record.model_dump(exclude={'external_key'})
        values['evidence_url'] = str(record.evidence_url)
        values.update(item_id=mapping.item_id, variant_id=mapping.variant_id, mapping_id=mapping.id)
        existing = db.scalar(select(Price).where(Price.source_id == source.id,
                                                Price.source_record_key == record.source_record_key))
        if existing:
            for field, value in values.items():
                previous = getattr(existing, field)
                if isinstance(previous, datetime):
                    previous = utc(previous)
                if previous != value:
                    raise ImportConflict('Immutable source record conflicts with existing observation')
            continue
        db.add(Price(id=stable_id('price:' + source.id + ':' + record.source_record_key),
                     source_id=source.id, **values))
        db.flush()
        inserted += 1
    return {'status': 'ok', 'inserted': inserted, 'processed': len(batch.records), 'source': source.code}
