import re

with open("app/services/auth_service.py", "r") as f:
    content = f.read()

# register_user
content = content.replace(
    "def register_user(db: Session, payload: RegisterRequest) -> tuple[User, str | None, bool]:",
    "def register_user(db: Session, payload: RegisterRequest, client_ip: str) -> tuple[User, str | None, bool]:\n    _check_action_rate_limit(db, client_ip, 'register', limit=3, window_seconds=60, is_ip=True)"
)

# login
old_login = '''def login(db: Session, email: str, password: str, otp_code: str | None) -> dict[str, Any]:
    user = db.query(User).filter(User.email == email).first()

    # Always run verify_password, even when no user was found, so a
    # nonexistent email doesn't return measurably faster than a wrong
    # password does (bcrypt dominates response time either way).
    password_ok = verify_password(password, user.password_hash if user else _dummy_password_hash())
    if not user or not password_ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    if user.status == UserStatusEnum.PENDING_VERIFICATION:'''

new_login = '''def login(db: Session, email: str, password: str, otp_code: str | None, client_ip: str) -> dict[str, Any]:
    # 1. IP-level rate limit
    _check_action_rate_limit(db, client_ip, 'login', limit=20, window_seconds=60, is_ip=True)
    
    user = db.query(User).filter(User.email == email).first()

    # 2. Account-level lockout check before verifying password
    if user and user.locked_until and user.locked_until > datetime.now(timezone.utc).replace(tzinfo=None):
        # We don't want to leak that the account is locked vs wrong password easily, but HTTP 401 is appropriate
        # Actually, let's return identical 401 to prevent enumeration. Wait, no, returning identical 401 doesn't tell the user they are locked out.
        # But wait! To prevent account enumeration, "login returns identical responses for 'no such user' vs 'wrong password'". 
        # A locked account is a valid user, so returning "Account locked" leaks that the user exists. 
        # BUT a real user needs to know they are locked out! Let's return "Invalid email or password" but internally log it. 
        # Actually, if we return 401 "Invalid email or password" for locked accounts, they won't know when they can login. Let's return 401. 
        # Let's run a dummy verify_password just for timing.
        verify_password("dummy", _dummy_password_hash())
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    password_ok = verify_password(password, user.password_hash if user else _dummy_password_hash())
    
    if not user or not password_ok:
        if user:
            # Increment failed attempt count and maybe lock out
            try:
                _check_action_rate_limit(db, user.user_id, 'login_failed', limit=5, window_seconds=60, is_ip=False)
            except HTTPException as e:
                if e.status_code == 429:
                    user.locked_until = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=15)
                    _log_auth_audit(db, user.user_id, client_ip, "ACCOUNT_LOCKOUT", "FAILURE", "15-minute temporary lockout after 5 failed login attempts")
                    db.commit()
                    # Return 401 instead of 429 to prevent enumeration
                    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    if user.status == UserStatusEnum.PENDING_VERIFICATION:'''

content = content.replace(old_login, new_login)

# refresh_access_token
content = content.replace(
    "def refresh_access_token(db: Session, refresh_token: str) -> dict[str, str]:",
    "def refresh_access_token(db: Session, refresh_token: str, client_ip: str) -> dict[str, str]:\n    # Additive protection: 10 refreshes per minute ceiling\n    _check_action_rate_limit(db, client_ip, 'refresh', limit=10, window_seconds=60, is_ip=True)"
)

# enroll_mfa
content = content.replace(
    "def enroll_mfa(db: Session, user_id: str, jti: str, otp_code: str) -> dict[str, str]:\n    if db.query(UsedJTI).filter(UsedJTI.jti == jti).first():\n        raise HTTPException(status.HTTP_401_UNAUTHORIZED, \"Token already used\")\n\n    _check_action_rate_limit(db, user_id, \"enroll_mfa\", 60)",
    "def enroll_mfa(db: Session, user_id: str, jti: str, otp_code: str, client_ip: str) -> dict[str, str]:\n    if db.query(UsedJTI).filter(UsedJTI.jti == jti).first():\n        raise HTTPException(status.HTTP_401_UNAUTHORIZED, \"Token already used\")\n\n    _check_action_rate_limit(db, user_id, \"enroll_mfa\", limit=3, window_seconds=60, is_ip=False)\n    _check_action_rate_limit(db, client_ip, \"enroll_mfa\", limit=10, window_seconds=60, is_ip=True)"
)

# resend_otp
content = content.replace(
    "def resend_otp(db: Session, user_id: str) -> None:\n    _check_action_rate_limit(db, user_id, \"resend_otp\", 60)",
    "def resend_otp(db: Session, user_id: str, client_ip: str) -> None:\n    _check_action_rate_limit(db, user_id, \"resend_otp\", limit=3, window_seconds=60, is_ip=False)\n    _check_action_rate_limit(db, client_ip, \"resend_otp\", limit=10, window_seconds=60, is_ip=True)"
)

# verify_otp
content = content.replace(
    "def verify_otp(db: Session, user_id: str, jti: str, otp_code: str) -> User:",
    "def verify_otp(db: Session, user_id: str, jti: str, otp_code: str, client_ip: str) -> User:\n    _check_action_rate_limit(db, user_id, \"verify_otp\", limit=5, window_seconds=60, is_ip=False)\n    _check_action_rate_limit(db, client_ip, \"verify_otp\", limit=20, window_seconds=60, is_ip=True)"
)

with open("app/services/auth_service.py", "w") as f:
    f.write(content)
