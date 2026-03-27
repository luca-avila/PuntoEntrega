import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_async_session
from features.organizations.service import (
    OrganizationUserContext,
    get_member_assigned_location_id,
    require_organization_member,
    require_organization_user,
)
from features.product_requests.schemas import (
    ProductRequestCreate,
    ProductRequestListFilters,
    ProductRequestRead,
)
from features.product_requests.service import (
    create_product_request,
    list_product_requests_for_organization,
    send_product_request_email_in_background,
)

router = APIRouter()


@router.post(
    "/product-requests",
    response_model=ProductRequestRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_product_request_endpoint(
    payload: ProductRequestCreate,
    background_tasks: BackgroundTasks,
    context: OrganizationUserContext = Depends(require_organization_member),
    session: AsyncSession = Depends(get_async_session),
):
    member_location_id = await get_member_assigned_location_id(
        session=session,
        context=context,
    )
    if member_location_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El miembro no tiene una ubicación asignada.",
        )

    product_request = await create_product_request(
        session=session,
        organization_id=context.organization.id,
        requested_by_user_id=context.user.id,
        requested_for_location_id=member_location_id,
        subject=payload.subject,
        message=payload.message,
        items=[(item.product_id, item.quantity) for item in payload.items],
    )
    background_tasks.add_task(
        send_product_request_email_in_background,
        product_request.id,
    )
    return product_request


@router.get(
    "/product-requests",
    response_model=list[ProductRequestRead],
)
async def list_product_requests_endpoint(
    requested_for_location_id: uuid.UUID | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    context: OrganizationUserContext = Depends(require_organization_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        filters = ProductRequestListFilters(
            requested_for_location_id=requested_for_location_id,
            created_from=created_from,
            created_to=created_to,
        )
    except ValidationError as exc:
        errors = exc.errors(include_input=False, include_url=False)
        message = errors[0]["msg"] if errors else "Parámetros de búsqueda inválidos."
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=message,
        ) from exc

    scoped_location_id = await get_member_assigned_location_id(
        session=session,
        context=context,
    )

    return await list_product_requests_for_organization(
        session=session,
        organization_id=context.organization.id,
        filters=filters,
        scoped_location_id=scoped_location_id,
    )
