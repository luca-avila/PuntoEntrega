"""Create product requests table.

Revision ID: 0005_create_product_requests
Revises: 0004_create_organization_invitations
Create Date: 2026-03-25 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0005_create_product_requests"
down_revision: str | None = "0004_create_organization_invitations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    product_request_email_status_enum = sa.Enum(
        "pending",
        "sent",
        "failed",
        name="product_request_email_status_enum",
        native_enum=False,
        create_constraint=True,
    )

    op.create_table(
        "product_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "email_status",
            product_request_email_status_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("email_attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("email_last_error", sa.Text(), nullable=True),
        sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_product_requests_organization_id"),
        "product_requests",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_requests_requested_by_user_id"),
        "product_requests",
        ["requested_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_requests_email_status"),
        "product_requests",
        ["email_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_product_requests_email_status"), table_name="product_requests")
    op.drop_index(op.f("ix_product_requests_requested_by_user_id"), table_name="product_requests")
    op.drop_index(op.f("ix_product_requests_organization_id"), table_name="product_requests")
    op.drop_table("product_requests")
