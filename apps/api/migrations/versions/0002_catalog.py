"""Stable catalog, variants, licensed sources and provenance mappings."""
import sqlalchemy as sa
from alembic import op

revision = '0002'
down_revision = '0001'


def upgrade():
    op.create_table('items',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('canonical_key', sa.String(250), nullable=False, unique=True),
        sa.Column('category', sa.String(40), nullable=False),
        sa.Column('name_zh', sa.String(500)), sa.Column('name_en', sa.String(500), nullable=False),
        sa.Column('market_hash_name', sa.String(500)), sa.Column('image_url', sa.Text),
        sa.Column('attributes_json', sa.JSON, nullable=False),
        sa.Column('tradable', sa.Boolean), sa.Column('marketable', sa.Boolean),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_items_category', 'items', ['category'])
    op.create_index('ix_items_name_en', 'items', ['name_en'])
    op.create_table('item_variants',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('item_id', sa.String(36), sa.ForeignKey('items.id'), nullable=False),
        sa.Column('variant_key', sa.String(300), nullable=False, unique=True),
        sa.Column('market_hash_name', sa.String(500)), sa.Column('wear', sa.String(100)),
        sa.Column('stattrak', sa.Boolean), sa.Column('souvenir', sa.Boolean),
        sa.Column('paint_index', sa.Integer), sa.Column('attributes_json', sa.JSON, nullable=False))
    op.create_index('ix_item_variants_item_id', 'item_variants', ['item_id'])
    op.create_table('data_sources',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('code', sa.String(100), nullable=False, unique=True),
        sa.Column('name', sa.String(250), nullable=False), sa.Column('homepage', sa.Text, nullable=False),
        sa.Column('license_status', sa.String(100), nullable=False),
        sa.Column('license_reference', sa.Text, nullable=False), sa.Column('redistribution_allowed', sa.Boolean),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False))
    op.create_table('source_item_mappings',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('item_id', sa.String(36), sa.ForeignKey('items.id'), nullable=False),
        sa.Column('variant_id', sa.String(36), sa.ForeignKey('item_variants.id')),
        sa.Column('source_id', sa.String(36), sa.ForeignKey('data_sources.id'), nullable=False),
        sa.Column('external_key', sa.String(300), nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('dataset_revision', sa.String(250), nullable=False),
        sa.Column('evidence_url', sa.Text, nullable=False), sa.UniqueConstraint('source_id', 'external_key'))
    for field in ['item_id', 'variant_id', 'source_id']:
        op.create_index('ix_source_item_mappings_' + field, 'source_item_mappings', [field])


def downgrade():
    for table in ['source_item_mappings', 'data_sources', 'item_variants', 'items']:
        op.drop_table(table)
