"""Shared provider budget, explicit fixture identity and bounded inbox search."""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workspaces",
        sa.Column(
            "fictional_data", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.execute(
        "UPDATE workspaces SET fictional_data = true WHERE expires_at IS NOT NULL OR public_key IN ('naran-demo', 'tarvio-demo', 'other-demo')"
    )
    op.alter_column("workspaces", "fictional_data", server_default=None)
    op.create_table(
        "provider_usage_periods",
        sa.Column("period", sa.Date(), primary_key=True),
        sa.Column("charged_tokens", sa.Integer(), nullable=False),
    )
    op.execute(
        "INSERT INTO provider_usage_periods SELECT period, SUM(charged_tokens) FROM usage_periods GROUP BY period"
    )
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_index(
        "ix_message_body_search",
        "messages",
        ["body"],
        postgresql_using="gin",
        postgresql_ops={"body": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_inbox_activity_cursor",
        "conversations",
        ["workspace_id", sa.text("updated_at DESC"), sa.text("id DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_inbox_activity_cursor", table_name="conversations")
    op.drop_index("ix_message_body_search", table_name="messages")
    op.drop_table("provider_usage_periods")
    op.drop_column("workspaces", "fictional_data")
