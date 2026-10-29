"""Require a non-null role for every staff actor."""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        op.f("ck_workspace_actors_kind_role"), "workspace_actors", type_="check"
    )
    op.create_check_constraint(
        "kind_role",
        "workspace_actors",
        "(kind = 'staff' AND user_id IS NOT NULL AND role IS NOT NULL AND role IN ('admin','agent')) OR (kind IN ('visitor','assistant') AND user_id IS NULL AND role IS NULL)",
    )


def downgrade():
    op.drop_constraint(
        op.f("ck_workspace_actors_kind_role"), "workspace_actors", type_="check"
    )
    op.create_check_constraint(
        "kind_role",
        "workspace_actors",
        "(kind = 'staff' AND user_id IS NOT NULL AND role IN ('admin','agent')) OR (kind IN ('visitor','assistant') AND user_id IS NULL AND role IS NULL)",
    )
