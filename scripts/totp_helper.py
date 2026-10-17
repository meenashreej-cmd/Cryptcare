"""
scripts/totp_helper.py

Utility to inspect, generate, and retrieve TOTP codes for registered CryptCare users.

Usage:
    python scripts/totp_helper.py                        # List all users and their MFA status
    python scripts/totp_helper.py <email>               # Get current TOTP code or provision MFA
    python scripts/totp_helper.py --provision-all       # Provision MFA for all staff/admin accounts
"""

import sys
import os
import time
import argparse
import pyotp

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.user import User, RoleEnum
from app.core.encryption import encrypt, decrypt
from app.core.config import settings


def get_remaining_seconds() -> int:
    return 30 - (int(time.time()) % 30)


def show_user_totp(user: User, db) -> None:
    print(f"\n========================================================")
    print(f" User: {user.full_name} ({user.email})")
    print(f" Role: {user.role.value} | Status: {user.status.value}")
    print(f"========================================================")

    secret = None
    if user.mfa_secret:
        try:
            secret = decrypt(user.mfa_secret)
        except Exception as e:
            print(f"[!] Error decrypting mfa_secret: {e}")

    if not secret:
        print("[!] No MFA secret is currently set for this account.")
        resp = input("Do you want to provision an MFA secret for this account now? (y/N): ").strip().lower()
        if resp == "y":
            secret = pyotp.random_base32()
            user.mfa_secret = encrypt(secret)
            user.mfa_enabled = True
            db.commit()
            print("[+] Successfully generated and saved MFA secret!")
        else:
            return

    totp = pyotp.TOTP(secret)
    current_code = totp.now()
    rem = get_remaining_seconds()
    uri = totp.provisioning_uri(name=user.email, issuer_name=settings.MFA_ISSUER_NAME)

    print(f"\n>> CURRENT 6-DIGIT TOTP CODE:  {current_code}  (valid for {rem}s)")
    print(f"\nAuthenticator Secret (Base32): {secret}")
    print(f"Provisioning URI:              {uri}\n")
    print("You can manually enter the secret into Google Authenticator / Authy,")
    print("or use the current 6-digit code above to log in directly.")
    print("========================================================\n")


def list_users(db) -> None:
    users = db.query(User).all()
    print(f"\n{'Email':<32} {'Role':<16} {'MFA Enabled':<13} {'Secret Provisioned':<18}")
    print("-" * 80)
    for u in users:
        has_secret = bool(u.mfa_secret)
        print(f"{u.email:<32} {u.role.value:<16} {str(u.mfa_enabled):<13} {str(has_secret):<18}")
    print("-" * 80)
    print("\nTo view the TOTP code or provision MFA for a user, run:")
    print("  python scripts/totp_helper.py <email>")
    print("  python scripts/totp_helper.py --provision-all\n")


def provision_all_staff(db) -> None:
    staff_roles = [
        RoleEnum.DOCTOR, RoleEnum.NURSE, RoleEnum.PHARMACIST,
        RoleEnum.LAB, RoleEnum.HOSPITAL_ADMIN, RoleEnum.ADMIN
    ]
    users = db.query(User).filter(User.role.in_(staff_roles)).all()
    count = 0
    print(f"\nProvisioning MFA for all staff/admin roles...")
    print("-" * 65)
    for u in users:
        if not u.mfa_secret:
            secret = pyotp.random_base32()
            u.mfa_secret = encrypt(secret)
            u.mfa_enabled = True
            count += 1
            totp = pyotp.TOTP(secret)
            print(f"[+] {u.role.value:<14} {u.email:<30} Code: {totp.now()}  Secret: {secret}")
        else:
            secret = decrypt(u.mfa_secret)
            totp = pyotp.TOTP(secret)
            print(f"[=] {u.role.value:<14} {u.email:<26} Code: {totp.now()}  Secret: {secret}")
    db.commit()
    print("-" * 65)
    print(f"Done. Provisioned {count} new accounts.\n")


def main():
    parser = argparse.ArgumentParser(description="CryptCare TOTP Helper")
    parser.add_argument("email", nargs="?", default=None, help="Email of the user to check")
    parser.add_argument("--provision-all", action="store_true", help="Provision MFA for all staff/admin roles")

    args = parser.parse_args()
    db = SessionLocal()
    try:
        if args.provision_all:
            provision_all_staff(db)
        elif args.email:
            user = db.query(User).filter(User.email == args.email.strip()).first()
            if not user:
                print(f"[!] User with email '{args.email}' not found.")
                sys.exit(1)
            show_user_totp(user, db)
        else:
            list_users(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
