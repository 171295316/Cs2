"""Scoped redistribution grants and immutable price observations."""
import sqlalchemy as sa
from alembic import op

revision = '0003'
down_revision = '0002'


def upgrade():
    op.create_table('source_grants', sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('source_id', sa.String(36), sa.ForeignKey('data_sources.id'), nullable=False),
        sa.Column('dataset', sa.String(20), nullable=False), sa.Column('license_reference', sa.Text, nullable=False),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('enabled', sa.Boolean, nullable=False), sa.UniqueConstraint('source_id', 'dataset'))
    op.create_index('ix_source_grants_source_id', 'source_grants', ['source_id'])
    op.create_table('price_observations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('item_id', sa.String(36), sa.ForeignKey('items.id'), nullable=False),
        sa.Column('variant_id', sa.String(36), sa.ForeignKey('item_variants.id')),
        sa.Column('source_id', sa.String(36), sa.ForeignKey('data_sources.id'), nullable=False),
        sa.Column('mapping_id', sa.String(36), sa.ForeignKey('source_item_mappings.id'), nullable=False),
        sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('bucket_duration', sa.String(10), nullable=False),
        sa.Column('price_kind', sa.String(30), nullable=False), sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('minor_units', sa.BigInteger, nullable=False), sa.Column('volume', sa.BigInteger),
        sa.Column('source_record_key', sa.String(250), nullable=False),
        sa.Column('evidence_url', sa.Text, nullable=False), sa.Column('coverage', sa.Text, nullable=False),
        sa.Column('methodology', sa.Text, nullable=False),
        sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('minor_units >= 0 AND (volume IS NULL OR volume >= 0)'),
        sa.CheckConstraint("price_kind IN ('sale_median','ask_min','bid_max')"),
        sa.CheckConstraint("bucket_duration IN ('1h','1d')"),
        sa.UniqueConstraint('source_id', 'source_record_key'),
        sa.UniqueConstraint('mapping_id', 'observed_at', 'price_kind', 'currency', 'bucket_duration'))
    for field in ['item_id', 'variant_id', 'source_id', 'observed_at']:
        op.create_index('ix_price_observations_' + field, 'price_observations', [field])


def downgrade():
    op.drop_table('price_observations')
    op.drop_table('source_grants')
