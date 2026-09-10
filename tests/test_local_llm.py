"""
Phase 7 — local LLM explanation generation degrades gracefully.

Ollama is not running in this test environment (nor in most CI environments),
so this exercises exactly the path every test in test_clinical_safety.py
already relies on implicitly: explain_safety_findings() returning None when
unreachable, with clinical_safety_service falling back to a deterministic
template rather than raising or hanging.
"""

from app.core.config import settings
from app.core.local_llm import explain_safety_findings
from app.services.clinical_safety_service import _template_explanation


def test_explain_safety_findings_returns_none_when_ollama_unreachable():
    # settings.LOCAL_LLM_BASE_URL points at the default localhost:11434,
    # which has nothing listening in this test environment — this must fail
    # closed (None), not raise.
    result = explain_safety_findings({"interactions": {"results": []}, "allergies": {"conflicts": []}, "duplicates": {"duplicates": []}})
    assert result is None


def test_explain_safety_findings_respects_disabled_flag():
    original = settings.LOCAL_LLM_ENABLED
    try:
        settings.LOCAL_LLM_ENABLED = False
        result = explain_safety_findings({"anything": "at all"})
        assert result is None
    finally:
        settings.LOCAL_LLM_ENABLED = original


def test_template_explanation_covers_clean_case():
    findings = {
        "interactions": {"results": []},
        "allergies": {"conflicts": []},
        "duplicates": {"duplicates": []},
        "unmatched_drugs": [],
    }
    text = _template_explanation(findings)
    assert "no interaction" in text.lower() or "no findings" in text.lower() or "no concerns" in text.lower() or "concerns found" in text.lower()


def test_template_explanation_covers_severe_and_allergy_case():
    findings = {
        "interactions": {"results": [{"drug_a": "warfarin", "drug_b": "aspirin", "severity": "SEVERE", "description": "x"}]},
        "allergies": {"conflicts": [{"drug": "amoxicillin", "allergen": "penicillin"}]},
        "duplicates": {"duplicates": []},
        "unmatched_drugs": [],
    }
    text = _template_explanation(findings)
    assert "allerg" in text.lower()
    assert "warfarin" in text.lower() and "aspirin" in text.lower()
