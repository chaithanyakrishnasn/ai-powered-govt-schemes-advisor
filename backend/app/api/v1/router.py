from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.v1 import match, profiles, schemes, chat
from app.core.config import settings
from app.db.models import Scheme

router = APIRouter()


@router.get("/health", tags=["monitoring"])
async def health(session: AsyncSession = Depends(get_db)) -> dict:
    try:
        scheme_count = await session.scalar(select(func.count()).select_from(Scheme))
        db_status = "connected"
    except Exception:
        scheme_count = -1
        db_status = "error"

    return {
        "status": "ok",
        "db": db_status,
        "schemes_count": scheme_count,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }

router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
router.include_router(schemes.router, prefix="/schemes", tags=["schemes"])
router.include_router(match.router, prefix="/match", tags=["match"])
router.include_router(chat.router, prefix="/chat", tags=["chat"])
