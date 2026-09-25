import re

with open("app/services/auth_service.py", "r") as f:
    content = f.read()

content = content.replace("from app.models.audit import AuditLog", "from app.models.audit import AccessLog, AccessActionEnum")

old_log = '''def _log_auth_audit(db: Session, user_id: str, ip_address: str, event_name: str, status_msg: str, details: str):
    db.add(AuditLog(
        user_id=user_id,
        actor_id=user_id,
        action=event_name,
        target_resource="auth",
        status=status_msg,
        details=details,
        ip_address=ip_address
    ))
    db.commit()'''

new_log = '''def _log_auth_audit(db: Session, user_id: str, ip_address: str, attempt_count: int):
    db.add(AccessLog(
        user_id=user_id,
        resource_type=f"auth_lockout:attempts={attempt_count}",
        action=AccessActionEnum.DENIED,
        ip_address=ip_address
    ))
    db.commit()'''

content = content.replace(old_log, new_log)

content = content.replace(
    "_log_auth_audit(db, user.user_id, client_ip, \"ACCOUNT_LOCKOUT\", \"FAILURE\", \"15-minute temporary lockout after 5 failed login attempts\")",
    "_log_auth_audit(db, user.user_id, client_ip, 5)"
)

with open("app/services/auth_service.py", "w") as f:
    f.write(content)
