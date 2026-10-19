"""人工核实的跨平台 ID 对齐，不依据展示名称自动猜测。"""
import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, model_validator
from sqlalchemy import select

from app.catalog import ImportConflict, Key, stable_id
from app.jobs import run_import
from app.models import Item, Mapping, Source, Variant
from app.observations import utc
from app.routes import DB, authenticate

router = APIRouter()


class MappingInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    external_key: Key
    item_id: UUID
    variant_id: UUID | None = None


class MappingBatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source_code: Key
    verified_at: AwareDatetime
    dataset_revision: str = Field(min_length=1, max_length=250)
    evidence_url: HttpUrl
    mappings: list[MappingInput] = Field(min_length=1, max_length=1000)

    @model_validator(mode='after')
    def verified(self):
        self.verified_at = utc(self.verified_at)
        if self.verified_at > datetime.now(timezone.utc):
            raise ValueError('核验时间不能是未来')
        keys = [r.external_key for r in self.mappings]
        if len(keys) != len(set(keys)):
            raise ValueError('同一批次不能重复映射来源键')
        return self


def import_mappings(db, batch: MappingBatch):
    source = db.scalar(select(Source).where(Source.code == batch.source_code,
                       Source.redistribution_allowed.is_(True), Source.license_status == 'approved'))
    if source is None:
        raise PermissionError('来源未获审批')
    for record in batch.mappings:
        item_id = str(record.item_id)
        variant_id = str(record.variant_id) if record.variant_id else None
        if db.get(Item, item_id) is None:
            raise ImportConflict('基础物品不存在')
        if variant_id:
            variant = db.get(Variant, variant_id)
            if variant is None or variant.item_id != item_id:
                raise ImportConflict('变体不属于该基础物品')
        row = db.scalar(select(Mapping).where(Mapping.source_id == source.id,
                                             Mapping.external_key == record.external_key))
        if row:
            if (row.item_id, row.variant_id) != (item_id, variant_id) or utc(row.verified_at) > batch.verified_at:
                raise ImportConflict('已有映射冲突或新核验时间过早，不能重新绑定')
        else:
            row = Mapping(id=stable_id('mapping:' + json.dumps([source.code, record.external_key], separators=(',', ':'))),
                          source_id=source.id, external_key=record.external_key,
                          item_id=item_id, variant_id=variant_id)
            db.add(row)
        row.verified_at = batch.verified_at
        row.dataset_revision = batch.dataset_revision
        row.evidence_url = str(batch.evidence_url)
        db.flush()
    return {'status': 'ok', 'processed': len(batch.mappings), 'source': source.code}


@router.post('/internal/import/mappings', dependencies=[Depends(authenticate)])
def ingest(batch: MappingBatch, db: DB):
    return run_import(db, batch.source_code, 'mappings', lambda: import_mappings(db, batch))
