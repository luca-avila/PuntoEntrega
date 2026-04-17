"""Create notification outbox events table.

Revision ID: 0008_create_notification_outbox_events
Revises: 0007_product_request_items_and_optional_message
Create Date: 2026-04-14 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0008_create_notification_outbox_events"
down_revision: str | None = "0007_product_request_items_and_optional_message"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    notification_outbox_status_enum = sa.Enum(
        "pending",
        "processing",
        "processed",
        "failed",
        name="notification_outbox_status_enum",
        native_enum=False,
        create_constraint=True,
    )

    op.create_table(
        "notification_outbox_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("aggregate_type", sa.String(length=80), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            notification_outbox_status_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default=sa.text("5")),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=120), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("deduplication_key", sa.String(length=255), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deduplication_key"),
    )
    op.create_index(
        op.f("ix_notification_outbox_events_event_type"),
        "notification_outbox_events",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notification_outbox_events_organization_id"),
        "notification_outbox_events",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_notification_outbox_events_status_available_at",
        "notification_outbox_events",
        ["status", "available_at"],
        unique=False,
    )
    op.create_index(
        "ix_notification_outbox_events_aggregate",
        "notification_outbox_events",
        ["aggregate_type", "aggregate_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_notification_outbox_events_aggregate", table_name="notification_outbox_events")
    op.drop_index(
        "ix_notification_outbox_events_status_available_at",
        table_name="notification_outbox_events",
    )
    op.drop_index(
        op.f("ix_notification_outbox_events_organization_id"),
        table_name="notification_outbox_events",
    )
    op.drop_index(
        op.f("ix_notification_outbox_events_event_type"),
        table_name="notification_outbox_events",
    )
    op.drop_table("notification_outbox_events")
