import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from features.auth.models import User
from features.notifications.models import (
    NotificationOutboxEvent,
    NotificationOutboxStatus,
)
from features.notifications.outbox import (
    EVENT_PRODUCT_REQUEST_OWNER_NOTIFICATION_REQUESTED,
    enqueue_notification_event,
)
from features.organizations.models import MembershipRole, OrganizationMembership
from features.organizations.service import ensure_products_belong_to_organization
from features.product_requests.models import (
    ProductRequest,
    ProductRequestEmailStatus,
    ProductRequestItem,
)
from features.product_requests.schemas import ProductRequestListFilters

EMAIL_SEND_MAX_ATTEMPTS = 3


def _owner_not_sendable_reason(owner: User | None) -> str:
    if owner is None:
        return "No se pudo resolver el owner de la organización."
    if not owner.is_active:
        return "El owner de la organización está inactivo."
    if not owner.is_verified:
        return "El owner de la organización no tiene email verificado."
    if not owner.email or not owner.email.strip():
        return "El owner de la organización no tiene un email válido."
    return "El owner de la organización no es enviable."


def _format_quantity_for_email(quantity: Decimal) -> str:
    if quantity == quantity.to_integral_value():
        return str(int(quantity))
    return format(quantity.normalize(), "f")


async def _get_product_request_or_none(
    session: AsyncSession,
    product_request_id: uuid.UUID,
) -> ProductRequest | None:
    result = await session.execute(
        select(ProductRequest)
        .where(ProductRequest.id == product_request_id)
        .options(
            selectinload(ProductRequest.organization),
            selectinload(ProductRequest.requested_by_user),
            selectinload(ProductRequest.requested_for_location),
            selectinload(ProductRequest.items).selectinload(ProductRequestItem.product),
        )
    )
    return result.scalar_one_or_none()


def _set_product_request_email_snapshot(
    product_request: ProductRequest,
    event: NotificationOutboxEvent | None,
) -> None:
    email_status = ProductRequestEmailStatus.PENDING
    email_attempts = 0
    email_last_error: str | None = None
    email_sent_at = None

    if event is not None and event.status == NotificationOutboxStatus.PROCESSED:
        email_status = ProductRequestEmailStatus.SENT
        email_attempts = event.attempts
        email_sent_at = event.processed_at
    elif event is not None and event.status == NotificationOutboxStatus.FAILED:
        email_status = ProductRequestEmailStatus.FAILED
        email_attempts = event.attempts
        email_last_error = event.last_error

    setattr(product_request, "email_status", email_status)
    setattr(product_request, "email_attempts", email_attempts)
    setattr(product_request, "email_last_error", email_last_error)
    setattr(product_request, "email_sent_at", email_sent_at)


async def _list_product_request_notification_events(
    session: AsyncSession,
    product_request_ids: list[uuid.UUID],
) -> dict[uuid.UUID, NotificationOutboxEvent]:
    if not product_request_ids:
        return {}

    result = await session.execute(
        select(NotificationOutboxEvent).where(
            NotificationOutboxEvent.event_type
            == EVENT_PRODUCT_REQUEST_OWNER_NOTIFICATION_REQUESTED,
            NotificationOutboxEvent.aggregate_id.in_(product_request_ids),
        )
    )
    events = list(result.scalars().all())
    return {event.aggregate_id: event for event in events}


async def _hydrate_product_request_email_snapshots(
    session: AsyncSession,
    product_requests: list[ProductRequest],
) -> None:
    events_by_request_id = await _list_product_request_notification_events(
        session,
        [product_request.id for product_request in product_requests],
    )
    for product_request in product_requests:
        _set_product_request_email_snapshot(
            product_request,
            events_by_request_id.get(product_request.id),
        )


async def _get_owner_user_for_organization(
    session: AsyncSession,
    organization_id: uuid.UUID,
) -> User | None:
    result = await session.execute(
        select(User)
        .join(OrganizationMembership, OrganizationMembership.user_id == User.id)
        .where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.role == MembershipRole.OWNER.value,
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_product_request(
    session: AsyncSession,
    organization_id: uuid.UUID,
    requested_by_user_id: uuid.UUID,
    requested_for_location_id: uuid.UUID,
    subject: str,
    message: str | None,
    items: list[tuple[uuid.UUID, Decimal]],
) -> ProductRequest:
    await ensure_products_belong_to_organization(
        session=session,
        organization_id=organization_id,
        product_ids=(product_id for product_id, _quantity in items),
    )

    product_request = ProductRequest(
        organization_id=organization_id,
        requested_by_user_id=requested_by_user_id,
        requested_for_location_id=requested_for_location_id,
        subject=subject,
        message=message,
    )
    session.add(product_request)

    await session.flush()

    for product_id, quantity in items:
        session.add(
            ProductRequestItem(
                product_request_id=product_request.id,
                product_id=product_id,
                quantity=quantity,
            )
        )

    await enqueue_notification_event(
        session,
        event_type=EVENT_PRODUCT_REQUEST_OWNER_NOTIFICATION_REQUESTED,
        aggregate_type="product_request",
        aggregate_id=product_request.id,
        organization_id=organization_id,
        payload={"product_request_id": str(product_request.id)},
        deduplication_key=f"product_request:{product_request.id}:owner_notification",
        max_attempts=EMAIL_SEND_MAX_ATTEMPTS,
    )

    await session.commit()

    created_product_request = await _get_product_request_or_none(
        session=session,
        product_request_id=product_request.id,
    )
    if created_product_request is None:
        raise RuntimeError("No se pudo recuperar la solicitud de producto creada.")
    await _hydrate_product_request_email_snapshots(
        session,
        [created_product_request],
    )
    return created_product_request


async def list_product_requests_for_organization(
    session: AsyncSession,
    organization_id: uuid.UUID,
    filters: ProductRequestListFilters,
    scoped_location_id: uuid.UUID | None = None,
) -> list[ProductRequest]:
    query: Select[tuple[ProductRequest]] = (
        select(ProductRequest)
        .where(ProductRequest.organization_id == organization_id)
        .options(
            selectinload(ProductRequest.requested_for_location),
            selectinload(ProductRequest.items),
        )
        .order_by(ProductRequest.created_at.desc())
    )

    if scoped_location_id is not None:
        if (
            filters.requested_for_location_id is not None
            and filters.requested_for_location_id != scoped_location_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El miembro no puede consultar pedidos de otra ubicación.",
            )
        query = query.where(ProductRequest.requested_for_location_id == scoped_location_id)
    elif filters.requested_for_location_id is not None:
        query = query.where(
            ProductRequest.requested_for_location_id == filters.requested_for_location_id
        )

    if filters.created_from is not None:
        query = query.where(ProductRequest.created_at >= filters.created_from)
    if filters.created_to is not None:
        query = query.where(ProductRequest.created_at <= filters.created_to)

    result = await session.execute(query)
    product_requests = list(result.scalars().all())
    for product_request in product_requests:
        setattr(
            product_request,
            "requested_for_location_name",
            (
                product_request.requested_for_location.name
                if product_request.requested_for_location is not None
                else None
            ),
        )
        setattr(
            product_request,
            "requested_for_location_address",
            (
                product_request.requested_for_location.address
                if product_request.requested_for_location is not None
                else None
            ),
        )

    await _hydrate_product_request_email_snapshots(session, product_requests)
    return product_requests
