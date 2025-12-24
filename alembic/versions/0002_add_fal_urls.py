import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "generation_jobs",
        sa.Column("status_url", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "generation_jobs",
        sa.Column("response_url", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "generation_jobs",
        sa.Column("cancel_url", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("generation_jobs", "cancel_url")
    op.drop_column("generation_jobs", "response_url")
    op.drop_column("generation_jobs", "status_url")
