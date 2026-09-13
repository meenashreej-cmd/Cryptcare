from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.rbac import CurrentUser, require_role
from app.db.session import get_db
from app.models.user import User, DoctorProfile, NurseProfile, PatientProfile, InsurerProfile, BloodBankProfile, HospitalAdminProfile, RoleEnum

router = APIRouter(prefix="/hospital", tags=["Hospital Admin"])

@router.get("/staff")
def get_hospital_staff(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("HOSPITAL_ADMIN")),
):
    admin_profile = db.query(HospitalAdminProfile).filter(HospitalAdminProfile.user_id == current_user.id).first()
    if not admin_profile:
        return []
        
    hospital_name = admin_profile.hospital_name
    
    # Get doctors
    doctors = db.query(User, DoctorProfile).join(DoctorProfile).filter(DoctorProfile.hospital_name == hospital_name).all()
    # Get nurses
    nurses = db.query(User, NurseProfile).join(NurseProfile).filter(NurseProfile.hospital_name == hospital_name).all()
    
    results = []
    for u, p in doctors:
        results.append({
            "user_id": u.user_id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "specialization": p.specialization,
            "license_number": p.license_number,
            "verified": p.verified
        })
    for u, p in nurses:
        results.append({
            "user_id": u.user_id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "department": p.department,
            "license_number": p.license_number,
            "verified": p.verified
        })
    return results

@router.get("/network")
def get_hospital_network(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("HOSPITAL_ADMIN")),
):
    # Insurers and BloodBanks are platform-wide, so the hospital admin can view them
    insurers = db.query(User, InsurerProfile).join(InsurerProfile).all()
    blood_banks = db.query(User, BloodBankProfile).join(BloodBankProfile).all()
    
    results = []
    for u, p in insurers:
        results.append({
            "user_id": u.user_id,
            "type": "Insurer",
            "name": p.company_name,
            "email": u.email
        })
    for u, p in blood_banks:
        results.append({
            "user_id": u.user_id,
            "type": "Blood Bank",
            "name": p.facility_name,
            "email": u.email
        })
    return results
