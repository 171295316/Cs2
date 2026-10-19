"""Normalized, provenance-preserving catalog import; no network scraping."""
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import NAMESPACE_URL, uuid5

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Item, Mapping, Source, Variant

Category = Literal['skin', 'knife', 'glove', 'case', 'collection_package', 'sticker', 'capsule',
                   'agent', 'music_kit', 'keychain', 'graffiti', 'patch', 'tool', 'other']
Key = Annotated[str, Field(min_length=1, max_length=90, pattern=r'^[a-zA-Z0-9_.:/-]+$')]


def stable_id(key: str) -> str:
    return str(uuid5(NAMESPACE_URL, 'cs2-market:' + key))


class VariantInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    external_key: Key
    wear: str | None = Field(None, max_length=100)
    stattrak: bool | None = None
    souvenir: bool | None = None
    paint_index: int | None = Field(None, ge=0)
    market_hash_name: str | None = Field(None, max_length=500)


class ItemInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    external_key: Key
    category: Category
    name_en: str = Field(min_length=1, max_length=500)
    name_zh: str | None = Field(None, max_length=500)
    market_hash_name: str | None = Field(None, max_length=500)
    image_url: HttpUrl | None = None
    tradable: bool | None = None
    marketable: bool | None = None
    variants: list[VariantInput] = Field(default_factory=list, max_length=500)


class CatalogImport(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source_code: Key
    dataset_revision: str = Field(min_length=1, max_length=250)
    evidence_url: HttpUrl
    verified_at: AwareDatetime
    items: list[ItemInput] = Field(min_length=1, max_length=1000)

    @model_validator(mode='after')
    def unique_keys(self):
        keys = [i.external_key for i in self.items]
        keys += [v.external_key for i in self.items for v in i.variants]
        if len(keys) != len(set(keys)):
            raise ValueError('duplicate source external keys in batch')
        if self.verified_at > datetime.now(timezone.utc):
            raise ValueError('verification date cannot be in the future')
        self.verified_at = self.verified_at.astimezone(timezone.utc)
        return self


class ImportConflict(ValueError):
    pass


def import_catalog(db: Session, batch: CatalogImport) -> dict:
    source = db.scalar(select(Source).where(Source.code == batch.source_code))
    if source is None or source.redistribution_allowed is not True or source.license_status != 'approved':
        raise PermissionError('Source requires server-side approval and redistribution evidence')
    for record in batch.items:
        key = source.code + ':' + record.external_key
        item_id = stable_id('item:' + key)
        item = db.get(Item, item_id)
        values = record.model_dump(exclude={'variants', 'external_key', 'image_url'})
        values['image_url'] = str(record.image_url) if record.image_url else None
        if item is None:
            item = Item(id=item_id, canonical_key=key, **values)
            db.add(item)
        else:
            for field, value in values.items():
                setattr(item, field, value)
            item.updated_at = datetime.now(timezone.utc)
        db.flush()
        map_record(db, source, batch, record.external_key, item_id, None)
        for variant in record.variants:
            variant_key = key + ':' + variant.external_key
            variant_id = stable_id('variant:' + variant_key)
            existing = db.get(Variant, variant_id)
            values = variant.model_dump(exclude={'external_key'})
            if existing is None:
                db.add(Variant(id=variant_id, item_id=item_id, variant_key=variant_key, **values))
            else:
                for field, value in values.items():
                    setattr(existing, field, value)
            db.flush()
            map_record(db, source, batch, variant.external_key, item_id, variant_id)
    db.flush()
    return {'status': 'ok', 'processed': len(batch.items), 'source': source.code,
            'dataset_revision': batch.dataset_revision, 'as_of': batch.verified_at}


def map_record(db: Session, source: Source, batch: CatalogImport, external_key: str,
               item_id: str, variant_id: str | None) -> None:
    mapping = db.scalar(select(Mapping).where(Mapping.source_id == source.id, Mapping.external_key == external_key))
    if mapping and (mapping.item_id != item_id or mapping.variant_id != variant_id):
        raise ImportConflict('Source key is already assigned to a different item or variant')
    if mapping:
        # Never overwrite newer provenance with an older batch.
        previous = mapping.verified_at.replace(tzinfo=timezone.utc)
        if batch.verified_at < previous:
            raise ImportConflict('Stale import would overwrite newer provenance')
    else:
        mapping = Mapping(id=stable_id('mapping:' + source.code + ':' + external_key),
                          source_id=source.id, external_key=external_key, item_id=item_id, variant_id=variant_id)
        db.add(mapping)
    mapping.verified_at = batch.verified_at
    mapping.dataset_revision = batch.dataset_revision
    mapping.evidence_url = str(batch.evidence_url)
