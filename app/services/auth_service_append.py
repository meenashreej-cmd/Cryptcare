
def logout(db: Session, refresh_token: str) -> None:
    try:
        payload = verify_refresh_token(refresh_token)
    except TokenError:
        return  # If token is invalid or expired, nothing to revoke
        
    db.query(RefreshToken).filter(RefreshToken.jti == payload["jti"]).update({"revoked": True})
    db.commit()


def logout_all(db: Session, user_id: str) -> None:
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked == False
    ).update({"revoked": True})
    db.commit()


def change_password(db: Session, user_id: str, new_password: str) -> None:
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
        
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    db.commit()
    logout_all(db, user_id)


# Simple rate limit for resend_otp: map of user_id to last resend time
_RESEND_OTP_RATE_LIMIT: dict[str, datetime] = {}

def resend_otp(db: Session, user_id: str) -> None:
    now = datetime.now(timezone.utc)
    last_resend = _RESEND_OTP_RATE_LIMIT.get(user_id)
    
    if last_resend and (now - last_resend) < timedelta(seconds=60):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Please wait 60 seconds before requesting a new OTP")
        
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user or user.status != UserStatusEnum.PENDING_VERIFICATION:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User is not in pending verification state")
        
    # Invalidate prior OTP by overwriting it
    _RESEND_OTP_RATE_LIMIT[user_id] = now
    _send_otp(user)

