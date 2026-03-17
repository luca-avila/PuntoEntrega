import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_async_session
from features.organizations.service import get_current_organization_id
from features.products.schemas import ProductCreate, ProductRead, ProductUpdate
from features.products.service import (
    create_product_for_organization,
    get_product_for_organization,
    list_products_for_organization,
    update_product_for_organization,
)

router = APIRouter()


@router.get("", response_model=list[ProductRead])
async def list_products(
    active_only: bool = Query(default=False),
    organization_id: uuid.UUID = Depends(get_current_organization_id),
    session: AsyncSession = Depends(get_async_session),
):
    return await list_products_for_organization(
        session=session,
        organization_id=organization_id,
        active_only=active_only,
    )


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    organization_id: uuid.UUID = Depends(get_current_organization_id),
    session: AsyncSession = Depends(get_async_session),
):
    return await create_product_for_organization(
        session=session,
        organization_id=organization_id,
        payload=payload,
    )


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: uuid.UUID,
    organization_id: uuid.UUID = Depends(get_current_organization_id),
    session: AsyncSession = Depends(get_async_session),
):
    return await get_product_for_organization(
        session=session,
        organization_id=organization_id,
        product_id=product_id,
    )


@router.patch("/{product_id}", response_model=ProductRead)
async def patch_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    organization_id: uuid.UUID = Depends(get_current_organization_id),
    session: AsyncSession = Depends(get_async_session),
):
    return await update_product_for_organization(
        session=session,
        organization_id=organization_id,
        product_id=product_id,
        payload=payload,
    )
