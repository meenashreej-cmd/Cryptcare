from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.local_llm import answer_patient_question
from app.core.rbac import CurrentUser, get_current_user
from app.db.session import get_db
from app.utils.network import get_client_ip
from app.services.auth_service import _check_action_rate_limit
import threading

# Limit max concurrent local LLM calls to 2 to prevent OOM/CPU starvation.
_ai_semaphore = threading.BoundedSemaphore(2)

router = APIRouter(prefix="/ai", tags=["ai"])

class ChatRequest(BaseModel):
    message: str = Field(..., max_length=2000)

class ChatResponse(BaseModel):
    reply: str

@router.post("/chat", response_model=ChatResponse)
def chat_with_ai(
    payload: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    if current_user.role != "PATIENT":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only patients can use the AI assistant")
    
    client_ip = get_client_ip(request)
    _check_action_rate_limit(db, current_user.id, "chat_with_ai", limit=5, window_seconds=60, is_ip=False)
    _check_action_rate_limit(db, client_ip, "chat_with_ai", limit=5, window_seconds=60, is_ip=True)
    
    if not _ai_semaphore.acquire(blocking=False):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, 
            "AI service is currently at capacity, please try again in a few moments."
        )
        
    try:
        reply = answer_patient_question(payload.message)
        if not reply:
            reply = "I'm currently unable to connect to the AI model. Please ensure the local AI service (Ollama) is running."
    finally:
        _ai_semaphore.release()
    
    return ChatResponse(reply=reply)
