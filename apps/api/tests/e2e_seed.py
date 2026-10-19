"""显式运行的隔离浏览器测试种子；普通服务启动绝不执行。"""
import os
from datetime import datetime, timedelta, timezone

from app.catalog import CatalogImport, import_catalog, stable_id
from app.db import SessionLocal
from app.models import Source, SourceGrant
from app.observations import PriceBatch, import_prices
from app.supply import SupplyBatch, import_supply
from sqlalchemy.engine import make_url


def main():
    url = make_url(os.environ['DATABASE_URL'])
    database = url.database or ''
    if os.environ.get('CS2_E2E_MODE') != '1' or not (
        database == 'cs2_e2e' or (url.drivername == 'sqlite' and database.endswith('/cs2_e2e.db'))
    ):
        raise RuntimeError('只能向显式命名的隔离 cs2_e2e 测试数据库写入合成记录')
    with SessionLocal.begin() as db:
        source = Source(id=stable_id('source:e2e-fixture'), code='e2e-fixture', name='仅测试演示来源',
                        homepage='https://example.invalid', license_status='approved',
                        license_reference='TEST ONLY synthetic fixture', redistribution_allowed=True)
        db.merge(source)
        db.flush()
        for scope in ['prices', 'supply']:
            db.merge(SourceGrant(id=stable_id('e2e-grant:' + scope), source_id=source.id, dataset=scope,
                                 license_reference='TEST ONLY', enabled=True))
        db.flush()
        batch = CatalogImport.model_validate({'source_code': source.code, 'dataset_revision': 'synthetic-e2e-v1',
            'evidence_url': 'https://example.invalid/test-only', 'verified_at': '2026-01-01T00:00:00Z',
            'items': [{'external_key': 'test-item', 'category': 'skin', 'name_en': 'TEST ONLY <script>alert(1)</script>',
                       'name_zh': '测试专用饰品（演示）', 'variants': [{'external_key': 'test-variant', 'wear': 'test-only'}]}]})
        import_catalog(db, batch)
        common = {'external_key': 'test-item', 'bucket_duration': '1d', 'price_kind': 'sale_median',
                  'currency': 'USD', 'evidence_url': 'https://example.invalid/test-only',
                  'coverage': 'TEST ONLY synthetic record', 'methodology': 'TEST ONLY no market data'}
        import_prices(db, PriceBatch.model_validate({'source_code': source.code, 'records': [
            {**common, 'source_record_key': 'e2e-price-1', 'observed_at': '2026-01-01T00:00:00Z', 'minor_units': 12345},
            {**common, 'source_record_key': 'e2e-price-2', 'observed_at': '2026-01-03T00:00:00Z', 'minor_units': 23456},
            {**common, 'source_record_key': 'e2e-latest', 'observed_at': (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
             'minor_units': 34567}]}))
        import_supply(db, SupplyBatch.model_validate({'source_code': source.code, 'records': [
            {'external_key': 'test-item', 'source_record_key': 'e2e-snapshot', 'measured_at': '2026-01-01T00:00:00Z',
             'metric_type': 'listed_units', 'quantity': 12, 'methodology_version': 'test-v1',
             'coverage_note': 'TEST ONLY synthetic scope', 'sampling_method': 'TEST ONLY synthetic snapshot',
             'evidence_url': 'https://example.invalid/test-only'}]}))


if __name__ == '__main__':
    main()
