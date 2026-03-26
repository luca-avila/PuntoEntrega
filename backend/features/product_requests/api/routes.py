from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_async_session
from features.organizations.service import (
    OrganizationUserContext,
    get_member_assigned_location_id,
    require_organization_member,
    require_organization_owner,
)
from features.product_requests.schemas import ProductRequestCreate, ProductRequestRead
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
    context: OrganizationUserContext = Depends(require_organization_owner),
    session: AsyncSession = Depends(get_async_session),
):
    return await list_product_requests_for_organization(
        session=session,
        organization_id=context.organization.id,
    )
