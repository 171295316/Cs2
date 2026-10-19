"""分口径原始供给快照，估算必须有区间和方法依据。"""
import sqlalchemy as sa
from alembic import op

revision = '0004'
down_revision = '0003'


def upgrade():
    op.create_table('supply_snapshots', sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('item_id', sa.String(36), sa.ForeignKey('items.id'), nullable=False),
        sa.Column('variant_id', sa.String(36), sa.ForeignKey('item_variants.id')),
        sa.Column('source_id', sa.String(36), sa.ForeignKey('data_sources.id'), nullable=False),
        sa.Column('mapping_id', sa.String(36), sa.ForeignKey('source_item_mappings.id'), nullable=False),
        sa.Column('measured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metric_type', sa.String(40), nullable=False), sa.Column('quantity', sa.BigInteger, nullable=False),
        sa.Column('methodology_version', sa.String(100), nullable=False),
        sa.Column('coverage_note', sa.Text, nullable=False), sa.Column('sampling_method', sa.Text, nullable=False),
        sa.Column('confidence_low', sa.BigInteger), sa.Column('confidence_high', sa.BigInteger),
        sa.Column('model_evidence_url', sa.Text), sa.Column('evidence_url', sa.Text, nullable=False),
        sa.Column('source_record_key', sa.String(250), nullable=False),
        sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('quantity >= 0'),
        sa.CheckConstraint("metric_type IN ('observed_distinct_instances','public_inventory_units','listed_units','estimated_total_units')"),
        sa.CheckConstraint("metric_type != 'estimated_total_units' OR (confidence_low IS NOT NULL AND confidence_high IS NOT NULL AND model_evidence_url IS NOT NULL AND confidence_low >= 0 AND confidence_low <= quantity AND confidence_high >= quantity)"),
        sa.UniqueConstraint('source_id', 'source_record_key'),
        sa.UniqueConstraint('mapping_id', 'measured_at', 'metric_type', 'methodology_version'))
    for field in ['item_id', 'variant_id', 'source_id', 'measured_at', 'metric_type']:
        op.create_index('ix_supply_snapshots_' + field, 'supply_snapshots', [field])


def downgrade():
    op.drop_table('supply_snapshots')
