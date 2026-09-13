from fastapi import APIRouter

from app.api.v1.endpoints import auth, consent, fraud, lab, notifications, nursing, vault, pharmacy, emergency, blood_bank, insurance, audit, admin, ai

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(vault.router)
api_router.include_router(lab.router)
api_router.include_router(consent.router)
api_router.include_router(notifications.router)
api_router.include_router(pharmacy.router, prefix="/pharmacy", tags=["pharmacy"])
api_router.include_router(nursing.router)
api_router.include_router(fraud.router)
api_router.include_router(emergency.router)
api_router.include_router(blood_bank.router)
api_router.include_router(insurance.router)
api_router.include_router(audit.router)
api_router.include_router(admin.router)
api_router.include_router(ai.router)

# All 13 Phases are now built!
