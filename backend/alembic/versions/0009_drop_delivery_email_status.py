"""Drop delivery email status.

Revision ID: 0009_drop_delivery_email_status
Revises: 0008_create_notification_outbox_events
Create Date: 2026-04-16 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0009_drop_delivery_email_status"
down_revision: str | None = "0008_create_notification_outbox_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    delivery_columns = {column["name"] for column in inspector.get_columns("deliveries")}
    if "email_status" not in delivery_columns:
        return
    delivery_check_constraints = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("deliveries")
    }

    with op.batch_alter_table("deliveries") as batch_op:
        if "email_status_enum" in delivery_check_constraints:
            batch_op.drop_constraint("email_status_enum", type_="check")
        batch_op.drop_column("email_status")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    delivery_columns = {column["name"] for column in inspector.get_columns("deliveries")}
    if "email_status" in delivery_columns:
        return

    email_status_enum = sa.Enum(
        "pending",
        "sent",
        "failed",
        name="email_status_enum",
        native_enum=False,
        create_constraint=True,
    )
    with op.batch_alter_table("deliveries") as batch_op:
        batch_op.add_column(
            sa.Column(
                "email_status",
                email_status_enum,
                server_default="pending",
                nullable=False,
            )
        )
