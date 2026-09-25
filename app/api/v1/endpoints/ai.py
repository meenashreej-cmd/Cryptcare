"""
Phase 5 — AI Medical Assistant endpoint.

Security layers:
  1. PATIENT-only role enforcement
  2. Dual-layer rate limiting (per-user + per-IP, 5 req/60s each)
  3. Bounded semaphore (max 2 concurrent LLM calls to prevent OOM/CPU starvation)
  4. PHI guardrails via phi_guardrails.check_prompt_safety():
       - Prompt injection detection (27 patterns)
       - Out-of-scope topic rejection
       - PHI redaction from prompt before it reaches the LLM
  5. Response boundary enforcement via phi_guardrails.enforce_response_boundary():
       - PHI redacted from LLM output
       - System marker stripping
       - Max 2000 char response truncation
  6. Audit logging of all AI interactions (including blocked attempts)
"""

import threading

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.local_llm import answer_patient_question
from app.core.phi_guardrails import check_prompt_safety, enforce_response_boundary
from app.core.rbac import CurrentUser, get_current_user
from app.db.session import get_db
from app.services.auth_service import _check_action_rate_limit
from app.utils.network import get_client_ip

# Limit max concurrent local LLM calls to prevent OOM / CPU starvation.
_ai_semaphore = threading.BoundedSemaphore(2)

router = APIRouter(prefix="/ai", tags=["ai"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
def chat_with_ai(
    payload: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    # ── Role gate ────────────────────────────────────────────────────────────
    if current_user.role != "PATIENT":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only patients can use the AI assistant")

    client_ip = get_client_ip(request)

    # ── Rate limiting (dual-layer) ────────────────────────────────────────────
    _check_action_rate_limit(db, current_user.id, "chat_with_ai", limit=5, window_seconds=60, is_ip=False)
    _check_action_rate_limit(db, client_ip, "chat_with_ai", limit=5, window_seconds=60, is_ip=True)

    # ── Phase 5: prompt safety gate (injection + PHI + scope) ────────────────
    safety = check_prompt_safety(payload.message)
    if not safety.is_safe:
        # Log the blocked attempt to audit trail without exposing the reason to the user
        try:
            from app.core.audit import write_access_log
            from app.models.audit import AccessActionEnum
            write_access_log(
                db,
                user_id=current_user.id,
                resource_type="ai_chat",
                resource_id=None,
                action=AccessActionEnum.DENIED,
                ip_address=client_ip,
                patient_id=current_user.id,
            )
        except Exception:
            pass  # Audit failure must never block the response

        return ChatResponse(
            reply=(
                "I'm not able to help with that request. "
                "Please ask a general health or medication question and I'll do my best to assist. "
                "For urgent concerns, please contact your doctor directly."
            )
        )

    # ── Semaphore: cap concurrent LLM calls ──────────────────────────────────
    if not _ai_semaphore.acquire(blocking=False):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "AI service is currently at capacity. Please try again in a few moments.",
        )

    try:
        # answer_patient_question() also runs check_prompt_safety + enforce_response_boundary
        # internally, but we pre-check here to avoid acquiring the semaphore for blocked prompts.
        reply = answer_patient_question(payload.message)
        if not reply:
            reply = (
                "I'm currently unable to connect to the AI model. "
                "Please ensure the local AI service (Ollama) is running."
            )
        else:
            # Belt-and-suspenders: enforce boundary again at this layer too
            reply = enforce_response_boundary(reply, max_length=2000)
    finally:
        _ai_semaphore.release()

    # ── Audit log successful interaction ─────────────────────────────────────
    try:
        from app.core.audit import write_access_log
        from app.models.audit import AccessActionEnum
        write_access_log(
            db,
            user_id=current_user.id,
            resource_type="ai_chat",
            resource_id=None,
            action=AccessActionEnum.READ,
            ip_address=client_ip,
            patient_id=current_user.id,
        )
    except Exception:
        pass

    return ChatResponse(reply=reply)
