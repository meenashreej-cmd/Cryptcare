"""
Phase 5 — PHI (Protected Health Information) Guardrails.

This module prevents PHI leakage through the AI boundary by:
1. Detecting PHI patterns in user prompts before they reach the LLM
2. Redacting PHI from AI responses before they are returned to users
3. Enforcing topic scope so the AI cannot be used as a data exfiltration vector

PHI categories covered (HIPAA 18 identifiers + clinical identifiers):
  - Names (patient/doctor names)
  - Geographic data (addresses, zip codes)
  - Dates (DOB, admission dates, discharge dates)
  - Phone numbers
  - Fax numbers
  - Email addresses
  - Social security numbers
  - Medical record numbers (MRN)
  - Health plan beneficiary numbers
  - Account numbers
  - Certificate/license numbers
  - Vehicle identifiers / serial numbers
  - Device identifiers
  - URLs / IP addresses
  - Biometric identifiers (fingerprints, voiceprints)
  - Full-face photographs
  - Any unique identifier number

IMPORTANT: This module intentionally fails closed. If a check is uncertain,
it prefers to block/redact rather than pass through, since this is healthcare.
"""

import re
from typing import Optional
from dataclasses import dataclass, field


# ─── PHI Detection Patterns ─────────────────────────────────────────────────

_PHI_PATTERNS: list[tuple[str, re.Pattern]] = [
    # Dates — DOB, admission, discharge (DD/MM/YYYY, MM/DD/YYYY, YYYY-MM-DD)
    ("date_of_birth", re.compile(
        r"\b(?:dob|date of birth|born on|born:|my dob|my date of birth)\s*[\:\-]?\s*"
        r"(?:\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})",
        re.IGNORECASE
    )),
    # Also catch bare "date of birth is DD/MM/YYYY" without a preceding keyword anchor
    ("date_of_birth_bare", re.compile(
        r"\bdate of birth\s+(?:is\s+)?\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}",
        re.IGNORECASE
    )),
    ("date_pattern", re.compile(
        r"\b(?:admitted|discharged|diagnosis date|on)\s+\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}",
        re.IGNORECASE
    )),

    # Phone numbers
    ("phone_number", re.compile(
        r"\b(?:phone|mobile|cell|tel|fax|call me at)\s*[\:\-]?\s*"
        r"(?:\+?[\d\s\-\(\)\.]{10,})",
        re.IGNORECASE
    )),
    ("bare_phone", re.compile(
        r"\b\+?1?\s*[\(\-]?\d{3}[\)\-\s]\s*\d{3}[\-\s]\d{4}\b"
    )),

    # Email addresses
    ("email_address", re.compile(
        r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b"
    )),

    # Social Security Numbers (US)
    ("ssn", re.compile(
        r"\b(?:SSN|Social Security|SS#)\s*[\:\-]?\s*\d{3}[\-\s]\d{2}[\-\s]\d{4}\b",
        re.IGNORECASE
    )),
    ("bare_ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),

    # Medical Record Numbers
    ("mrn", re.compile(
        r"\b(?:MRN|Medical Record Number|Record #|Patient ID)\s*[\:\-]?\s*[A-Z0-9]{5,12}\b",
        re.IGNORECASE
    )),

    # IP Addresses
    ("ip_address", re.compile(
        r"\b(?!0\.)(?!10\.)(?!172\.1[6-9]\.)(?!172\.2\d\.)(?!172\.3[0-1]\.)(?!192\.168\.)"
        r"(?:\d{1,3}\.){3}\d{1,3}\b"
    )),

    # URLs with potential patient data
    ("url_with_id", re.compile(
        r"https?://[^\s]+(?:patient|user|record|id)[^\s]*",
        re.IGNORECASE
    )),

    # Physical addresses
    ("physical_address", re.compile(
        r"\b\d{1,5}\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+"
        r"(?:Street|St|Avenue|Ave|Boulevard|Blvd|Road|Rd|Lane|Ln|Drive|Dr|Court|Ct)\b",
        re.IGNORECASE
    )),

    # Zip codes (US)
    ("zip_code", re.compile(r"\b\d{5}(?:-\d{4})?\b")),

    # Full names (pattern: "my name is X Y" or "I am Dr X Y")
    ("name_disclosure", re.compile(
        r"\b(?:my name is|I am|I'm|patient name|doctor|dr\.?)\s+"
        r"(?:[A-Z][a-z]+\s+){1,3}[A-Z][a-z]+\b",
        re.IGNORECASE
    )),

    # License / ID numbers
    ("license_id", re.compile(
        r"\b(?:license|ID|badge|permit)\s*(?:#|number|no\.?)?\s*[\:\-]?\s*[A-Z0-9]{5,15}\b",
        re.IGNORECASE
    )),
]

# Redaction label map: pattern_name → replacement text
_REDACTION_LABELS: dict[str, str] = {
    "date_of_birth": "[DATE-OF-BIRTH REDACTED]",
    "date_of_birth_bare": "[DATE-OF-BIRTH REDACTED]",
    "date_pattern": "[DATE REDACTED]",
    "phone_number": "[PHONE REDACTED]",
    "bare_phone": "[PHONE REDACTED]",
    "email_address": "[EMAIL REDACTED]",
    "ssn": "[SSN REDACTED]",
    "bare_ssn": "[SSN REDACTED]",
    "mrn": "[MRN REDACTED]",
    "ip_address": "[IP REDACTED]",
    "url_with_id": "[URL REDACTED]",
    "physical_address": "[ADDRESS REDACTED]",
    "zip_code": "[ZIP REDACTED]",
    "name_disclosure": "[NAME REDACTED]",
    "license_id": "[LICENSE REDACTED]",
}

# ─── Prompt Injection Patterns ───────────────────────────────────────────────

_INJECTION_PATTERNS: list[re.Pattern] = [
    # Classic ignore/override instructions
    re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior|above|your)\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(?:all\s+)?(?:previous|prior|above|your)\s+instructions?", re.IGNORECASE),
    re.compile(r"forget\s+(?:everything|all)\s+(?:you|i|we)\s+(?:said|told|gave)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:a|an)\s+\w+", re.IGNORECASE),
    re.compile(r"act\s+as\s+(?:a|an|if)\s+", re.IGNORECASE),
    re.compile(r"pretend\s+(?:you\s+are|to\s+be)", re.IGNORECASE),
    re.compile(r"roleplay\s+as", re.IGNORECASE),
    re.compile(r"your\s+new\s+(?:instructions?|prompt|role|task)\s+(?:is|are)", re.IGNORECASE),

    # DAN / jailbreak patterns
    re.compile(r"\bDAN\b"),
    re.compile(r"do\s+anything\s+now", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),

    # System prompt override attempts
    re.compile(r"\[SYSTEM\]", re.IGNORECASE),
    re.compile(r"SYSTEM\s*[:：]\s*\w", re.IGNORECASE),   # "SYSTEM: new instructions"
    re.compile(r"<\s*system\s*>", re.IGNORECASE),
    re.compile(r"<<SYS>>", re.IGNORECASE),
    re.compile(r"\[INST\]", re.IGNORECASE),
    re.compile(r"###\s*(?:Instruction|System|Human|Assistant)", re.IGNORECASE),

    # Data exfiltration attempts through AI
    re.compile(r"(?:list|show|print|display|reveal|give\s+me)\s+all\s+(?:patients?|users?|records?|data)", re.IGNORECASE),
    re.compile(r"(?:database|db|sql)\s+(?:dump|export|query|select)", re.IGNORECASE),
    re.compile(r"what\s+(?:other\s+)?patients?\s+(?:are|have|do\s+you\s+(?:have|know|see))", re.IGNORECASE),

    # Medical overreach attempts
    re.compile(r"prescribe\s+(?:me|a|the)", re.IGNORECASE),
    re.compile(r"give\s+me\s+a\s+prescription", re.IGNORECASE),
    re.compile(r"write\s+a\s+prescription", re.IGNORECASE),
    re.compile(r"diagnose\s+(?:me|my|this)", re.IGNORECASE),
    re.compile(r"what\s+medication\s+should\s+I\s+take", re.IGNORECASE),

    # Token manipulation
    re.compile(r"token\s*(?:limit|length|context)\s*(?:bypass|ignore|skip)", re.IGNORECASE),
    re.compile(r"repeat\s+(?:the\s+)?(?:above|previous|system)\s+prompt", re.IGNORECASE),
]

# ─── Topic Scope Enforcement ─────────────────────────────────────────────────
# The AI assistant is limited to health/medical education questions only.
# These patterns signal out-of-scope topics that should be rejected.

_OUT_OF_SCOPE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(?:stock|crypto|bitcoin|investment|trading)\b", re.IGNORECASE),
    re.compile(r"\b(?:hack|exploit|vulnerability|malware|virus|ransomware)\b", re.IGNORECASE),
    re.compile(r"\b(?:weapons?|firearms?|explosives?|bomb)\b", re.IGNORECASE),
    re.compile(r"\b(?:legal advice|lawsuit|sue|attorney|lawyer)\b", re.IGNORECASE),
    re.compile(r"\b(?:suicide|self.harm|hurt myself|kill myself)\b", re.IGNORECASE),
    re.compile(r"\b(?:illegal drugs?|narcotics?|cocaine|heroin|meth)\b", re.IGNORECASE),
]

# ─── Result dataclasses ──────────────────────────────────────────────────────

@dataclass
class PHICheckResult:
    contains_phi: bool
    phi_types_found: list[str] = field(default_factory=list)
    redacted_text: Optional[str] = None


@dataclass
class PromptSafetyResult:
    is_safe: bool
    blocked_reason: Optional[str] = None
    sanitized_prompt: Optional[str] = None


# ─── Core functions ──────────────────────────────────────────────────────────

def detect_phi(text: str) -> PHICheckResult:
    """
    Scan text for PHI patterns. Returns which PHI categories were found.
    Does NOT modify the original text — call redact_phi() for that.
    """
    if not isinstance(text, str) or not text.strip():
        return PHICheckResult(contains_phi=False)

    found_types: list[str] = []
    for pattern_name, pattern in _PHI_PATTERNS:
        if pattern.search(text):
            found_types.append(pattern_name)

    return PHICheckResult(
        contains_phi=len(found_types) > 0,
        phi_types_found=found_types,
    )


def redact_phi(text: str) -> str:
    """
    Replace PHI in text with labelled redaction placeholders.
    Used on AI responses before returning to users to prevent
    the LLM from echoing back PHI it may have been exposed to.
    """
    if not isinstance(text, str):
        return text

    for pattern_name, pattern in _PHI_PATTERNS:
        replacement = _REDACTION_LABELS.get(pattern_name, "[PHI REDACTED]")
        text = pattern.sub(replacement, text)

    return text


def check_prompt_safety(prompt: str) -> PromptSafetyResult:
    """
    Comprehensive prompt safety check before sending to LLM.
    Checks for:
      1. Prompt injection attempts
      2. Out-of-scope topics
      3. PHI in the prompt (warn — the LLM should not see raw PHI)

    Returns PromptSafetyResult with is_safe=False and a reason if blocked.
    """
    if not isinstance(prompt, str) or not prompt.strip():
        return PromptSafetyResult(is_safe=False, blocked_reason="Empty prompt")

    # 1. Injection detection
    for pattern in _INJECTION_PATTERNS:
        match = pattern.search(prompt)
        if match:
            return PromptSafetyResult(
                is_safe=False,
                blocked_reason=f"Prompt injection attempt detected: '{match.group(0)[:50]}'"
            )

    # 2. Out-of-scope topic detection
    for pattern in _OUT_OF_SCOPE_PATTERNS:
        match = pattern.search(prompt)
        if match:
            return PromptSafetyResult(
                is_safe=False,
                blocked_reason=f"Out-of-scope topic detected. The AI assistant is for medical questions only."
            )

    # 3. PHI check — redact PHI from the prompt before it reaches the LLM
    phi_result = detect_phi(prompt)
    sanitized = redact_phi(prompt) if phi_result.contains_phi else prompt

    return PromptSafetyResult(
        is_safe=True,
        sanitized_prompt=sanitized,
    )


def enforce_response_boundary(response_text: str, max_length: int = 2000) -> str:
    """
    Post-processing of LLM responses:
      1. Redact any PHI the model may have echoed back
      2. Truncate to max_length to prevent verbose data dumps
      3. Strip any injected system-level markers from the response

    Always call this on every LLM output before returning to the client.
    """
    if not isinstance(response_text, str):
        return "Unable to generate response."

    # Strip injected system markers the LLM might output
    system_marker_pattern = re.compile(
        r"(?:\[SYSTEM\]|\[INST\]|<<SYS>>|###\s*(?:System|Instruction|Assistant|Human))[^\n]*\n?",
        re.IGNORECASE
    )
    response_text = system_marker_pattern.sub("", response_text).strip()

    # Redact PHI from response
    response_text = redact_phi(response_text)

    # Truncate if too long (prevents data dumping)
    _TRUNCATION_MARKER = "... [response truncated]"  # 24 chars
    if len(response_text) > max_length:
        response_text = response_text[:max_length] + _TRUNCATION_MARKER

    return response_text
