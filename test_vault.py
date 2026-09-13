import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.user import User, RoleEnum
from app.core.rbac import CurrentUser
from app.services.access_control import is_owner, _resolve_user_id_for_patient

db = SessionLocal()

# Find the patient user
patient = db.query(User).filter(User.role == RoleEnum.PATIENT).first()
if not patient:
    print("No patient found!")
    sys.exit(1)

current_user = CurrentUser(id=patient.user_id, role="PATIENT")

print(f"Patient user ID: {patient.user_id}")

# Test if is_owner works when we pass user_id instead of patient_id
result = is_owner(current_user, patient.user_id, db)
print(f"is_owner(current_user, user_id): {result}")

resolved = _resolve_user_id_for_patient(db, patient.user_id)
print(f"_resolve_user_id_for_patient(user_id): {resolved}")
