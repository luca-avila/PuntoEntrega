"""Add product request items and make product request message optional.

Revision ID: 0007_product_request_items_and_optional_message
Revises: 0006_memberships_location_scoping_cutover
Create Date: 2026-03-26 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0007_product_request_items_and_optional_message"
down_revision: str | None = "0006_memberships_location_scoping_cutover"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("product_requests", schema=None) as batch_op:
        batch_op.alter_column(
            "message",
            existing_type=sa.Text(),
            nullable=True,
        )

    op.create_table(
        "product_request_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_request_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_product_request_items_quantity_gt_zero"),
        sa.ForeignKeyConstraint(["product_request_id"], ["product_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "product_request_id",
            "product_id",
            name="uq_product_request_items_request_product",
        ),
    )
    op.create_index(
        op.f("ix_product_request_items_product_request_id"),
        "product_request_items",
        ["product_request_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_request_items_product_id"),
        "product_request_items",
        ["product_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_product_request_items_product_id"), table_name="product_request_items")
    op.drop_index(op.f("ix_product_request_items_product_request_id"), table_name="product_request_items")
    op.drop_table("product_request_items")

    op.execute(sa.text("UPDATE product_requests SET message = '' WHERE message IS NULL"))
    with op.batch_alter_table("product_requests", schema=None) as batch_op:
        batch_op.alter_column(
            "message",
            existing_type=sa.Text(),
            nullable=False,
        )
