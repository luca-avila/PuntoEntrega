"""Add organization ownership and drop user role.

Revision ID: 0003_organizations_owner_and_drop_user_role
Revises: 0002_fix_auth_user_table_name
Create Date: 2026-03-25 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0003_organizations_owner_and_drop_user_role"
down_revision: str | None = "0002_fix_auth_user_table_name"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("organizations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("owner_user_id", sa.Uuid(), nullable=False))
        batch_op.create_foreign_key(
            "fk_organizations_owner_user_id_user",
            "user",
            ["owner_user_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index(
            op.f("ix_organizations_owner_user_id"),
            ["owner_user_id"],
            unique=False,
        )

    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("role")


def downgrade() -> None:
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("role", sa.String(length=50), nullable=True))

    with op.batch_alter_table("organizations", schema=None) as batch_op:
        batch_op.drop_index(op.f("ix_organizations_owner_user_id"))
        batch_op.drop_constraint("fk_organizations_owner_user_id_user", type_="foreignkey")
        batch_op.drop_column("owner_user_id")
