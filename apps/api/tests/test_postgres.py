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
    assert {'items', 'item_variants', 'source_item_mappings', 'data_sources', 'import_jobs'} <= set(inspector.get_table_names())
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
        db.rollback()
    assert TestClient(app).get('/readyz').status_code == 200
