import re

with open("app/services/auth_service.py", "r") as f:
    content = f.read()

# 1. Imports
if "IpRateLimit" not in content:
    content = content.replace(
        "from app.models.auth import RefreshToken, UsedJTI, MfaState, ActionRateLimit",
        "from app.models.auth import RefreshToken, UsedJTI, MfaState, ActionRateLimit, IpRateLimit\nfrom app.models.audit import AuditLog"
    )

# 2. _check_action_rate_limit
old_check = '''def _check_action_rate_limit(db: Session, user_id: str, action: str, window_seconds: int) -> None:
    now = datetime.now(timezone.utc)
    record = db.query(ActionRateLimit).filter(
        ActionRateLimit.user_id == user_id, 
        ActionRateLimit.action == action
    ).first()
    
    if record and (now.replace(tzinfo=None) - record.last_attempt_at) < timedelta(seconds=window_seconds):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"Please wait {window_seconds} seconds before requesting this action")
        
    if not record:
        record = ActionRateLimit(user_id=user_id, action=action, last_attempt_at=now.replace(tzinfo=None))
        db.add(record)
    else:
        record.last_attempt_at = now.replace(tzinfo=None)
    db.commit()'''

new_check = '''def _check_action_rate_limit(db: Session, target_id: str, action: str, limit: int, window_seconds: int, is_ip: bool = False) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now - timedelta(seconds=window_seconds)
    
    model = IpRateLimit if is_ip else ActionRateLimit
    filter_col = model.ip_address if is_ip else model.user_id
    
    record = db.query(model).filter(filter_col == target_id, model.action == action).first()
    
    if not record:
        kwargs = {"action": action, "last_attempt_at": now, "attempt_count": 1, "window_start": now}
        if is_ip:
            kwargs["ip_address"] = target_id
        else:
            kwargs["user_id"] = target_id
        new_record = model(**kwargs)
        db.add(new_record)
        try:
            db.commit()
            return
        except Exception:
            db.rollback()

    # If already exceeded AND window hasn't expired yet, reject
    if record and record.attempt_count >= limit and record.window_start > cutoff:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests. Please try again later.")

    # Try incrementing if window is valid
    updated = db.query(model).filter(
        filter_col == target_id,
        model.action == action,
        model.window_start > cutoff,
        model.attempt_count < limit
    ).update({
        "attempt_count": model.attempt_count + 1,
        "last_attempt_at": now
    }, synchronize_session=False)

    if updated == 0:
        # Try to reset the window if it's expired.
        reset = db.query(model).filter(
            filter_col == target_id,
            model.action == action,
            model.window_start <= cutoff
        ).update({
            "attempt_count": 1,
            "window_start": now,
            "last_attempt_at": now
        }, synchronize_session=False)
        
        if reset == 0:
            db.commit()
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests. Please try again later.")
            
    db.commit()

def _log_auth_audit(db: Session, user_id: str, ip_address: str, event_name: str, status_msg: str, details: str):
    db.add(AuditLog(
        user_id=user_id,
        actor_id=user_id,
        action=event_name,
        target_resource="auth",
        status=status_msg,
        details=details,
        ip_address=ip_address
    ))
    db.commit()
'''

if old_check in content:
    content = content.replace(old_check, new_check)


with open("app/services/auth_service.py", "w") as f:
    f.write(content)
