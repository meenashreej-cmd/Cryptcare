"""
Phase 7 — local LLM explanation generation via Ollama.

Architectural boundary this module exists to enforce: the LLM only ever
*explains* findings that clinical_safety_service already computed
deterministically (interaction pairs, allergy conflicts, duplicates) — it
never decides what counts as a conflict and it never sees a patient's full
record, only the small structured findings dict. It also never leaves the
local machine: this calls localhost Ollama, never a third-party API, so no
PHI-adjacent text crosses the trust boundary. If Ollama isn't running (very
likely true in CI/tests, and possibly in a developer's environment too),
every function here fails closed to a deterministic templated string —
explanation quality degrades, but a safety check can never silently pass
(or silently hang) just because the local model is unavailable.
"""

import json
import urllib.error
import urllib.request

from app.core.config import settings


def _call_ollama(prompt: str) -> str | None:
    if not settings.LOCAL_LLM_ENABLED:
        return None

    body = json.dumps({
        "model": settings.LOCAL_LLM_MODEL,
        "prompt": prompt,
        "stream": False,
    }).encode("utf-8")

    request = urllib.request.Request(
        f"{settings.LOCAL_LLM_BASE_URL}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.LOCAL_LLM_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
            text = payload.get("response", "").strip()
            return text or None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        # Connection refused (Ollama not running), DNS failure, timeout,
        # malformed response — all treated the same: no explanation
        # available right now, caller falls back to a template.
        return None


def explain_safety_findings(findings: dict) -> str | None:
    """
    Best-effort plain-language summary of a full_safety_check() result.
    Returns None on any failure — callers must have a non-LLM fallback ready
    (see clinical_safety_service._template_explanation) and must never block
    on or fail because this returned None.
    """
    prompt = (
        "You are summarizing a clinical safety check for a doctor reviewing "
        "a new prescription. Given the structured findings below (already "
        "computed by rule-based logic — do not add or remove findings, only "
        "explain them in plain language), write a concise 2-3 sentence "
        "summary a busy clinician can read in a few seconds. Do not give "
        "dosing advice or suggest alternative medications.\n\n"
        f"Findings (JSON): {json.dumps(findings)}"
    )
    return _call_ollama(prompt)


def answer_patient_question(question: str) -> str | None:
    """
    Patient-facing medical assistant. Strongly sandboxed.
    """
    # Assert that no full record/context object is being passed yet.
    # The prompt is strictly constructed from the static string and the user's typed question.
    assert isinstance(question, str)
    
    prompt = (
        "You are CryptCare's AI Medical Assistant interacting directly with a patient. "
        "You help patients understand medications and general health concepts. "
        "CRITICAL RULES: "
        "1. Do not diagnose any condition. "
        "2. Do not suggest or prescribe new medications or treatments. "
        "3. Do not advise on changing medication dosages or stopping medications. "
        "4. Keep your answers concise, reassuring, and educational. "
        "5. Always recommend consulting their doctor for specific or urgent concerns. "
        "If the patient asks anything that violates these rules, gently decline and tell them to ask their doctor.\n\n"
        f"Patient Question: {question}"
    )
    return _call_ollama(prompt)
