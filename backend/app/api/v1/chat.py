from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.api.deps import get_db, get_matching_service, get_gemini_client
from app.services.chat.chat_service import ChatService
from app.schemas.user_profile import UserProfile
from app.db.models import UserProfile as UserProfileModel
from app.schemas.match import SchemeResultItem
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

class ChatHistoryItem(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatHistoryItem] = []
    profile: Optional[UserProfile] = None
    profile_id: Optional[str] = None
    language: str = "en"

class ChatResponse(BaseModel):
    response: str
    schemes: Optional[List[SchemeResultItem]] = None
    should_show_schemes: bool = False

@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    session: AsyncSession = Depends(get_db),
    gemini_client = Depends(get_gemini_client),
    matching_service = Depends(get_matching_service),
):
    profile = request.profile
    if request.profile_id and not profile:
        db_profile = await session.get(UserProfileModel, request.profile_id)
        if db_profile:
            profile = UserProfile.model_validate(db_profile)
    
    chat_service = ChatService(gemini_client, matching_service)
    result = await chat_service.chat(
        message=request.message,
        history=[h.dict() for h in request.history],
        profile=profile,
        language=request.language,
    )
    return ChatResponse(**result)
