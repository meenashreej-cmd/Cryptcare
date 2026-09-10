"""
Phase 7 — Clinical Safety Validation.

Uses the same db-fixture + direct-token pattern as tests/test_nursing.py.
Covers: a SEVERE interaction blocks prescription creation (422), an allergy
conflict blocks, a MODERATE interaction / duplicate therapy is surfaced as a
non-blocking warning on a successful 201, and an unrecognized drug name
neither blocks nor crashes.
"""

from app.core.security import create_access_token, hash_password
from app.models.user import DoctorProfile, PatientProfile, RoleEnum, User, UserStatusEnum
from app.services.auth_service import ROLE_PERMISSIONS
from unittest.mock import patch

class DummyDrugMatching:
    @staticmethod
    def match_drug_name(raw_name: str, similarity_threshold: float = 0.55):
        if not raw_name: return None, 0.0
        raw_lower = raw_name.lower().strip()
        canonical_drugs = [
            "amoxicillin", "ampicillin", "penicillin v", "augmentin", 
            "sulfamethoxazole", "trimethoprim-sulfamethoxazole", "ibuprofen", 
            "naproxen", "aspirin", "clarithromycin", "erythromycin", "warfarin",
            "clopidogrel", "ciprofloxacin", "metformin", "lisinopril", 
            "enalapril", "spironolactone", "potassium chloride", "simvastatin", 
            "atorvastatin", "sertraline", "fluoxetine", "phenelzine", 
            "tramadol", "digoxin", "amiodarone", "levothyroxine", "omeprazole"
        ]
        for c in canonical_drugs:
            if c in raw_lower:
                return c, 1.0
        return None, 0.0


def _make_user(db, email, role, **profile_kwargs):
    user = User(
        email=email,
        phone=f"+1{abs(hash(email)) % 10**9:09d}",
        password_hash=hash_password("Password123!"),
        role=role,
        full_name=f"Test {role.value.title()}",
        status=UserStatusEnum.ACTIVE,
    )
    db.add(user)
    db.flush()

    if role == RoleEnum.PATIENT:
        profile = PatientProfile(user_id=user.user_id, **profile_kwargs)
    elif role == RoleEnum.DOCTOR:
        profile = DoctorProfile(user_id=user.user_id, license_number="DOC-SAFETY-001", **profile_kwargs)
    else:
        db.commit()
        return user, None

    db.add(profile)
    db.commit()
    return user, profile


def _auth_header(user_id: str, role: RoleEnum) -> dict:
    token = create_access_token(user_id=user_id, role=role.value, permissions=ROLE_PERMISSIONS.get(role, []))
    return {"Authorization": f"Bearer {token}"}


def _grant_prescription_consent(client, patient_headers, doctor_headers, patient_id):
    req = client.post(
        "/api/v1/consent/request",
        json={"patient_id": patient_id, "resource_type": "prescriptions", "permission": "BOTH"},
        headers=doctor_headers,
    )
    assert req.status_code == 201, req.text
    consent_id = req.json()["consent_id"]
    approve = client.put(f"/api/v1/consent/{consent_id}/approve", json={"duration_days": 30}, headers=patient_headers)
    assert approve.status_code == 200, approve.text


def _setup_patient_and_doctor(db, client, suffix):
    patient_user, patient_profile = _make_user(db, f"safety_patient_{suffix}@medivault.ai", RoleEnum.PATIENT)
    doctor_user, _ = _make_user(db, f"safety_doctor_{suffix}@medivault.ai", RoleEnum.DOCTOR)
    patient_headers = _auth_header(patient_user.user_id, RoleEnum.PATIENT)
    doctor_headers = _auth_header(doctor_user.user_id, RoleEnum.DOCTOR)
    _grant_prescription_consent(client, patient_headers, doctor_headers, patient_profile.patient_id)
    return patient_profile.patient_id, patient_headers, doctor_headers


def _prescribe(client, doctor_headers, patient_id, medicine_names, diagnosis="Test diagnosis"):
    return client.post(
        "/api/v1/vault/prescriptions",
        json={
            "patient_id": patient_id,
            "diagnosis": diagnosis,
            "items": [{"medicine_name": name} for name in medicine_names],
        },
        headers=doctor_headers,
    )


@patch('app.services.clinical_safety_service.match_drug_name', new=DummyDrugMatching.match_drug_name)
def test_unit_severe_interaction_blocks_prescription(client, db):
    patient_id, patient_headers, doctor_headers = _setup_patient_and_doctor(db, client, "severe_int")

    resp = _prescribe(client, doctor_headers, patient_id, ["Warfarin", "Aspirin"])
    assert resp.status_code == 422, resp.text
    body = resp.json()["detail"]
    assert body["safety"]["blocking"] is True
    assert any(r["severity"] == "SEVERE" for r in body["safety"]["interactions"]["results"])


@patch('app.services.clinical_safety_service.match_drug_name', new=DummyDrugMatching.match_drug_name)
def test_unit_severe_interaction_blocks_against_existing_active_prescription(client, db):
    patient_id, patient_headers, doctor_headers = _setup_patient_and_doctor(db, client, "severe_existing")

    first = _prescribe(client, doctor_headers, patient_id, ["Warfarin"])
    assert first.status_code == 201, first.text

    second = _prescribe(client, doctor_headers, patient_id, ["Aspirin"], diagnosis="Different visit")
    assert second.status_code == 422, second.text


@patch('app.services.clinical_safety_service.match_drug_name', new=DummyDrugMatching.match_drug_name)
def test_unit_allergy_conflict_blocks_prescription(client, db):
    patient_id, patient_headers, doctor_headers = _setup_patient_and_doctor(db, client, "allergy")

    allergy_resp = client.post(
        f"/api/v1/vault/allergies?patient_id={patient_id}",
        json={"allergen": "penicillin", "severity": "SEVERE"},
        headers=patient_headers,
    )
    assert allergy_resp.status_code == 201, allergy_resp.text

    resp = _prescribe(client, doctor_headers, patient_id, ["Amoxicillin 500mg"])
    assert resp.status_code == 422, resp.text
    body = resp.json()["detail"]
    assert body["safety"]["allergies"]["blocking"] is True
    assert body["safety"]["allergies"]["conflicts"][0]["drug"] == "amoxicillin"


@patch('app.services.clinical_safety_service.match_drug_name', new=DummyDrugMatching.match_drug_name)
def test_unit_moderate_interaction_warns_but_does_not_block(client, db):
    patient_id, patient_headers, doctor_headers = _setup_patient_and_doctor(db, client, "moderate")

    resp = _prescribe(client, doctor_headers, patient_id, ["Clopidogrel", "Aspirin"])
    assert resp.status_code == 201, resp.text
    warnings = resp.json()["safety_warnings"]
    assert warnings is not None
    assert any(r["severity"] == "MODERATE" for r in warnings["interactions"]["results"])


@patch('app.services.clinical_safety_service.match_drug_name', new=DummyDrugMatching.match_drug_name)
def test_unit_duplicate_therapy_flagged_as_non_blocking_warning(client, db):
    patient_id, patient_headers, doctor_headers = _setup_patient_and_doctor(db, client, "duplicate")

    first = _prescribe(client, doctor_headers, patient_id, ["Metformin"])
    assert first.status_code == 201, first.text

    second = _prescribe(client, doctor_headers, patient_id, ["Metformin 500mg"], diagnosis="Follow-up")
    assert second.status_code == 201, second.text
    warnings = second.json()["safety_warnings"]
    assert warnings is not None
    assert "metformin" in warnings["duplicates"]["duplicates"]


@patch('app.services.clinical_safety_service.match_drug_name', new=DummyDrugMatching.match_drug_name)
def test_unit_unrecognized_drug_name_does_not_block(client, db):
    patient_id, patient_headers, doctor_headers = _setup_patient_and_doctor(db, client, "unknown")

    resp = _prescribe(client, doctor_headers, patient_id, ["Zorblaxin 10mg"])
    assert resp.status_code == 201, resp.text
    warnings = resp.json().get("safety_warnings")
    # unmatched drug should be reported but never block creation
    assert warnings is not None
    assert "Zorblaxin 10mg" in warnings["unmatched_drugs"]


@patch('app.services.clinical_safety_service.match_drug_name', new=DummyDrugMatching.match_drug_name)
def test_unit_clean_prescription_has_no_safety_warnings(client, db):
    patient_id, patient_headers, doctor_headers = _setup_patient_and_doctor(db, client, "clean")

    resp = _prescribe(client, doctor_headers, patient_id, ["Levothyroxine"])
    assert resp.status_code == 201, resp.text
    assert resp.json()["safety_warnings"] is None


# --------------------------------------------------------------------------
# INTEGRATION TESTS - Using the REAL FAISS engine and drug hashing
# --------------------------------------------------------------------------

def test_integration_severe_interaction_blocks_prescription(client, db):
    patient_id, patient_headers, doctor_headers = _setup_patient_and_doctor(db, client, "int_severe")

    # Real engine should match these regardless of casing/spacing
    resp = _prescribe(client, doctor_headers, patient_id, ["Warfarin", "ASPIRIN 81mg"])
    assert resp.status_code == 422, resp.text
    body = resp.json()["detail"]
    assert body["safety"]["blocking"] is True
    assert any(r["severity"] == "SEVERE" for r in body["safety"]["interactions"]["results"])


def test_integration_allergy_conflict_blocks_prescription(client, db):
    patient_id, patient_headers, doctor_headers = _setup_patient_and_doctor(db, client, "int_allergy")

    # Record Penicillin allergy
    allergy_resp = client.post(
        f"/api/v1/vault/allergies?patient_id={patient_id}",
        json={"allergen": "penicillin", "severity": "SEVERE"},
        headers=patient_headers,
    )
    assert allergy_resp.status_code == 201, allergy_resp.text

    # Prescribing Amoxicillin (a penicillin-class drug in the real dataset) should block
    resp = _prescribe(client, doctor_headers, patient_id, ["Amoxicillin 500mg"])
    assert resp.status_code == 422, resp.text
    body = resp.json()["detail"]
    assert body["safety"]["allergies"]["blocking"] is True
    assert body["safety"]["allergies"]["conflicts"][0]["drug"] == "amoxicillin"


def test_integration_moderate_interaction_warns(client, db):
    patient_id, patient_headers, doctor_headers = _setup_patient_and_doctor(db, client, "int_mod")

    resp = _prescribe(client, doctor_headers, patient_id, ["Clopidogrel 75mg", "Aspirin 81mg"])
    assert resp.status_code == 201, resp.text
    warnings = resp.json()["safety_warnings"]
    assert warnings is not None
    assert any(r["severity"] == "MODERATE" for r in warnings["interactions"]["results"])


def test_integration_clean_prescription_passes(client, db):
    patient_id, patient_headers, doctor_headers = _setup_patient_and_doctor(db, client, "int_clean")

    resp = _prescribe(client, doctor_headers, patient_id, ["Levothyroxine 50mcg"])
    assert resp.status_code == 201, resp.text
    assert resp.json()["safety_warnings"] is None
