"""Add multi-tenant core models.

Revision ID: 0001_multitenant_core_models
Revises:
Create Date: 2026-03-16 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001_multitenant_core_models"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    payment_method_enum = sa.Enum(
        "cash",
        "transfer",
        "current_account",
        "other",
        name="payment_method_enum",
        native_enum=False,
        create_constraint=True,
    )
    email_status_enum = sa.Enum(
        "pending",
        "sent",
        "failed",
        name="email_status_enum",
        native_enum=False,
        create_constraint=True,
    )

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("organizations"):
        op.create_table(
            "organizations",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("slug", sa.String(length=120), nullable=False),
            sa.Column("subscription_status", sa.String(length=50), nullable=True),
            sa.Column("plan_code", sa.String(length=50), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
            sa.UniqueConstraint("slug"),
        )

    inspector = sa.inspect(bind)
    users_table_exists = inspector.has_table("users")

    if not users_table_exists:
        op.create_table(
            "users",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("email", sa.String(length=320), nullable=False),
            sa.Column("hashed_password", sa.String(length=1024), nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
            sa.Column("is_superuser", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.Column("is_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.Column("organization_id", sa.Uuid(), nullable=True),
            sa.Column("role", sa.String(length=50), nullable=True),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name="fk_users_organization_id_organizations",
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
        op.create_index(op.f("ix_users_organization_id"), "users", ["organization_id"], unique=False)
    else:
        existing_user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "organization_id" not in existing_user_columns:
            op.add_column("users", sa.Column("organization_id", sa.Uuid(), nullable=True))
            op.create_index(op.f("ix_users_organization_id"), "users", ["organization_id"], unique=False)

        if "role" not in existing_user_columns:
            op.add_column("users", sa.Column("role", sa.String(length=50), nullable=True))

        # SQLite cannot add foreign keys to existing tables via ALTER TABLE.
        if bind.dialect.name != "sqlite":
            op.create_foreign_key(
                "fk_users_organization_id_organizations",
                "users",
                "organizations",
                ["organization_id"],
                ["id"],
                ondelete="SET NULL",
            )

    inspector = sa.inspect(bind)
    if not inspector.has_table("locations"):
        op.create_table(
            "locations",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("organization_id", sa.Uuid(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("address", sa.String(length=500), nullable=False),
            sa.Column("contact_name", sa.String(length=255), nullable=True),
            sa.Column("contact_phone", sa.String(length=50), nullable=True),
            sa.Column("contact_email", sa.String(length=320), nullable=True),
            sa.Column("latitude", sa.Float(), nullable=False),
            sa.Column("longitude", sa.Float(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
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
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_locations_organization_id"), "locations", ["organization_id"], unique=False)

    inspector = sa.inspect(bind)
    if not inspector.has_table("products"):
        op.create_table(
            "products",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("organization_id", sa.Uuid(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_products_organization_id"), "products", ["organization_id"], unique=False)

    inspector = sa.inspect(bind)
    if not inspector.has_table("deliveries"):
        op.create_table(
            "deliveries",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("organization_id", sa.Uuid(), nullable=False),
            sa.Column("location_id", sa.Uuid(), nullable=False),
            sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("payment_method", payment_method_enum, nullable=False),
            sa.Column("payment_notes", sa.Text(), nullable=True),
            sa.Column("observations", sa.Text(), nullable=True),
            sa.Column("email_status", email_status_enum, server_default="pending", nullable=False),
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
            sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_deliveries_location_id"), "deliveries", ["location_id"], unique=False)
        op.create_index(op.f("ix_deliveries_organization_id"), "deliveries", ["organization_id"], unique=False)

    inspector = sa.inspect(bind)
    if not inspector.has_table("delivery_items"):
        op.create_table(
            "delivery_items",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("delivery_id", sa.Uuid(), nullable=False),
            sa.Column("product_id", sa.Uuid(), nullable=False),
            sa.Column("quantity", sa.Numeric(precision=10, scale=2), nullable=False),
            sa.CheckConstraint("quantity > 0", name="ck_delivery_items_quantity_gt_zero"),
            sa.ForeignKeyConstraint(["delivery_id"], ["deliveries.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_delivery_items_delivery_id"), "delivery_items", ["delivery_id"], unique=False)
        op.create_index(op.f("ix_delivery_items_product_id"), "delivery_items", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_delivery_items_product_id"), table_name="delivery_items")
    op.drop_index(op.f("ix_delivery_items_delivery_id"), table_name="delivery_items")
    op.drop_table("delivery_items")

    op.drop_index(op.f("ix_deliveries_organization_id"), table_name="deliveries")
    op.drop_index(op.f("ix_deliveries_location_id"), table_name="deliveries")
    op.drop_table("deliveries")

    op.drop_index(op.f("ix_products_organization_id"), table_name="products")
    op.drop_table("products")

    op.drop_index(op.f("ix_locations_organization_id"), table_name="locations")
    op.drop_table("locations")

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("users"):
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        user_indexes = {index["name"] for index in inspector.get_indexes("users")}
        if bind.dialect.name != "sqlite":
            user_foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys("users")}
            if "fk_users_organization_id_organizations" in user_foreign_keys:
                op.drop_constraint("fk_users_organization_id_organizations", "users", type_="foreignkey")

            if op.f("ix_users_organization_id") in user_indexes:
                op.drop_index(op.f("ix_users_organization_id"), table_name="users")

            if "role" in user_columns:
                op.drop_column("users", "role")
            if "organization_id" in user_columns:
                op.drop_column("users", "organization_id")
        else:
            with op.batch_alter_table("users", recreate="always") as batch_op:
                if op.f("ix_users_organization_id") in user_indexes:
                    batch_op.drop_index(op.f("ix_users_organization_id"))
                if "role" in user_columns:
                    batch_op.drop_column("role")
                if "organization_id" in user_columns:
                    batch_op.drop_column("organization_id")

    op.drop_table("organizations")
