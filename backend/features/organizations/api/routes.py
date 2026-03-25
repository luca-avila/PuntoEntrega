from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_async_session
from features.auth.models import User
from features.auth.service import current_active_user
from features.organizations.schemas import OrganizationCreate, OrganizationRead
from features.organizations.service import (
    create_organization_for_user,
    get_current_organization_for_user,
)

router = APIRouter()


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreate,
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await create_organization_for_user(
        session=session,
        user_id=current_user.id,
        organization_name=payload.name,
    )


@router.get("/current", response_model=OrganizationRead)
async def get_current_organization(
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await get_current_organization_for_user(
        session=session,
        user_id=current_user.id,
    )
