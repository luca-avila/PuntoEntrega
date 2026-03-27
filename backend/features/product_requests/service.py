import asyncio
import logging
import uuid
from decimal import Decimal
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.sql import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.db import async_session_maker
from features.auth.models import User
from features.organizations.models import MembershipRole, OrganizationMembership
from features.organizations.service import ensure_products_belong_to_organization
from features.product_requests.email import send_product_request_email
from features.product_requests.models import (
    ProductRequest,
    ProductRequestEmailStatus,
    ProductRequestItem,
)
from features.product_requests.schemas import ProductRequestListFilters

logger = logging.getLogger(__name__)

EMAIL_SEND_MAX_ATTEMPTS = 3
EMAIL_SEND_RETRY_DELAY_SECONDS = 2.0
EMAIL_LAST_ERROR_MAX_LENGTH = 2000


def _truncate_error_message(error_message: str) -> str:
    normalized = error_message.strip()
    if not normalized:
        return "Error desconocido al enviar email."
    if len(normalized) <= EMAIL_LAST_ERROR_MAX_LENGTH:
        return normalized
    return normalized[:EMAIL_LAST_ERROR_MAX_LENGTH]


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


async def _set_product_request_failed(
    session: AsyncSession,
    product_request: ProductRequest,
    *,
    attempts: int,
    error_message: str,
) -> None:
    product_request.email_status = ProductRequestEmailStatus.FAILED
    product_request.email_attempts = attempts
    product_request.email_last_error = _truncate_error_message(error_message)
    product_request.email_sent_at = None
    await session.commit()


async def _set_product_request_sent(
    session: AsyncSession,
    product_request: ProductRequest,
    *,
    attempts: int,
) -> None:
    product_request.email_status = ProductRequestEmailStatus.SENT
    product_request.email_attempts = attempts
    product_request.email_last_error = None
    product_request.email_sent_at = datetime.now(UTC)
    await session.commit()


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
        email_status=ProductRequestEmailStatus.PENDING,
        email_attempts=0,
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

    await session.commit()

    created_product_request = await _get_product_request_or_none(
        session=session,
        product_request_id=product_request.id,
    )
    if created_product_request is None:
        raise RuntimeError("No se pudo recuperar la solicitud de producto creada.")
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

    return product_requests


async def send_product_request_email_in_background(
    product_request_id: uuid.UUID,
) -> None:
    for attempt in range(1, EMAIL_SEND_MAX_ATTEMPTS + 1):
        async with async_session_maker() as session:
            product_request = await _get_product_request_or_none(session, product_request_id)
            if product_request is None:
                logger.warning(
                    "Product request not found during async email dispatch: request_id=%s",
                    product_request_id,
                )
                return

            if product_request.email_status in (
                ProductRequestEmailStatus.SENT,
                ProductRequestEmailStatus.FAILED,
            ):
                return

            if product_request.organization is None:
                await _set_product_request_failed(
                    session,
                    product_request,
                    attempts=attempt,
                    error_message="La organización de la solicitud no existe.",
                )
                return

            owner = await _get_owner_user_for_organization(
                session,
                product_request.organization_id,
            )
            if (
                owner is None
                or not owner.is_active
                or not owner.is_verified
                or not owner.email
                or not owner.email.strip()
            ):
                await _set_product_request_failed(
                    session,
                    product_request,
                    attempts=attempt,
                    error_message=_owner_not_sendable_reason(owner),
                )
                return

            requester_email = (
                product_request.requested_by_user.email
                if product_request.requested_by_user is not None
                else str(product_request.requested_by_user_id)
            )
            requested_for_location_name = (
                product_request.requested_for_location.name
                if product_request.requested_for_location is not None
                else "Sin ubicación asignada"
            )
            requested_for_location_address = (
                product_request.requested_for_location.address
                if product_request.requested_for_location is not None
                else "Sin dirección"
            )
            request_items = [
                (
                    item.product.name if item.product is not None else str(item.product_id),
                    _format_quantity_for_email(item.quantity),
                )
                for item in product_request.items
            ]
            if not request_items:
                request_items = [("Sin productos especificados", "-")]

            try:
                await send_product_request_email(
                    to_email=owner.email.strip(),
                    organization_name=product_request.organization.name,
                    requester_email=requester_email,
                    requested_for_location_name=requested_for_location_name,
                    requested_for_location_address=requested_for_location_address,
                    request_subject=product_request.subject,
                    request_message=product_request.message,
                    request_items=request_items,
                    requested_at=product_request.created_at,
                )
                await _set_product_request_sent(
                    session,
                    product_request,
                    attempts=attempt,
                )
                return
            except Exception as exc:
                await session.rollback()
                logger.exception(
                    "Product request email attempt failed: request_id=%s attempt=%s error=%s",
                    product_request_id,
                    attempt,
                    exc,
                )

                if attempt >= EMAIL_SEND_MAX_ATTEMPTS:
                    try:
                        latest_product_request = await _get_product_request_or_none(
                            session,
                            product_request_id,
                        )
                        if (
                            latest_product_request is not None
                            and latest_product_request.email_status
                            != ProductRequestEmailStatus.SENT
                        ):
                            await _set_product_request_failed(
                                session,
                                latest_product_request,
                                attempts=attempt,
                                error_message=str(exc),
                            )
                    except Exception as status_exc:
                        await session.rollback()
                        logger.exception(
                            "Failed to persist failed product request email status: request_id=%s error=%s",
                            product_request_id,
                            status_exc,
                        )
                    return

        await asyncio.sleep(EMAIL_SEND_RETRY_DELAY_SECONDS)
