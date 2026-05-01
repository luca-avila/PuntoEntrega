import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from features.auth.models import Base

if TYPE_CHECKING:
    from features.auth.models import User
    from features.locations.models import Location
    from features.organizations.models import Organization
    from features.products.models import Product


class ProductRequestEmailStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class ProductRequest(Base):
    __tablename__ = "product_requests"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "requested_for_location_id"],
            ["locations.organization_id", "locations.id"],
            name="fk_product_requests_organization_requested_for_location",
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    requested_for_location_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    organization: Mapped["Organization"] = relationship(overlaps="requested_for_location")
    requested_by_user: Mapped["User"] = relationship()
    requested_for_location: Mapped["Location | None"] = relationship(overlaps="organization")
    items: Mapped[list["ProductRequestItem"]] = relationship(
        back_populates="product_request",
        cascade="all, delete-orphan",
    )


class ProductRequestItem(Base):
    __tablename__ = "product_request_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_product_request_items_quantity_gt_zero"),
        UniqueConstraint(
            "product_request_id",
            "product_id",
            name="uq_product_request_items_request_product",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    product_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("product_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    product_request: Mapped["ProductRequest"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(back_populates="product_request_items")
