"""Exercise the actual migrated PostgreSQL schema in CI; never seed production."""
import os

import pytest
from app.catalog import CatalogImport, import_catalog
from app.db import SessionLocal, engine
from app.main import app
from app.models import Item
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select


@pytest.mark.skipif(not os.environ.get('DATABASE_URL', '').startswith('postgresql'), reason='requires PostgreSQL')
def test_postgres_migration_and_dependency_readiness():
    inspector = inspect(engine)
    assert {'items', 'item_variants', 'source_item_mappings', 'data_sources', 'import_jobs', 'source_grants', 'price_observations', 'supply_snapshots'} <= set(inspector.get_table_names())
    assert 'ix_prices_series' in {i['name'] for i in inspector.get_indexes('price_observations')}
    assert 'ix_supply_series' in {i['name'] for i in inspector.get_indexes('supply_snapshots')}
    from app.models import Source

    from tests.test_catalog import BATCH
    # Reuse test-only synthetic fixtures inside an uncommitted transaction.
    with SessionLocal() as db:
        source = Source(id='00000000-0000-0000-0000-000000000001', code='test-fixture', name='TEST ONLY',
                        homepage='https://example.invalid', license_status='approved',
                        license_reference='test-only', redistribution_allowed=True)
        db.add(source)
        db.flush()
        import_catalog(db, CatalogImport.model_validate(BATCH))
        assert db.scalar(select(Item).where(Item.name_en == 'TEST ONLY Skin')) is not None
        from app.models import SourceGrant
        from app.observations import PriceBatch, import_prices
        from app.supply import SupplyBatch, import_supply

        from tests.test_prices import RECORD
        from tests.test_supply import SNAPSHOT
        for dataset in ['prices', 'supply']:
            db.add(SourceGrant(id='00000000-0000-0000-0000-00000000000' + ('2' if dataset == 'prices' else '3'),
                               source_id=source.id, dataset=dataset, license_reference='TEST ONLY', enabled=True))
        db.flush()
        prices = PriceBatch.model_validate({'source_code': source.code, 'records': [RECORD]})
        assert import_prices(db, prices)['inserted'] == 1
        assert import_prices(db, prices)['inserted'] == 0
        snapshots = SupplyBatch.model_validate({'source_code': source.code, 'records': [SNAPSHOT]})
        assert import_supply(db, snapshots)['inserted'] == 1
        assert import_supply(db, snapshots)['inserted'] == 0
        db.rollback()
    assert TestClient(app).get('/readyz').status_code == 200
