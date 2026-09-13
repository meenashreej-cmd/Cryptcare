from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.local_llm import answer_patient_question
from app.core.rbac import CurrentUser, get_current_user

router = APIRouter(prefix="/ai", tags=["ai"])

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

@router.post("/chat", response_model=ChatResponse)
def chat_with_ai(
    payload: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user)
):
    if current_user.role != "PATIENT":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only patients can use the AI assistant")
    
    reply = answer_patient_question(payload.message)
    if not reply:
        reply = "I'm currently unable to connect to the AI model. Please ensure the local AI service (Ollama) is running."
    
    return ChatResponse(reply=reply)
