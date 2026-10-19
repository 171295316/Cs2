"""时间序列和排行的复合查询索引。"""
from alembic import op

revision = '0005'
down_revision = '0004'


def upgrade():
    op.create_index('ix_prices_series', 'price_observations',
                    ['item_id', 'variant_id', 'source_id', 'currency', 'price_kind', 'bucket_duration', 'observed_at'])
    op.create_index('ix_supply_series', 'supply_snapshots',
                    ['item_id', 'variant_id', 'source_id', 'metric_type', 'methodology_version', 'measured_at'])


def downgrade():
    op.drop_index('ix_supply_series', 'supply_snapshots')
    op.drop_index('ix_prices_series', 'price_observations')
