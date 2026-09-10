from datetime import datetime
from pydantic import BaseModel

from app.models.user import RoleEnum, UserStatusEnum


class PendingVerificationResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    role: RoleEnum
    status: UserStatusEnum
    created_at: datetime
    # We deliberately do not include any profile-specific fields here (e.g., license numbers, 
    # hospital names, or especially encrypted fields) to prevent accidental data leakage.
    # An admin uses this endpoint to identify WHO needs verification, then can use
    # specific profile-retrieval endpoints if they need to see the license details.

    class Config:
        from_attributes = True
