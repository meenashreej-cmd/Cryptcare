"""
Phase 7 — Clinical Safety Validation.

Replaces the always-safe stub. Three deterministic, rule-based checks run
against a curated dataset (see app.data.drug_knowledge_base — READ THE
DISCLAIMER THERE before treating this as clinically authoritative):

  1. interactions — pairwise drug-interaction lookup, both within the new
     prescription's items and against the patient's other ACTIVE
     prescriptions. SEVERE interactions block; MODERATE ones are surfaced
     as warnings but don't block.
  2. allergies — cross-checks each new item's allergen class against the
     patient's recorded Allergy rows. Any match blocks.
  3. duplicates — flags a new item that matches a drug the patient already
     has an ACTIVE prescription for. Informational only — never blocks, since
     legitimate reasons for "duplicate" therapy exist (e.g. dose-splitting)
     that this system has no way to distinguish from a real error.

Drug names are resolved to a canonical form via FAISS-based fuzzy matching
(app.core.drug_matching) before any rule lookup — see that module's
docstring for why. An unmatched drug (outside the curated dataset) is
reported but never blocks; this dataset's absence of a drug says nothing
about its actual safety.

The local LLM (Ollama, via app.core.local_llm) only ever explains findings
this module already computed — it is never consulted for the blocking
decision itself, and its unavailability never changes the outcome.
"""

from itertools import combinations, product

from sqlalchemy.orm import Session

from app.core.drug_matching import match_drug_name
from app.core.local_llm import explain_safety_findings
from app.data.drug_knowledge_base import DRUG_ALLERGY_CLASSES
from app.data.drug_knowledge_base import DRUG_INTERACTIONS as _RAW_INTERACTIONS
from app.models.vault import Allergy, Prescription, PrescriptionItem, PrescriptionStatusEnum

# Two entries per pair (a,b) and (b,a) so lookup doesn't need to try both
# orders at every call site — built once at import time from the curated list.
_INTERACTION_LOOKUP: dict[tuple[str, str], dict] = {}
for _pair in _RAW_INTERACTIONS:
    _INTERACTION_LOOKUP[(_pair["a"], _pair["b"])] = _pair
    _INTERACTION_LOOKUP[(_pair["b"], _pair["a"])] = _pair


def _match_items(items: list[dict]) -> tuple[list[str], list[str]]:
    """Returns (matched_canonical_names, unmatched_raw_names) for a list of
    {"medicine_name": ...} dicts, deduplicated."""
    matched: list[str] = []
    unmatched: list[str] = []
    for item in items:
        canonical, _ = match_drug_name(item["medicine_name"])
        if canonical:
            if canonical not in matched:
                matched.append(canonical)
        elif item["medicine_name"] not in unmatched:
            unmatched.append(item["medicine_name"])
    return matched, unmatched


def _get_active_medications(db: Session, patient_id: str) -> list[str]:
    rows = (
        db.query(PrescriptionItem.medicine_name)
        .join(Prescription, PrescriptionItem.prescription_id == Prescription.prescription_id)
        .filter(Prescription.patient_id == patient_id)
        .filter(Prescription.status == PrescriptionStatusEnum.ACTIVE)
        .all()
    )
    names = [row[0] for row in rows]
    matched, _ = _match_items([{"medicine_name": n} for n in names])
    return matched


def _check_interactions(new_drugs: list[str], existing_drugs: list[str]) -> dict:
    results = []
    seen_pairs: set[tuple[str, str]] = set()

    # Within the new prescription's own items.
    pairs = list(combinations(new_drugs, 2))
    # Between new items and the patient's other active medications.
    pairs += list(product(new_drugs, existing_drugs))

    for a, b in pairs:
        if a == b:
            continue
        key = tuple(sorted((a, b)))
        if key in seen_pairs:
            continue
        seen_pairs.add(key)

        found = _INTERACTION_LOOKUP.get((a, b))
        if found:
            results.append({
                "drug_a": found["a"],
                "drug_b": found["b"],
                "severity": found["severity"],
                "description": found["description"],
            })

    blocking = any(r["severity"] == "SEVERE" for r in results)
    return {"results": results, "blocking": blocking}


def _check_allergies(db: Session, patient_id: str, new_drugs: list[str]) -> dict:
    allergy_rows = db.query(Allergy).filter(Allergy.patient_id == patient_id).all()
    patient_allergens = {row.allergen.strip().lower() for row in allergy_rows}

    conflicts = []
    for drug in new_drugs:
        drug_classes = {c.lower() for c in DRUG_ALLERGY_CLASSES.get(drug, [])}
        matched_classes = drug_classes & patient_allergens
        for allergen_class in matched_classes:
            conflicts.append({"drug": drug, "allergen": allergen_class})

    return {"conflicts": conflicts, "blocking": len(conflicts) > 0}


def _check_duplicates(new_drugs: list[str], existing_drugs: list[str]) -> dict:
    existing_set = set(existing_drugs)
    duplicates = [d for d in new_drugs if d in existing_set]
    # Never blocking by design — see module docstring.
    return {"duplicates": duplicates, "blocking": False}


def _template_explanation(findings: dict) -> str:
    """Deterministic fallback used whenever the local LLM is unavailable —
    never blocks, never depends on anything but the findings dict itself."""
    parts = []
    if findings["allergies"]["conflicts"]:
        drugs = ", ".join(c["drug"] for c in findings["allergies"]["conflicts"])
        parts.append(f"Blocked: patient has a recorded allergy conflicting with {drugs}.")
    severe = [r for r in findings["interactions"]["results"] if r["severity"] == "SEVERE"]
    if severe:
        pairs = "; ".join(f"{r['drug_a']} + {r['drug_b']}" for r in severe)
        parts.append(f"Blocked: severe interaction risk between {pairs}.")
    moderate = [r for r in findings["interactions"]["results"] if r["severity"] == "MODERATE"]
    if moderate:
        pairs = "; ".join(f"{r['drug_a']} + {r['drug_b']}" for r in moderate)
        parts.append(f"Review suggested: moderate interaction risk between {pairs}.")
    if findings["duplicates"]["duplicates"]:
        drugs = ", ".join(findings["duplicates"]["duplicates"])
        parts.append(f"Note: patient already has an active prescription for {drugs}.")
    if findings.get("unmatched_drugs"):
        drugs = ", ".join(findings["unmatched_drugs"])
        parts.append(f"Could not verify {drugs} against the known drug list — no findings either way.")
    if not parts:
        parts.append("No interaction, allergy, or duplicate-therapy concerns found in the available data.")
    return " ".join(parts)


def full_safety_check(db: Session, patient_id: str, items: list[dict]) -> dict:
    new_drugs, unmatched = _match_items(items)
    existing_drugs = _get_active_medications(db, patient_id)

    interactions = _check_interactions(new_drugs, existing_drugs)
    allergies = _check_allergies(db, patient_id, new_drugs)
    duplicates = _check_duplicates(new_drugs, existing_drugs)

    findings = {
        "interactions": interactions,
        "allergies": allergies,
        "duplicates": duplicates,
        "unmatched_drugs": unmatched,
        "blocking": interactions["blocking"] or allergies["blocking"],
    }

    findings["explanation"] = explain_safety_findings(findings) or _template_explanation(findings)
    findings["disclaimer"] = (
        "Automated check against a small illustrative dataset — not a substitute for "
        "pharmacist or clinician review. See app/data/drug_knowledge_base.py."
    )
    return findings
