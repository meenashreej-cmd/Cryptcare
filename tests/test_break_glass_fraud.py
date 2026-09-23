from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.fraud import FraudAlert, FraudAlertCategoryEnum
from app.models.user import User, UserStatusEnum, RoleEnum, PatientProfile
from unittest.mock import patch
import time

@patch("app.services.auth_service.verify_license_or_raise", return_value=None)
def test_break_glass_fraud_abuse(mock_verify, client: TestClient, db: Session):
    timestamp = str(int(time.time()))
    
    # 1. Register 3 patients
    patient_ids = []
    for i in range(3):
        email = f"patient{i}_{timestamp}@example.com"
        resp = client.post("/api/v1/auth/register", json={
            "email": email, "password": "SecurePassword123!", "role": "PATIENT", "phone": f"+199988877{i}0", "full_name": f"Patient {i}"
        }, headers={"X-Forwarded-For": f"10.0.1.{i}"})
        assert resp.status_code == 201, f"Failed to register patient: {resp.text}"
        user = db.query(User).filter(User.email == email).first()
        user.status = UserStatusEnum.ACTIVE
        db.commit()
        
        prof = db.query(PatientProfile).filter(PatientProfile.user_id == user.user_id).first()
        patient_ids.append(prof.patient_id)
        
    # 2. Register a Doctor
    doc_email = f"doc_{timestamp}@example.com"
    resp = client.post("/api/v1/auth/register", json={
        "email": doc_email, "password": "SecurePassword123!", "role": "DOCTOR", "phone": "+19998881234", "full_name": "Doctor Dan", "license_number": "MD-12345"
    }, headers={"X-Forwarded-For": "10.0.2.1"})
    assert resp.status_code == 201, f"Failed to register doctor: {resp.text}"
    doc_user = db.query(User).filter(User.email == doc_email).first()
    doc_user.status = UserStatusEnum.ACTIVE
    db.commit()
    
    # Get doc token directly to bypass MFA requirements on /login
    from app.core.security import create_access_token
    doc_token = create_access_token(doc_user.user_id, RoleEnum.DOCTOR.value, [])
    
    # 3. Register an Admin (Directly via DB to bypass self-registration restriction)
    admin_email = f"admin_{timestamp}@example.com"
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    admin_user = User(
        email=admin_email,
        password_hash=pwd_context.hash("SecurePassword123!"),
        role=RoleEnum.ADMIN,
        status=UserStatusEnum.ACTIVE,
        phone="+19998889999",
        full_name="Admin Alan",
        mfa_enabled=False
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    
    admin_token = create_access_token(admin_user.user_id, RoleEnum.ADMIN.value, [])
    
    # 4. Invoke break-glass on all 3 patients using doc_token
    for pid in patient_ids:
        req = client.post("/api/v1/consent/break-glass", json={
            "patient_id": pid, "resource_type": "prescriptions", "permission": "READ", "reason": "Emergency access required"
        }, headers={"Authorization": f"Bearer {doc_token}", "X-Forwarded-For": "10.0.0.1"})
        assert req.status_code == 201, f"Failed to break glass: {req.text}"
        
    # 5. Admin gets global queue
    admin_resp = client.get("/api/v1/fraud/alerts", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_resp.status_code == 200
    
    data = admin_resp.json()
    assert len(data["alerts"]) >= 1
    
    # Verify the fraud alert response does NOT contain patient_id or encrypted_context
    abuse_alerts = [a for a in data["alerts"] if a["category"] == FraudAlertCategoryEnum.BREAK_GLASS_ABUSE.value]
    assert len(abuse_alerts) >= 1
    
    alert = abuse_alerts[0]
    assert "patient_id" not in alert
    assert "encrypted_context" not in alert
    assert "alert_id" in alert
    assert alert["severity"] == "SEVERE"
    assert alert["counts"] == 3
