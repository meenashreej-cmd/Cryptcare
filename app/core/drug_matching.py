"""
Phase 7 — FAISS-backed fuzzy drug-name matching.

Maps a doctor's free-text medicine_name ("Amoxicillin 500mg", "augmentin",
a typo like "ibuprofin") to a canonical drug key from
app.data.drug_knowledge_base.CANONICAL_DRUGS, so the interaction/allergy/
duplicate rules in clinical_safety_service can key off a normalized name
instead of doing brittle exact-string matching.

The index is built once at import time from a small, fixed drug list — cheap
enough that there's no need for persistence/caching infrastructure here.
"""

import faiss
import numpy as np

from app.core.text_embeddings import embed, embed_batch
from app.data.drug_knowledge_base import CANONICAL_DRUGS

_EMBED_DIM = 256

# IndexFlatIP over L2-normalized vectors == cosine similarity search.
# Exact (not approximate) search — the canonical list is tiny (dozens of
# entries), so there's no accuracy/speed tradeoff to make here; if this
# dataset grows to real production drug-database size (tens of thousands of
# entries), swap to an IVF/HNSW index for speed.
_index = faiss.IndexFlatIP(_EMBED_DIM)
_index.add(embed_batch(CANONICAL_DRUGS, dim=_EMBED_DIM))


def match_drug_name(raw_name: str, similarity_threshold: float = 0.55) -> tuple[str | None, float]:
    """
    Returns (canonical_name, similarity) for the closest known drug, or
    (None, best_similarity_seen) if nothing clears the threshold — callers
    should treat a None match as "unknown drug, not necessarily unsafe,
    just outside what this curated dataset knows about", not as an error.
    """
    if not raw_name or not raw_name.strip():
        return None, 0.0

    query = embed(raw_name, dim=_EMBED_DIM).reshape(1, -1).astype(np.float32)
    similarities, indices = _index.search(query, k=1)
    best_similarity = float(similarities[0][0])
    best_index = int(indices[0][0])

    if best_index < 0 or best_similarity < similarity_threshold:
        return None, best_similarity
    return CANONICAL_DRUGS[best_index], best_similarity
