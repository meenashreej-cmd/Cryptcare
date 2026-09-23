
import pytest
from app.models.audit import AccessLog, AccessActionEnum
from app.models.user import RoleEnum
from app.services.consent_service import get_patient_timeline
from tests.test_lab_and_imaging import setup_lab_environment

def test_patient_activity_timeline_isolation(client, db):
    patient_id, patient_user_id, doctor_user_id, lab_user_id = setup_lab_environment(db)
    
    from app.models.user import User, PatientProfile, UserStatusEnum
    from app.core.security import hash_password
    other_user = User(
        email="other@cryptcare.ai", phone="+1000000000", password_hash=hash_password("dummy"),
        role=RoleEnum.PATIENT, full_name="Other", status=UserStatusEnum.ACTIVE
    )
    db.add(other_user)
    db.flush()
    other_patient = PatientProfile(user_id=other_user.user_id)
    db.add(other_patient)
    db.commit()

    db.add(AccessLog(user_id=doctor_user_id, patient_id=patient_id, resource_type="prescriptions", action=AccessActionEnum.READ))
    db.add(AccessLog(user_id=doctor_user_id, patient_id=other_patient.patient_id, resource_type="prescriptions", action=AccessActionEnum.READ))
    db.add(AccessLog(user_id=doctor_user_id, patient_id=None, resource_type="blood_requests", action=AccessActionEnum.WRITE))
    db.add(AccessLog(user_id=patient_user_id, patient_id=None, resource_type="login", action=AccessActionEnum.WRITE))
    db.commit()

    from app.core.rbac import CurrentUser
    cu = CurrentUser(id=patient_user_id, role="PATIENT", permissions=[])
    logs = get_patient_timeline(db, cu)
    
    assert len(logs) == 1
    assert logs[0].resource_type == "prescriptions"

