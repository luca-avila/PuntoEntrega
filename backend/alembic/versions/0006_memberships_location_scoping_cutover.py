"""Cut over to organization memberships scoped by location.

Revision ID: 0006_memberships_location_scoping_cutover
Revises: 0005_create_product_requests
Create Date: 2026-03-26 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
import uuid

from alembic import op
from fastapi_users_db_sqlalchemy.generics import GUID
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0006_memberships_location_scoping_cutover"
down_revision: str | None = "0005_create_product_requests"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def _has_unique_constraint(
    inspector: sa.Inspector,
    table_name: str,
    constraint_name: str,
) -> bool:
    return any(
        unique_constraint.get("name") == constraint_name
        for unique_constraint in inspector.get_unique_constraints(table_name)
    )


def _has_unique_constraint_for_columns(
    inspector: sa.Inspector,
    table_name: str,
    expected_columns: tuple[str, ...],
) -> bool:
    expected = tuple(expected_columns)
    for unique_constraint in inspector.get_unique_constraints(table_name):
        constrained_columns = tuple(unique_constraint.get("column_names") or [])
        if constrained_columns == expected:
            return True
    return False


def _has_foreign_key(
    inspector: sa.Inspector,
    table_name: str,
    foreign_key_name: str,
) -> bool:
    return any(
        foreign_key.get("name") == foreign_key_name
        for foreign_key in inspector.get_foreign_keys(table_name)
    )


def _find_foreign_keys_for_column(
    inspector: sa.Inspector,
    table_name: str,
    column_name: str,
) -> list[str]:
    foreign_key_names: list[str] = []
    for foreign_key in inspector.get_foreign_keys(table_name):
        constraint_name = foreign_key.get("name")
        constrained_columns = foreign_key.get("constrained_columns") or []
        if constraint_name and column_name in constrained_columns:
            foreign_key_names.append(constraint_name)
    return foreign_key_names


def _pick_location_for_organization(
    *,
    organization_id: uuid.UUID,
    preferred_location_id: uuid.UUID | None,
    location_organization_by_id: dict[uuid.UUID, uuid.UUID],
    first_location_by_organization: dict[uuid.UUID, uuid.UUID],
) -> uuid.UUID | None:
    if preferred_location_id is not None:
        preferred_location_organization_id = location_organization_by_id.get(preferred_location_id)
        if preferred_location_organization_id == organization_id:
            return preferred_location_id
    return first_location_by_organization.get(organization_id)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_unique_constraint(inspector, "locations", "uq_locations_organization_id_id") and not _has_unique_constraint_for_columns(
        inspector,
        "locations",
        ("organization_id", "id"),
    ):
        with op.batch_alter_table("locations", schema=None) as batch_op:
            batch_op.create_unique_constraint(
                "uq_locations_organization_id_id",
                ["organization_id", "id"],
            )

    inspector = sa.inspect(bind)
    if not _has_column(inspector, "organization_invitations", "location_id"):
        with op.batch_alter_table("organization_invitations", schema=None) as batch_op:
            batch_op.add_column(sa.Column("location_id", sa.Uuid(), nullable=True))

    inspector = sa.inspect(bind)
    if not _has_column(inspector, "product_requests", "requested_for_location_id"):
        with op.batch_alter_table("product_requests", schema=None) as batch_op:
            batch_op.add_column(sa.Column("requested_for_location_id", sa.Uuid(), nullable=True))

    inspector = sa.inspect(bind)
    if not inspector.has_table("organization_memberships"):
        membership_role_enum = sa.Enum(
            "owner",
            "member",
            name="organization_membership_role_enum",
            native_enum=False,
            create_constraint=True,
        )

        op.create_table(
            "organization_memberships",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", GUID(), nullable=False),
            sa.Column("organization_id", sa.Uuid(), nullable=False),
            sa.Column("role", membership_role_enum, nullable=False),
            sa.Column("location_id", sa.Uuid(), nullable=True),
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
            sa.CheckConstraint(
                "((role = 'owner' AND location_id IS NULL) OR (role = 'member' AND location_id IS NOT NULL))",
                name="ck_organization_memberships_role_location",
            ),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["organization_id", "location_id"],
                ["locations.organization_id", "locations.id"],
                name="fk_organization_memberships_organization_location",
                ondelete="RESTRICT",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "user_id",
                "organization_id",
                name="uq_organization_memberships_user_id_organization_id",
            ),
        )
        op.create_index(
            op.f("ix_organization_memberships_user_id"),
            "organization_memberships",
            ["user_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_organization_memberships_organization_id"),
            "organization_memberships",
            ["organization_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_organization_memberships_role"),
            "organization_memberships",
            ["role"],
            unique=False,
        )
        op.create_index(
            op.f("ix_organization_memberships_location_id"),
            "organization_memberships",
            ["location_id"],
            unique=False,
        )
        op.create_index(
            "uq_organization_memberships_owner_per_organization",
            "organization_memberships",
            ["organization_id"],
            unique=True,
            postgresql_where=sa.text("role = 'owner'"),
            sqlite_where=sa.text("role = 'owner'"),
        )

    organization_table = sa.table(
        "organizations",
        sa.column("id", sa.Uuid()),
        sa.column("owner_user_id", sa.Uuid()),
    )
    user_table = sa.table(
        "user",
        sa.column("id", GUID()),
        sa.column("organization_id", sa.Uuid()),
        sa.column("location_id", sa.Uuid()),
    )
    location_table = sa.table(
        "locations",
        sa.column("id", sa.Uuid()),
        sa.column("organization_id", sa.Uuid()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    membership_table = sa.table(
        "organization_memberships",
        sa.column("id", sa.Uuid()),
        sa.column("user_id", GUID()),
        sa.column("organization_id", sa.Uuid()),
        sa.column("role", sa.String(length=20)),
        sa.column("location_id", sa.Uuid()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    invitation_table = sa.table(
        "organization_invitations",
        sa.column("id", sa.Uuid()),
        sa.column("organization_id", sa.Uuid()),
        sa.column("invited_by_user_id", GUID()),
        sa.column("location_id", sa.Uuid()),
    )
    product_request_table = sa.table(
        "product_requests",
        sa.column("id", sa.Uuid()),
        sa.column("organization_id", sa.Uuid()),
        sa.column("requested_by_user_id", GUID()),
        sa.column("requested_for_location_id", sa.Uuid()),
    )

    inspector = sa.inspect(bind)
    has_user_location_column = _has_column(inspector, "user", "location_id")

    location_rows = bind.execute(
        sa.select(
            location_table.c.id,
            location_table.c.organization_id,
            location_table.c.created_at,
        ).order_by(
            location_table.c.organization_id,
            location_table.c.created_at,
            location_table.c.id,
        )
    ).mappings().all()
    first_location_by_organization: dict[uuid.UUID, uuid.UUID] = {}
    location_organization_by_id: dict[uuid.UUID, uuid.UUID] = {}
    for row in location_rows:
        location_id = row["id"]
        organization_id = row["organization_id"]
        if location_id is None or organization_id is None:
            continue
        location_organization_by_id[location_id] = organization_id
        first_location_by_organization.setdefault(organization_id, location_id)

    now = datetime.now(UTC)
    existing_membership_rows = bind.execute(
        sa.select(
            membership_table.c.user_id,
            membership_table.c.organization_id,
            membership_table.c.role,
        )
    ).mappings().all()
    existing_membership_pairs = {
        (row["user_id"], row["organization_id"])
        for row in existing_membership_rows
        if row["user_id"] is not None and row["organization_id"] is not None
    }
    owner_organization_ids = {
        row["organization_id"]
        for row in existing_membership_rows
        if row["organization_id"] is not None and row["role"] == "owner"
    }

    owner_rows = bind.execute(
        sa.select(
            organization_table.c.id,
            organization_table.c.owner_user_id,
        ).where(organization_table.c.owner_user_id.is_not(None))
    ).mappings().all()
    for row in owner_rows:
        organization_id = row["id"]
        owner_user_id = row["owner_user_id"]
        if organization_id is None or owner_user_id is None:
            continue
        if organization_id in owner_organization_ids:
            continue
        membership_pair = (owner_user_id, organization_id)
        if membership_pair in existing_membership_pairs:
            continue

        bind.execute(
            membership_table.insert().values(
                id=uuid.uuid4(),
                user_id=owner_user_id,
                organization_id=organization_id,
                role="owner",
                location_id=None,
                created_at=now,
                updated_at=now,
            )
        )
        existing_membership_pairs.add(membership_pair)
        owner_organization_ids.add(organization_id)

    if has_user_location_column:
        user_rows = bind.execute(
            sa.select(
                user_table.c.id,
                user_table.c.organization_id,
                user_table.c.location_id,
            )
        ).mappings().all()
    else:
        user_rows = bind.execute(
            sa.select(
                user_table.c.id,
                user_table.c.organization_id,
            )
        ).mappings().all()

    user_location_by_user_id: dict[uuid.UUID, uuid.UUID | None] = {}
    for row in user_rows:
        user_id = row["id"]
        if user_id is None:
            continue
        user_location_by_user_id[user_id] = row.get("location_id") if has_user_location_column else None

    for row in user_rows:
        user_id = row["id"]
        organization_id = row["organization_id"]
        if user_id is None or organization_id is None:
            continue

        membership_pair = (user_id, organization_id)
        if membership_pair in existing_membership_pairs:
            continue

        preferred_location_id = row.get("location_id") if has_user_location_column else None
        location_id = _pick_location_for_organization(
            organization_id=organization_id,
            preferred_location_id=preferred_location_id,
            location_organization_by_id=location_organization_by_id,
            first_location_by_organization=first_location_by_organization,
        )
        if location_id is None:
            continue

        bind.execute(
            membership_table.insert().values(
                id=uuid.uuid4(),
                user_id=user_id,
                organization_id=organization_id,
                role="member",
                location_id=location_id,
                created_at=now,
                updated_at=now,
            )
        )
        existing_membership_pairs.add(membership_pair)

    invitation_rows = bind.execute(
        sa.select(
            invitation_table.c.id,
            invitation_table.c.organization_id,
            invitation_table.c.invited_by_user_id,
            invitation_table.c.location_id,
        ).where(invitation_table.c.location_id.is_(None))
    ).mappings().all()
    for row in invitation_rows:
        invitation_id = row["id"]
        organization_id = row["organization_id"]
        invited_by_user_id = row["invited_by_user_id"]
        if invitation_id is None or organization_id is None:
            continue

        preferred_location_id = user_location_by_user_id.get(invited_by_user_id)
        location_id = _pick_location_for_organization(
            organization_id=organization_id,
            preferred_location_id=preferred_location_id,
            location_organization_by_id=location_organization_by_id,
            first_location_by_organization=first_location_by_organization,
        )
        if location_id is None:
            continue

        bind.execute(
            invitation_table.update()
            .where(invitation_table.c.id == invitation_id)
            .values(location_id=location_id)
        )

    product_request_rows = bind.execute(
        sa.select(
            product_request_table.c.id,
            product_request_table.c.organization_id,
            product_request_table.c.requested_by_user_id,
            product_request_table.c.requested_for_location_id,
        ).where(product_request_table.c.requested_for_location_id.is_(None))
    ).mappings().all()
    for row in product_request_rows:
        product_request_id = row["id"]
        organization_id = row["organization_id"]
        requested_by_user_id = row["requested_by_user_id"]
        if product_request_id is None or organization_id is None:
            continue

        preferred_location_id = user_location_by_user_id.get(requested_by_user_id)
        location_id = _pick_location_for_organization(
            organization_id=organization_id,
            preferred_location_id=preferred_location_id,
            location_organization_by_id=location_organization_by_id,
            first_location_by_organization=first_location_by_organization,
        )
        if location_id is None:
            continue

        bind.execute(
            product_request_table.update()
            .where(product_request_table.c.id == product_request_id)
            .values(requested_for_location_id=location_id)
        )

    inspector = sa.inspect(bind)
    if not _has_index(inspector, "organization_invitations", op.f("ix_organization_invitations_location_id")):
        op.create_index(
            op.f("ix_organization_invitations_location_id"),
            "organization_invitations",
            ["location_id"],
            unique=False,
        )

    inspector = sa.inspect(bind)
    if not _has_foreign_key(
        inspector,
        "organization_invitations",
        "fk_organization_invitations_organization_location",
    ):
        with op.batch_alter_table("organization_invitations", schema=None) as batch_op:
            batch_op.create_foreign_key(
                "fk_organization_invitations_organization_location",
                "locations",
                ["organization_id", "location_id"],
                ["organization_id", "id"],
                ondelete="RESTRICT",
            )

    inspector = sa.inspect(bind)
    if not _has_index(inspector, "product_requests", op.f("ix_product_requests_requested_for_location_id")):
        op.create_index(
            op.f("ix_product_requests_requested_for_location_id"),
            "product_requests",
            ["requested_for_location_id"],
            unique=False,
        )

    inspector = sa.inspect(bind)
    if not _has_foreign_key(
        inspector,
        "product_requests",
        "fk_product_requests_organization_requested_for_location",
    ):
        with op.batch_alter_table("product_requests", schema=None) as batch_op:
            batch_op.create_foreign_key(
                "fk_product_requests_organization_requested_for_location",
                "locations",
                ["organization_id", "requested_for_location_id"],
                ["organization_id", "id"],
                ondelete="RESTRICT",
            )

    inspector = sa.inspect(bind)
    organization_indexes = {index.get("name") for index in inspector.get_indexes("organizations")}
    organization_foreign_keys = _find_foreign_keys_for_column(
        inspector,
        "organizations",
        "owner_user_id",
    )
    if _has_column(inspector, "organizations", "owner_user_id"):
        with op.batch_alter_table("organizations", schema=None) as batch_op:
            for foreign_key_name in organization_foreign_keys:
                batch_op.drop_constraint(foreign_key_name, type_="foreignkey")
            if op.f("ix_organizations_owner_user_id") in organization_indexes:
                batch_op.drop_index(op.f("ix_organizations_owner_user_id"))
            batch_op.drop_column("owner_user_id")

    inspector = sa.inspect(bind)
    user_indexes = {index.get("name") for index in inspector.get_indexes("user")}
    user_foreign_keys_for_organization = _find_foreign_keys_for_column(
        inspector,
        "user",
        "organization_id",
    )
    user_foreign_keys_for_location = _find_foreign_keys_for_column(
        inspector,
        "user",
        "location_id",
    )
    has_user_organization_column = _has_column(inspector, "user", "organization_id")
    has_user_location_column = _has_column(inspector, "user", "location_id")
    if has_user_organization_column or has_user_location_column:
        with op.batch_alter_table("user", schema=None) as batch_op:
            for foreign_key_name in user_foreign_keys_for_organization:
                batch_op.drop_constraint(foreign_key_name, type_="foreignkey")
            for foreign_key_name in user_foreign_keys_for_location:
                batch_op.drop_constraint(foreign_key_name, type_="foreignkey")
            if op.f("ix_users_organization_id") in user_indexes:
                batch_op.drop_index(op.f("ix_users_organization_id"))
            if op.f("ix_user_organization_id") in user_indexes:
                batch_op.drop_index(op.f("ix_user_organization_id"))
            if op.f("ix_users_location_id") in user_indexes:
                batch_op.drop_index(op.f("ix_users_location_id"))
            if op.f("ix_user_location_id") in user_indexes:
                batch_op.drop_index(op.f("ix_user_location_id"))
            if has_user_organization_column:
                batch_op.drop_column("organization_id")
            if has_user_location_column:
                batch_op.drop_column("location_id")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_column(inspector, "user", "organization_id"):
        with op.batch_alter_table("user", schema=None) as batch_op:
            batch_op.add_column(sa.Column("organization_id", sa.Uuid(), nullable=True))

    inspector = sa.inspect(bind)
    if not _has_index(inspector, "user", op.f("ix_users_organization_id")):
        op.create_index(op.f("ix_users_organization_id"), "user", ["organization_id"], unique=False)

    inspector = sa.inspect(bind)
    if not _has_foreign_key(inspector, "user", "fk_users_organization_id_organizations"):
        with op.batch_alter_table("user", schema=None) as batch_op:
            batch_op.create_foreign_key(
                "fk_users_organization_id_organizations",
                "organizations",
                ["organization_id"],
                ["id"],
                ondelete="SET NULL",
            )

    inspector = sa.inspect(bind)
    if not _has_column(inspector, "organizations", "owner_user_id"):
        with op.batch_alter_table("organizations", schema=None) as batch_op:
            batch_op.add_column(sa.Column("owner_user_id", sa.Uuid(), nullable=True))
            batch_op.create_foreign_key(
                "fk_organizations_owner_user_id_user",
                "user",
                ["owner_user_id"],
                ["id"],
                ondelete="RESTRICT",
            )

    inspector = sa.inspect(bind)
    if not _has_index(inspector, "organizations", op.f("ix_organizations_owner_user_id")):
        op.create_index(
            op.f("ix_organizations_owner_user_id"),
            "organizations",
            ["owner_user_id"],
            unique=False,
        )

    inspector = sa.inspect(bind)
    if _has_foreign_key(
        inspector,
        "product_requests",
        "fk_product_requests_organization_requested_for_location",
    ):
        with op.batch_alter_table("product_requests", schema=None) as batch_op:
            batch_op.drop_constraint(
                "fk_product_requests_organization_requested_for_location",
                type_="foreignkey",
            )

    inspector = sa.inspect(bind)
    if _has_index(inspector, "product_requests", op.f("ix_product_requests_requested_for_location_id")):
        op.drop_index(op.f("ix_product_requests_requested_for_location_id"), table_name="product_requests")

    inspector = sa.inspect(bind)
    if _has_column(inspector, "product_requests", "requested_for_location_id"):
        with op.batch_alter_table("product_requests", schema=None) as batch_op:
            batch_op.drop_column("requested_for_location_id")

    inspector = sa.inspect(bind)
    if _has_foreign_key(
        inspector,
        "organization_invitations",
        "fk_organization_invitations_organization_location",
    ):
        with op.batch_alter_table("organization_invitations", schema=None) as batch_op:
            batch_op.drop_constraint(
                "fk_organization_invitations_organization_location",
                type_="foreignkey",
            )

    inspector = sa.inspect(bind)
    if _has_index(inspector, "organization_invitations", op.f("ix_organization_invitations_location_id")):
        op.drop_index(op.f("ix_organization_invitations_location_id"), table_name="organization_invitations")

    inspector = sa.inspect(bind)
    if _has_column(inspector, "organization_invitations", "location_id"):
        with op.batch_alter_table("organization_invitations", schema=None) as batch_op:
            batch_op.drop_column("location_id")

    inspector = sa.inspect(bind)
    if inspector.has_table("organization_memberships"):
        op.drop_index("uq_organization_memberships_owner_per_organization", table_name="organization_memberships")
        op.drop_index(op.f("ix_organization_memberships_location_id"), table_name="organization_memberships")
        op.drop_index(op.f("ix_organization_memberships_role"), table_name="organization_memberships")
        op.drop_index(op.f("ix_organization_memberships_organization_id"), table_name="organization_memberships")
        op.drop_index(op.f("ix_organization_memberships_user_id"), table_name="organization_memberships")
        op.drop_table("organization_memberships")

    inspector = sa.inspect(bind)
    if _has_unique_constraint(inspector, "locations", "uq_locations_organization_id_id"):
        with op.batch_alter_table("locations", schema=None) as batch_op:
            batch_op.drop_constraint("uq_locations_organization_id_id", type_="unique")
