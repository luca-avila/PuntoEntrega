import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from features.products.models import Product
from features.products.schemas import ProductCreate, ProductUpdate


async def list_products_for_organization(
    session: AsyncSession,
    organization_id: uuid.UUID,
    *,
    active_only: bool = False,
) -> list[Product]:
    query = (
        select(Product)
        .where(Product.organization_id == organization_id)
        .order_by(Product.created_at.desc())
    )
    if active_only:
        query = query.where(Product.is_active.is_(True))

    result = await session.execute(query)
    return list(result.scalars().all())


async def create_product_for_organization(
    session: AsyncSession,
    organization_id: uuid.UUID,
    payload: ProductCreate,
) -> Product:
    product = Product(
        organization_id=organization_id,
        name=payload.name,
        description=payload.description,
        is_active=payload.is_active,
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return product


async def get_product_for_organization(
    session: AsyncSession,
    organization_id: uuid.UUID,
    product_id: uuid.UUID,
) -> Product:
    result = await session.execute(
        select(Product).where(
            Product.id == product_id,
            Product.organization_id == organization_id,
        )
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado.",
        )
    return product


async def update_product_for_organization(
    session: AsyncSession,
    organization_id: uuid.UUID,
    product_id: uuid.UUID,
    payload: ProductUpdate,
) -> Product:
    product = await get_product_for_organization(
        session=session,
        organization_id=organization_id,
        product_id=product_id,
    )

    for field_name, field_value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field_name, field_value)

    await session.commit()
    await session.refresh(product)
    return product
