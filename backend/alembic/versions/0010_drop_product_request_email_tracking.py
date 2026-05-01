"""Drop product request email tracking columns.

Revision ID: 0010_drop_product_request_email_tracking
Revises: 0009_drop_delivery_email_status
Create Date: 2026-05-01 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0010_drop_product_request_email_tracking"
down_revision: str | None = "0009_drop_delivery_email_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    product_request_columns = {
        column["name"] for column in inspector.get_columns("product_requests")
    }
    if "email_status" not in product_request_columns:
        return

    product_request_indexes = {
        index["name"] for index in inspector.get_indexes("product_requests")
    }
    product_request_check_constraints = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("product_requests")
    }

    with op.batch_alter_table("product_requests") as batch_op:
        if "ix_product_requests_email_status" in product_request_indexes:
            batch_op.drop_index("ix_product_requests_email_status")
        if "product_request_email_status_enum" in product_request_check_constraints:
            batch_op.drop_constraint(
                "product_request_email_status_enum",
                type_="check",
            )
        batch_op.drop_column("email_status")
        if "email_attempts" in product_request_columns:
            batch_op.drop_column("email_attempts")
        if "email_last_error" in product_request_columns:
            batch_op.drop_column("email_last_error")
        if "email_sent_at" in product_request_columns:
            batch_op.drop_column("email_sent_at")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    product_request_columns = {
        column["name"] for column in inspector.get_columns("product_requests")
    }
    if "email_status" in product_request_columns:
        return

    product_request_email_status_enum = sa.Enum(
        "pending",
        "sent",
        "failed",
        name="product_request_email_status_enum",
        native_enum=False,
        create_constraint=True,
    )

    with op.batch_alter_table("product_requests") as batch_op:
        batch_op.add_column(
            sa.Column(
                "email_status",
                product_request_email_status_enum,
                nullable=False,
                server_default="pending",
            )
        )
        batch_op.add_column(
            sa.Column(
                "email_attempts",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "email_last_error",
                sa.Text(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "email_sent_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.create_index(
            "ix_product_requests_email_status",
            ["email_status"],
            unique=False,
        )
