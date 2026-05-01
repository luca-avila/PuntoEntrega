from sqlalchemy.ext.asyncio import AsyncSession

from features.notifications.errors import NonRetryableNotificationError
from features.notifications.models import NotificationOutboxEvent
from features.notifications.payloads import require_payload_uuid
from features.product_requests import emails as product_request_emails
from features.product_requests import service as product_request_service


async def handle_owner_notification_requested(
    session: AsyncSession,
    event: NotificationOutboxEvent,
) -> None:
    product_request_id = require_payload_uuid(event.payload, "product_request_id")
    product_request = await product_request_service._get_product_request_or_none(
        session,
        product_request_id,
    )
    if product_request is None:
        raise NonRetryableNotificationError(
            f"Product request not found: {product_request_id}"
        )
    if product_request.organization is None:
        raise NonRetryableNotificationError("Product request organization is missing.")

    owner = await product_request_service._get_owner_user_for_organization(
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
        reason = product_request_service._owner_not_sendable_reason(owner)
        raise NonRetryableNotificationError(reason)

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
            product_request_service._format_quantity_for_email(item.quantity),
        )
        for item in product_request.items
    ]
    if not request_items:
        request_items = [("Sin productos especificados", "-")]

    await product_request_emails.send_product_request_email(
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
