"""Fix auth user table name mismatch.

Revision ID: 0002_fix_auth_user_table_name
Revises: 0001_multitenant_core_models
Create Date: 2026-03-18 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002_fix_auth_user_table_name"
down_revision: str | None = "0001_multitenant_core_models"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    has_user_table = inspector.has_table("user")
    has_users_table = inspector.has_table("users")

    # SQLAlchemy/FastAPI Users defaults to "user" for the auth table.
    # Keep this migration idempotent for environments that already have it.
    if has_users_table and not has_user_table:
        op.rename_table("users", "user")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    has_user_table = inspector.has_table("user")
    has_users_table = inspector.has_table("users")

    if has_user_table and not has_users_table:
        op.rename_table("user", "users")
