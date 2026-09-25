import os
import re

def search_files(paths, patterns):
    results = []
    for path in paths:
        if not os.path.exists(path): continue
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            for pattern in patterns:
                if re.search(pattern, line):
                    results.append(f"{path}:{i+1}: {line.strip()}")
    return results

print("=== 1. CORS ===")
print('\n'.join(search_files(['app/main.py', 'app/core/config.py'], [r'allow_origins', r'CORS'])))
print("=== 2. AAD binding ===")
print('\n'.join(search_files(['app/models/patient.py', 'app/services/clinical_safety_service.py', 'app/models/lab.py'], [r'aad=', r'encrypt\(', r'decrypt\('])))
print("=== 3. Nurse delegation ===")
print('\n'.join(search_files(['app/services/nursing_service.py', 'app/api/v1/endpoints/nursing.py'], [r'def assign_nurse', r'pending consent', r'PENDING', r'status'])))
print("=== 5. Lab queue ===")
print('\n'.join(search_files(['app/api/v1/endpoints/lab.py', 'app/services/lab_service.py'], [r'def get_requests', r'def get_queue', r'filter', r'consent'])))
print("=== 6. Blood bank broadcast ===")
print('\n'.join(search_files(['app/services/blood_bank_service.py'], [r'def broadcast', r'atomic', r'cooldown', r'compare_and_set'])))
print("=== 7. Registration ===")
print('\n'.join(search_files(['app/services/auth_service.py'], [r'def register', r'PENDING_VERIFICATION', r'ADMIN'])))
print("=== 8. get_current_user ===")
print('\n'.join(search_files(['app/services/auth_service.py', 'app/api/deps.py'], [r'def get_current_user', r'is_active', r'db.query'])))
print("=== 9. Lab BOLA ===")
print('\n'.join(search_files(['app/services/lab_service.py'], [r'def start_processing', r'def upload_report', r'assigned_to'])))
print("=== 10. Fraud alerts ===")
print('\n'.join(search_files(['app/services/fraud_service.py', 'app/api/v1/endpoints/fraud.py'], [r'def get_alerts', r'patient_id', r'role'])))
print("=== 11. seed_db.py ===")
print('\n'.join(search_files(['seed_db.py', 'scripts/seed_db.py'], [r'password', r'force_password_change'])))
print("=== 12. Refresh tokens ===")
print('\n'.join(search_files(['app/services/auth_service.py'], [r'refresh', r'jti', r'revoke'])))
print("=== 13. Cookies & CSRF ===")
print('\n'.join(search_files(['app/api/v1/endpoints/auth.py', 'app/main.py'], [r'set_cookie', r'httponly', r'csrf'])))
print("=== 14. logout, etc ===")
print('\n'.join(search_files(['app/api/v1/endpoints/auth.py', 'app/services/auth_service.py'], [r'def logout', r'def change_password', r'def resend_otp'])))
print("=== 15. Preauth tokens ===")
print('\n'.join(search_files(['app/services/auth_service.py', 'app/core/security.py'], [r'preauth', r'purpose'])))
print("=== 16. MFA required ===")
print('\n'.join(search_files(['app/services/auth_service.py', 'app/core/config.py'], [r'MFA', r'enrollment'])))
print("=== 17. TOTP enrollment ===")
print('\n'.join(search_files(['app/services/auth_service.py', 'app/api/v1/endpoints/auth.py'], [r'verify_totp', r'enroll_mfa'])))
print("=== 18. TOTP replay ===")
print('\n'.join(search_files(['app/services/auth_service.py'], [r'last_step', r'totp'])))
print("=== 19. Rate limits ===")
print('\n'.join(search_files(['app/core/rate_limit.py', 'app/services/auth_service.py'], [r'RateLimit', r'limit'])))
print("=== 20. Lockout ===")
print('\n'.join(search_files(['app/services/auth_service.py'], [r'lockout', r'failed_attempts'])))
print("=== 22. Deny-by-default ===")
print('\n'.join(search_files(['app/core/auth_registry.py', 'tests/test_deny_by_default.py', 'app/main.py'], [r'walk', r'registry', r'deny_by_default'])))
print("=== 24. Nursing assign/remove ===")
print('\n'.join(search_files(['app/services/nursing_service.py'], [r'def remove_nurse', r'def assign_nurse', r'notification', r'audit'])))
print("=== 25. IDOR matrix ===")
print('\n'.join(search_files(['tests/test_idor_matrix.py', 'tests/test_idor_matrix_full.py'], [r'def test_'])))

