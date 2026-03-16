from fastapi import APIRouter, Depends

from features.auth.models import User
from features.auth.service import current_active_user
from features.protected.service import build_protected_message

router = APIRouter()


@router.get("/protected-route")
async def protected_route(user: User = Depends(current_active_user)):
    """Example protected route - requires authentication."""
    return build_protected_message(user.email)
