import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    transaction_type = postgresql.ENUM(
        "CREDIT",
        "DEBIT",
        name="transaction_type",
        create_type=False,
    )

    balance_reason = postgresql.ENUM(
        "TOPUP",
        "GENERATION",
        "REFUND",
        name="balance_reason",
        create_type=False,
    )

    generation_kind = postgresql.ENUM(
        "TEXT_TO_IMAGE",
        "IMAGE_TO_IMAGE",
        "TEXT_TO_VIDEO",
        "IMAGE_TO_VIDEO",
        name="generation_kind",
        create_type=False,
    )

    generation_status = postgresql.ENUM(
        "QUEUED",
        "SUBMITTED",
        "IN_QUEUE",
        "IN_PROGRESS",
        "COMPLETED",
        "FAILED",
        "CANCELED",
        name="generation_status",
        create_type=False,
    )

    bind = op.get_bind()
    transaction_type.create(bind, checkfirst=True)
    balance_reason.create(bind, checkfirst=True)
    generation_kind.create(bind, checkfirst=True)
    generation_status.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "external_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
        ),
        sa.Column("api_key_hash", sa.Text(), nullable=True),
        sa.Column(
            "api_key_fingerprint",
            sa.String(length=128),
            nullable=True,
            unique=True,
        ),
        sa.Column(
            "balance_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "balance_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", transaction_type, nullable=False),
        sa.Column("reason", balance_reason, nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("external_ref", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_index(
        "ix_balance_transactions_external_ref_topup_unique",
        "balance_transactions",
        ["external_ref"],
        unique=True,
        postgresql_where=sa.text(
            "reason = 'TOPUP' AND external_ref IS NOT NULL"
        ),
    )

    op.create_table(
        "generation_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", generation_kind, nullable=False),
        sa.Column("model_id", sa.String(length=255), nullable=False),
        sa.Column("fal_request_id", sa.String(length=255), nullable=True),
        sa.Column("status", generation_status, nullable=False),
        sa.Column("cost_tokens", sa.Integer(), nullable=False),
        sa.Column("input_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index(
        "ix_balance_transactions_external_ref_topup_unique",
        table_name="balance_transactions",
    )

    op.drop_table("generation_jobs")
    op.drop_table("balance_transactions")
    op.drop_table("users")

    generation_status = postgresql.ENUM(name="generation_status")
    generation_kind = postgresql.ENUM(name="generation_kind")
    balance_reason = postgresql.ENUM(name="balance_reason")
    transaction_type = postgresql.ENUM(name="transaction_type")

    generation_status.drop(bind, checkfirst=True)
    generation_kind.drop(bind, checkfirst=True)
    balance_reason.drop(bind, checkfirst=True)
    transaction_type.drop(bind, checkfirst=True)
