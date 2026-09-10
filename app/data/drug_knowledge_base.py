"""
Phase 7 — curated clinical reference data for drug-interaction / allergy-class
/ duplicate-therapy checking.

*** NOT A CLINICAL DATABASE. DO NOT DEPLOY THIS DATASET AS-IS. ***

This is a small, hand-picked set of well-known, textbook drug interactions
and allergy cross-reactivity classes — the kind of thing found in any
first-year pharmacology course or a public interaction checker like
Drugs.com — included purely to make Phase 7's architecture (FAISS-based
fuzzy name matching -> rule evaluation -> optional LLM explanation)
demonstrable and testable. It is:
  - NOT exhaustive (dozens of clinically important interaction classes are
    simply absent because they weren't picked for this illustrative set)
  - NOT dosage/route/patient-factor aware (real interaction severity often
    depends on dose, renal/hepatic function, age, and more)
  - NOT a substitute for a licensed drug database (e.g. a real RxNorm-backed
    interaction API, First Databank, Micromedex, or equivalent) or for
    pharmacist/clinician review

A real deployment MUST replace this module with a licensed, regularly-updated
data source before this check is trusted for actual patient care. Treat
clinical_safety_service's output as a helpful second pair of eyes, never as
sign-off.
"""

# Canonical (lowercase) drug name -> allergen class(es) it belongs to, for
# cross-reactivity checking against a patient's recorded Allergy.allergen.
# Keys on the right are matched case-insensitively against the patient's
# stored allergen string.
DRUG_ALLERGY_CLASSES: dict[str, list[str]] = {
    "amoxicillin": ["penicillin"],
    "ampicillin": ["penicillin"],
    "penicillin v": ["penicillin"],
    "augmentin": ["penicillin"],
    "sulfamethoxazole": ["sulfa", "sulfonamides"],
    "trimethoprim-sulfamethoxazole": ["sulfa", "sulfonamides"],
    "ibuprofen": ["nsaids"],
    "naproxen": ["nsaids"],
    "aspirin": ["nsaids", "aspirin"],
    "clarithromycin": ["macrolides"],
    "erythromycin": ["macrolides"],
}

# Canonical drug names known to the matcher — every key that appears above,
# plus drugs that only participate in interaction pairs (no allergy class).
# This is what the FAISS index in app/core/drug_matching.py is built over.
CANONICAL_DRUGS: list[str] = sorted(set(DRUG_ALLERGY_CLASSES) | {
    "warfarin",
    "clopidogrel",
    "ciprofloxacin",
    "metformin",
    "lisinopril",
    "enalapril",
    "spironolactone",
    "potassium chloride",
    "simvastatin",
    "atorvastatin",
    "sertraline",
    "fluoxetine",
    "phenelzine",
    "tramadol",
    "digoxin",
    "amiodarone",
    "levothyroxine",
    "omeprazole",
})

# One entry per unordered drug pair. Both directions are checked by the
# service layer — a pair only needs to be listed once here.
#   severity: "SEVERE" (blocks prescription creation) | "MODERATE" (flagged,
#   does not block — surfaced as a warning so the doctor can review/override)
DRUG_INTERACTIONS: list[dict] = [
    {"a": "warfarin", "b": "aspirin", "severity": "SEVERE",
     "description": "Combining an anticoagulant with aspirin substantially increases the risk of major bleeding."},
    {"a": "warfarin", "b": "ibuprofen", "severity": "SEVERE",
     "description": "NSAIDs combined with warfarin increase bleeding risk via platelet inhibition and GI mucosal effects."},
    {"a": "warfarin", "b": "naproxen", "severity": "SEVERE",
     "description": "NSAIDs combined with warfarin increase bleeding risk via platelet inhibition and GI mucosal effects."},
    {"a": "warfarin", "b": "ciprofloxacin", "severity": "MODERATE",
     "description": "Fluoroquinolones can potentiate warfarin's anticoagulant effect — INR monitoring recommended."},
    {"a": "clopidogrel", "b": "aspirin", "severity": "MODERATE",
     "description": "Increased bleeding risk when combined; sometimes intentionally co-prescribed under specialist supervision (e.g. post-stent) — flag for review, not an automatic contraindication."},
    {"a": "clopidogrel", "b": "omeprazole", "severity": "MODERATE",
     "description": "Omeprazole may reduce clopidogrel's antiplatelet effectiveness via CYP2C19 inhibition."},
    {"a": "simvastatin", "b": "clarithromycin", "severity": "SEVERE",
     "description": "Macrolide antibiotics strongly inhibit statin metabolism (CYP3A4), raising myopathy/rhabdomyolysis risk."},
    {"a": "simvastatin", "b": "erythromycin", "severity": "SEVERE",
     "description": "Macrolide antibiotics strongly inhibit statin metabolism (CYP3A4), raising myopathy/rhabdomyolysis risk."},
    {"a": "lisinopril", "b": "spironolactone", "severity": "SEVERE",
     "description": "Combining an ACE inhibitor with a potassium-sparing diuretic risks dangerous hyperkalemia."},
    {"a": "enalapril", "b": "spironolactone", "severity": "SEVERE",
     "description": "Combining an ACE inhibitor with a potassium-sparing diuretic risks dangerous hyperkalemia."},
    {"a": "lisinopril", "b": "potassium chloride", "severity": "MODERATE",
     "description": "ACE inhibitors combined with potassium supplements raise the risk of hyperkalemia — monitor potassium levels."},
    {"a": "sertraline", "b": "phenelzine", "severity": "SEVERE",
     "description": "Combining an SSRI with an MAOI risks serotonin syndrome — these generally must not be co-prescribed."},
    {"a": "fluoxetine", "b": "phenelzine", "severity": "SEVERE",
     "description": "Combining an SSRI with an MAOI risks serotonin syndrome — these generally must not be co-prescribed."},
    {"a": "sertraline", "b": "tramadol", "severity": "MODERATE",
     "description": "Combined serotonergic effect increases seizure and serotonin syndrome risk."},
    {"a": "digoxin", "b": "amiodarone", "severity": "SEVERE",
     "description": "Amiodarone raises digoxin blood levels, increasing the risk of digoxin toxicity — dose adjustment usually required."},
]
