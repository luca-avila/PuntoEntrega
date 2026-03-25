"""Create organization invitations table.

Revision ID: 0004_create_organization_invitations
Revises: 0003_organizations_owner_and_drop_user_role
Create Date: 2026-03-25 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0004_create_organization_invitations"
down_revision: str | None = "0003_organizations_owner_and_drop_user_role"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    invitation_status_enum = sa.Enum(
        "pending",
        "accepted",
        "expired",
        "cancelled",
        name="organization_invitation_status_enum",
        native_enum=False,
        create_constraint=True,
    )

    op.create_table(
        "organization_invitations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("invited_email", sa.String(length=320), nullable=False),
        sa.Column("invited_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("status", invitation_status_enum, nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_organization_invitations_organization_id"),
        "organization_invitations",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_organization_invitations_invited_email"),
        "organization_invitations",
        ["invited_email"],
        unique=False,
    )
    op.create_index(
        op.f("ix_organization_invitations_invited_by_user_id"),
        "organization_invitations",
        ["invited_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_organization_invitations_status"),
        "organization_invitations",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_organization_invitations_expires_at"),
        "organization_invitations",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_organization_invitations_expires_at"), table_name="organization_invitations")
    op.drop_index(op.f("ix_organization_invitations_status"), table_name="organization_invitations")
    op.drop_index(op.f("ix_organization_invitations_invited_by_user_id"), table_name="organization_invitations")
    op.drop_index(op.f("ix_organization_invitations_invited_email"), table_name="organization_invitations")
    op.drop_index(op.f("ix_organization_invitations_organization_id"), table_name="organization_invitations")
    op.drop_table("organization_invitations")
