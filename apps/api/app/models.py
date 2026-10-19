from datetime import datetime, timezone

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class Item(Base):
    __tablename__ = 'items'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    canonical_key: Mapped[str] = mapped_column(String(250), unique=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    name_zh: Mapped[str | None] = mapped_column(String(500))
    name_en: Mapped[str] = mapped_column(String(500), index=True)
    market_hash_name: Mapped[str | None] = mapped_column(String(500))
    image_url: Mapped[str | None] = mapped_column(Text)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict)
    tradable: Mapped[bool | None] = mapped_column(Boolean)
    marketable: Mapped[bool | None] = mapped_column(Boolean)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Variant(Base):
    __tablename__ = 'item_variants'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    item_id: Mapped[str] = mapped_column(ForeignKey('items.id'), index=True)
    variant_key: Mapped[str] = mapped_column(String(300), unique=True)
    market_hash_name: Mapped[str | None] = mapped_column(String(500))
    wear: Mapped[str | None] = mapped_column(String(100))
    stattrak: Mapped[bool | None] = mapped_column(Boolean)
    souvenir: Mapped[bool | None] = mapped_column(Boolean)
    paint_index: Mapped[int | None]
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict)


class Source(Base):
    __tablename__ = 'data_sources'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(250))
    homepage: Mapped[str] = mapped_column(Text)
    license_status: Mapped[str] = mapped_column(String(100))
    license_reference: Mapped[str] = mapped_column(Text)
    redistribution_allowed: Mapped[bool | None] = mapped_column(Boolean)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Mapping(Base):
    __tablename__ = 'source_item_mappings'
    __table_args__ = (UniqueConstraint('source_id', 'external_key'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    item_id: Mapped[str] = mapped_column(ForeignKey('items.id'), index=True)
    variant_id: Mapped[str | None] = mapped_column(ForeignKey('item_variants.id'), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey('data_sources.id'), index=True)
    external_key: Mapped[str] = mapped_column(String(300))
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    dataset_revision: Mapped[str] = mapped_column(String(250))
    evidence_url: Mapped[str] = mapped_column(Text)


class SourceGrant(Base):
    __tablename__ = 'source_grants'
    __table_args__ = (UniqueConstraint('source_id', 'dataset'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey('data_sources.id'), index=True)
    dataset: Mapped[str] = mapped_column(String(20))
    license_reference: Mapped[str] = mapped_column(Text)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)


class Price(Base):
    __tablename__ = 'price_observations'
    __table_args__ = (UniqueConstraint('source_id', 'source_record_key'),
                     UniqueConstraint('mapping_id', 'observed_at', 'price_kind', 'currency', 'bucket_duration'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    item_id: Mapped[str] = mapped_column(ForeignKey('items.id'), index=True)
    variant_id: Mapped[str | None] = mapped_column(ForeignKey('item_variants.id'), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey('data_sources.id'), index=True)
    mapping_id: Mapped[str] = mapped_column(ForeignKey('source_item_mappings.id'))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    bucket_duration: Mapped[str] = mapped_column(String(10))
    price_kind: Mapped[str] = mapped_column(String(30))
    currency: Mapped[str] = mapped_column(String(3))
    minor_units: Mapped[int] = mapped_column(BigInteger)
    volume: Mapped[int | None] = mapped_column(BigInteger)
    source_record_key: Mapped[str] = mapped_column(String(250))
    evidence_url: Mapped[str] = mapped_column(Text)
    coverage: Mapped[str] = mapped_column(Text)
    methodology: Mapped[str] = mapped_column(Text)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Supply(Base):
    __tablename__ = 'supply_snapshots'
    __table_args__ = (UniqueConstraint('source_id', 'source_record_key'),
                     UniqueConstraint('mapping_id', 'measured_at', 'metric_type', 'methodology_version'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    item_id: Mapped[str] = mapped_column(ForeignKey('items.id'), index=True)
    variant_id: Mapped[str | None] = mapped_column(ForeignKey('item_variants.id'), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey('data_sources.id'), index=True)
    mapping_id: Mapped[str] = mapped_column(ForeignKey('source_item_mappings.id'))
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    metric_type: Mapped[str] = mapped_column(String(40), index=True)
    quantity: Mapped[int] = mapped_column(BigInteger)
    methodology_version: Mapped[str] = mapped_column(String(100))
    coverage_note: Mapped[str] = mapped_column(Text)
    sampling_method: Mapped[str] = mapped_column(Text)
    confidence_low: Mapped[int | None] = mapped_column(BigInteger)
    confidence_high: Mapped[int | None] = mapped_column(BigInteger)
    model_evidence_url: Mapped[str | None] = mapped_column(Text)
    evidence_url: Mapped[str] = mapped_column(Text)
    source_record_key: Mapped[str] = mapped_column(String(250))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
