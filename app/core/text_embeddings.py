"""
Deterministic, dependency-free text embeddings via the hashing trick.

Why hand-rolled instead of a pretrained model: matching a doctor-typed
medicine name ("amoxicilin", "Augmentin 625mg") against a canonical drug
list doesn't need semantic understanding — it needs robustness to typos,
casing, brand-name variants, and trailing dosage text. A character n-gram
hash embedding gives FAISS something meaningful to do approximate nearest-
neighbor search over, with zero external dependencies (no model download,
no internet access, no GPU) — consistent with this project's "no third-party
API calls on PHI-adjacent paths" stance, and it works identically in any
environment including fully air-gapped ones.
"""

import hashlib
import re
import numpy as np

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _stable_hash(token: str) -> int:
    # Python's built-in hash() is salted per-process (PYTHONHASHSEED) for
    # security reasons — great for dict lookups, disastrous here, since it
    # would make the same drug name embed differently every time the server
    # restarts and silently desync from whatever FAISS index was built
    # earlier. md5 is deterministic across processes/machines/restarts,
    # which is the only property that matters for this use case (not
    # cryptographic strength).
    return int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)


def _normalize(text: str) -> str:
    return text.strip().lower()


def _char_trigrams(text: str) -> list[str]:
    """Padded character trigrams, e.g. 'amox' -> ['  a', ' am', 'amo', 'mox', 'ox ']."""
    padded = f"  {text} "
    return [padded[i:i + 3] for i in range(len(padded) - 2)]


def embed(text: str, dim: int = 256) -> np.ndarray:
    """
    Hashing-trick bag-of-trigrams embedding, L2-normalized.

    Strips trailing dosage/form tokens (numbers, "mg", "ml", "tablet", etc.)
    before vectorizing so "Amoxicillin 500mg" and "amoxicillin" land close
    together — a doctor's free-text medicine_name field routinely includes
    dosage, which is irrelevant to *which drug* this is.
    """
    normalized = _normalize(text)
    tokens = _TOKEN_RE.findall(normalized)
    # Drop pure-numeric tokens and common dosage-unit/form words.
    _NOISE = {"mg", "mcg", "ml", "g", "iu", "tablet", "tablets", "capsule", "capsules", "cap", "caps"}
    core_tokens = [t for t in tokens if not t.isdigit() and t not in _NOISE]
    core_text = " ".join(core_tokens) if core_tokens else normalized

    vec = np.zeros(dim, dtype=np.float32)
    for trigram in _char_trigrams(core_text):
        h = _stable_hash(trigram) % dim
        vec[h] += 1.0

    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


def embed_batch(texts: list[str], dim: int = 256) -> np.ndarray:
    return np.stack([embed(t, dim) for t in texts]) if texts else np.zeros((0, dim), dtype=np.float32)
