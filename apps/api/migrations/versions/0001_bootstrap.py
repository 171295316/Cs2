"""Initialize engineering schema."""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None


def upgrade():
    op.create_table("import_jobs", sa.Column("id", sa.String(36), primary_key=True),
                    sa.Column("provider", sa.String(100), nullable=False),
                    sa.Column("job_type", sa.String(30), nullable=False),
                    sa.Column("status", sa.String(30), nullable=False),
                    sa.Column("cursor", sa.Text),
                    sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
                    sa.Column("started_at", sa.DateTime(timezone=True)),
                    sa.Column("completed_at", sa.DateTime(timezone=True)),
                    sa.Column("error_summary", sa.Text))


def downgrade():
    op.drop_table("import_jobs")
