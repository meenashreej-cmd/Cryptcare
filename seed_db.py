"""
seed_db.py — Full demo database seeding for CryptCare.

Creates 8 demo accounts (one per role) plus realistic clinical records
so every frontend view has live data to display. All passwords are
"Password123" (meets the complexity rule: upper + digit + 10 chars).

Run:
    python seed_db.py
"""

import sys
import os
from datetime import date, datetime, timedelta, timezone
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.core.security import hash_password
from app.core.encryption import encrypt

# Models
from app.models.user import (
    User, RoleEnum, UserStatusEnum,
    PatientProfile, DoctorProfile, NurseProfile,
    PharmacistProfile, InsurerProfile, BloodBankProfile, LabProfile,
)
from app.models.vault import (
    Prescription, PrescriptionItem, PrescriptionStatusEnum,
    Allergy, SeverityEnum, Vaccination, LabReport, DocumentTypeEnum,
)
from app.models.lab import LabTestRequest, LabRequestStatusEnum
from app.models.nursing import VitalSign
from app.models.consent import (
    ConsentRequest, ConsentStatusEnum, GranteeTypeEnum,
    ResourceTypeEnum, PermissionEnum,
)
from app.models.insurance import InsuranceClaim, ClaimStatusEnum
from app.models.blood_bank import (
    BloodUnit, BloodUnitStatusEnum, BloodComponentEnum,
    BloodRequest, BloodRequestStatusEnum, BloodRequestUrgencyEnum,
)
from app.models.fraud import FraudAlert, FraudAlertCategoryEnum, FraudAlertStatusEnum
from app.models.notification import Notification, NotificationTypeEnum

NOW = datetime.now(timezone.utc).replace(tzinfo=None)
PASSWORD = "Password123"  # meets: >=10 chars, 1 upper, 1 digit


def seed_db():
    print("Dropping all tables...")
    with engine.begin() as conn:
        if "sqlite" not in str(engine.url):
            conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        Base.metadata.drop_all(bind=conn)
        if "sqlite" not in str(engine.url):
            conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # ------------------------------------------------------------------ #
        # 1. USERS + PROFILES                                                 #
        # ------------------------------------------------------------------ #

        def make_user(email, phone, full_name, role, mfa=False):
            u = User(
                email=email,
                phone=phone,
                password_hash=hash_password(PASSWORD),
                role=role,
                full_name=full_name,
                status=UserStatusEnum.ACTIVE,
                mfa_enabled=mfa,
                mfa_secret="JBSWY3DPEHPK3PXP",  # demo TOTP (pyotp.random_base32() equivalent)
            )
            db.add(u)
            db.flush()
            return u

        # Patient
        patient_user = make_user(
            "patient@example.com", "+919876543210",
            "Aarav Mehta", RoleEnum.PATIENT,
        )
        patient_profile = PatientProfile(
            user_id=patient_user.user_id,
            dob=date(1991, 4, 14),
            gender="Male",
            blood_group="O+",
            emergency_contact_name="Sanya Mehta",
            emergency_contact_phone="+919000011122",
        )
        db.add(patient_profile)
        db.flush()

        # Doctor
        doctor_user = make_user(
            "doctor@example.com", "+918000055566",
            "Dr. Lena Cross", RoleEnum.DOCTOR, mfa=True,
        )
        doctor_profile = DoctorProfile(
            user_id=doctor_user.user_id,
            license_number="MCI-DOC-2024-001",
            specialization="Cardiology",
            hospital_name="City General Hospital",
            verified=True,
        )
        db.add(doctor_profile)
        db.flush()

        # Nurse
        nurse_user = make_user(
            "nurse@example.com", "+919000011122",
            "Priya Rao", RoleEnum.NURSE, mfa=True,
        )
        nurse_profile = NurseProfile(
            user_id=nurse_user.user_id,
            license_number="NMC-NURSE-2024-001",
            hospital_name="City General Hospital",
            department="Ward 4B",
            verified=True,
        )
        db.add(nurse_profile)
        db.flush()

        # Pharmacist
        pharmacist_user = make_user(
            "pharmacist@example.com", "+917000022233",
            "Imran Sheikh", RoleEnum.PHARMACIST, mfa=True,
        )
        pharmacist_profile = PharmacistProfile(
            user_id=pharmacist_user.user_id,
            license_number="PCI-PHARM-2024-001",
            pharmacy_name="Central Pharmacy",
            verified=True,
        )
        db.add(pharmacist_profile)
        db.flush()

        # Lab technician
        lab_user = make_user(
            "lab@example.com", "+916000033344",
            "Apollo Diagnostics Lab", RoleEnum.LAB,
        )
        lab_profile = LabProfile(
            user_id=lab_user.user_id,
            license_number="NABL-LAB-2024-001",
            lab_name="Apollo Diagnostics",
            verified=True,
        )
        db.add(lab_profile)
        db.flush()

        # Insurer
        insurer_user = make_user(
            "insurer@example.com", "+915000044455",
            "Northwind Health", RoleEnum.INSURER,
        )
        insurer_profile = InsurerProfile(
            user_id=insurer_user.user_id,
            license_number="IRDAI-INS-2024-001",
            company_name="Northwind Health Insurance",
            verified=True,
        )
        db.add(insurer_profile)
        db.flush()

        # Blood bank
        blood_bank_user = make_user(
            "bloodbank@example.com", "+914000055566",
            "City Blood Bank", RoleEnum.BLOOD_BANK,
        )
        blood_bank_profile = BloodBankProfile(
            user_id=blood_bank_user.user_id,
            license_number="NBTC-BB-2024-001",
            facility_name="City Blood Bank",
            verified=True,
        )
        db.add(blood_bank_profile)
        db.flush()

        # Admin
        admin_user = make_user(
            "admin@example.com", "+919999999999",
            "K. Okafor", RoleEnum.ADMIN,
        )
        db.flush()

        print("Users + profiles created.")

        # ------------------------------------------------------------------ #
        # 2. CONSENTS — doctor & nurse get ACTIVE access to patient records   #
        # ------------------------------------------------------------------ #

        pid = patient_profile.patient_id  # shorthand

        def active_consent(grantee_id, grantee_type, resource_type, permission=PermissionEnum.BOTH):
            c = ConsentRequest(
                patient_id=pid,
                grantee_id=grantee_id,
                grantee_type=grantee_type,
                resource_type=resource_type,
                permission=permission,
                status=ConsentStatusEnum.ACTIVE,
                expires_at=NOW + timedelta(days=30),
            )
            db.add(c)

        # Doctor has access to prescriptions, allergies, vaccinations, lab reports, lab requests
        for rt in [
            ResourceTypeEnum.PRESCRIPTIONS,
            ResourceTypeEnum.ALLERGIES,
            ResourceTypeEnum.VACCINATIONS,
            ResourceTypeEnum.LAB_REPORTS,
            ResourceTypeEnum.LAB_REQUESTS,
        ]:
            active_consent(doctor_user.user_id, GranteeTypeEnum.DOCTOR, rt)

        # Nurse has access to vitals + prescriptions (read-only for administration)
        active_consent(nurse_user.user_id, GranteeTypeEnum.NURSE, ResourceTypeEnum.VITALS)
        active_consent(nurse_user.user_id, GranteeTypeEnum.NURSE, ResourceTypeEnum.PRESCRIPTIONS, PermissionEnum.READ)

        # Insurer has access to fraud alerts for this patient
        active_consent(insurer_user.user_id, GranteeTypeEnum.INSURER, ResourceTypeEnum.FRAUD_ALERTS, PermissionEnum.READ)

        db.flush()
        print("Consents created.")

        # ------------------------------------------------------------------ #
        # 3. ALLERGIES                                                        #
        # ------------------------------------------------------------------ #

        allergies = [
            Allergy(patient_id=pid, allergen="Penicillin", severity=SeverityEnum.SEVERE),
            Allergy(patient_id=pid, allergen="Peanuts",    severity=SeverityEnum.MODERATE),
            Allergy(patient_id=pid, allergen="Latex",      severity=SeverityEnum.MILD),
        ]
        for a in allergies:
            db.add(a)
        db.flush()
        print("Allergies created.")

        # ------------------------------------------------------------------ #
        # 4. VACCINATIONS                                                     #
        # ------------------------------------------------------------------ #

        vaccinations = [
            Vaccination(patient_id=pid, vaccine_name="COVID-19 (Covishield)",
                        date_administered=datetime(2021, 6, 10),
                        next_due_date=None),
            Vaccination(patient_id=pid, vaccine_name="Influenza (Annual)",
                        date_administered=datetime(2025, 10, 5),
                        next_due_date=datetime(2026, 10, 5)),
            Vaccination(patient_id=pid, vaccine_name="Hepatitis B",
                        date_administered=datetime(2015, 3, 1),
                        next_due_date=None),
        ]
        for v in vaccinations:
            db.add(v)
        db.flush()
        print("Vaccinations created.")

        # ------------------------------------------------------------------ #
        # 5. PRESCRIPTIONS                                                    #
        # ------------------------------------------------------------------ #

        def make_prescription(status, items_data, days_ago=0):
            rx = Prescription(
                patient_id=pid,
                doctor_id=doctor_profile.doctor_id,
                diagnosis_encrypted=encrypt("Hyperlipidemia — routine management"),
                notes_encrypted=encrypt("Take with food. Monitor LFTs quarterly."),
                digital_signature="DEMO_SIG_" + str(days_ago),
                status=status,
                created_at=NOW - timedelta(days=days_ago),
            )
            db.add(rx)
            db.flush()
            for name, dosage, freq, dur in items_data:
                db.add(PrescriptionItem(
                    prescription_id=rx.prescription_id,
                    medicine_name=name,
                    dosage=dosage,
                    frequency=freq,
                    duration_days=dur,
                ))
            db.flush()
            return rx

        rx1 = make_prescription(
            PrescriptionStatusEnum.ACTIVE,
            [("Atorvastatin", "20mg", "Once daily at night", 90),
             ("Aspirin", "75mg", "Once daily with breakfast", 90)],
            days_ago=2,
        )
        rx2 = make_prescription(
            PrescriptionStatusEnum.ACTIVE,
            [("Metformin", "500mg", "Twice daily with meals", 60)],
            days_ago=12,
        )
        rx3 = make_prescription(
            PrescriptionStatusEnum.DISPENSED,
            [("Amoxicillin", "500mg", "Three times daily", 7)],
            days_ago=65,
        )
        rx4 = make_prescription(
            PrescriptionStatusEnum.EXPIRED,
            [("Ibuprofen", "400mg", "As needed (max 3/day)", 5)],
            days_ago=120,
        )
        print("Prescriptions created.")

        # ------------------------------------------------------------------ #
        # 6. LAB REQUESTS + REPORTS                                           #
        # ------------------------------------------------------------------ #

        def make_lab_request(test_name, status, days_ago):
            req = LabTestRequest(
                patient_id=pid,
                doctor_id=doctor_profile.doctor_id,
                test_name=test_name,
                status=status,
                assigned_lab_user_id=lab_user.user_id,
                requested_at=NOW - timedelta(days=days_ago),
            )
            db.add(req)
            db.flush()
            return req

        lab_req1 = make_lab_request("Lipid Panel",            LabRequestStatusEnum.COMPLETED, 3)
        lab_req2 = make_lab_request("HbA1c",                  LabRequestStatusEnum.COMPLETED, 3)
        lab_req3 = make_lab_request("Complete Blood Count",   LabRequestStatusEnum.COMPLETED, 49)
        lab_req4 = make_lab_request("Cardiac MRI",            LabRequestStatusEnum.COMPLETED, 155)
        lab_req5 = make_lab_request("Liver Function Tests",   LabRequestStatusEnum.IN_PROGRESS, 1)

        def make_lab_report(lab_req, summary, doc_type=DocumentTypeEnum.LAB_SUMMARY, days_ago=3):
            rpt = LabReport(
                patient_id=pid,
                lab_test_request_id=lab_req.request_id,
                document_type=doc_type,
                original_filename_encrypted=encrypt(f"{lab_req.test_name.replace(' ', '_')}_Report.pdf"),
                file_size_bytes=220000,
                file_path_encrypted=encrypt(f"/reports/{lab_req.request_id}.pdf"),
                report_summary_encrypted=encrypt(summary),
                uploaded_by=lab_user.user_id,
                uploaded_at=NOW - timedelta(days=days_ago),
            )
            db.add(rpt)
            db.flush()
            return rpt

        make_lab_report(lab_req1, "LDL: 142 mg/dL (Borderline High). HDL: 48 mg/dL. Triglycerides: 180 mg/dL. Recommend dietary changes and statin continuation.")
        make_lab_report(lab_req2, "HbA1c: 6.4% — Pre-diabetic range. Recommend lifestyle modification and Metformin continuation. Recheck in 3 months.")
        make_lab_report(lab_req3, "WBC: 7.2 K/uL (Normal). RBC: 4.8 M/uL (Normal). Hgb: 14.1 g/dL. Platelets: 220 K/uL. All within normal range.", days_ago=49)
        make_lab_report(lab_req4, "No structural cardiac abnormality detected. LVEF: 62%. No valvular disease.", DocumentTypeEnum.MRI, days_ago=155)

        print("Lab requests + reports created.")

        # ------------------------------------------------------------------ #
        # 7. VITAL SIGNS                                                      #
        # ------------------------------------------------------------------ #

        vitals_data = [
            (72, 120, 80, 37.0, 98,  98, "Patient resting comfortably post-consultation.",  2),
            (76, 122, 82, 37.2, 16,  97, "Mild exertion noted. Routine pre-procedure check.", 5),
            (80, 130, 85, 37.5, 18,  96, "Patient reports mild chest discomfort. Doctor notified.", 10),
            (70, 118, 78, 36.9, 15,  99, "Post-medication vitals. Stable.",                 15),
            (74, 124, 80, 37.1, 16,  98, "Routine admission check.",                        20),
        ]
        for hr, sys, dia, temp, rr, spo2, notes, days_ago in vitals_data:
            db.add(VitalSign(
                patient_id=pid,
                recorded_by=nurse_user.user_id,
                heart_rate_bpm=hr,
                blood_pressure_systolic=sys,
                blood_pressure_diastolic=dia,
                temperature_celsius=temp,
                respiratory_rate=rr,
                spo2_percent=spo2,
                notes_encrypted=encrypt(notes),
                recorded_at=NOW - timedelta(days=days_ago),
            ))
        db.flush()
        print("Vital signs created.")

        # ------------------------------------------------------------------ #
        # 8. BLOOD BANK UNITS                                                 #
        # ------------------------------------------------------------------ #

        blood_units = [
            ("O+",  BloodComponentEnum.PACKED_RBC,   date(2026, 6, 1),  date(2026, 9, 1)),
            ("O+",  BloodComponentEnum.PACKED_RBC,   date(2026, 7, 1),  date(2026, 10, 1)),
            ("O+",  BloodComponentEnum.PLASMA,        date(2026, 5, 15), date(2026, 11, 15)),
            ("O-",  BloodComponentEnum.PACKED_RBC,   date(2026, 7, 10), date(2026, 10, 10)),
            ("A+",  BloodComponentEnum.WHOLE_BLOOD,   date(2026, 6, 20), date(2026, 9, 20)),
            ("A+",  BloodComponentEnum.PLATELETS,     date(2026, 8, 1),  date(2026, 8, 6)),
            ("B+",  BloodComponentEnum.PACKED_RBC,   date(2026, 7, 5),  date(2026, 10, 5)),
            ("AB+", BloodComponentEnum.PLASMA,        date(2026, 6, 10), date(2026, 12, 10)),
            ("AB-", BloodComponentEnum.PACKED_RBC,   date(2026, 7, 20), date(2026, 10, 20)),
            ("B-",  BloodComponentEnum.PLATELETS,     date(2026, 8, 2),  date(2026, 8, 7)),
        ]
        for grp, comp, col, exp in blood_units:
            db.add(BloodUnit(
                blood_bank_id=blood_bank_profile.blood_bank_id,
                blood_group=grp,
                component=comp,
                collection_date=col,
                expiry_date=exp,
                status=BloodUnitStatusEnum.AVAILABLE,
            ))
        db.flush()
        print("Blood units created.")

        # ------------------------------------------------------------------ #
        # 9. BLOOD REQUEST                                                    #
        # ------------------------------------------------------------------ #

        blood_req = BloodRequest(
            patient_id=pid,
            requested_by=doctor_user.user_id,
            blood_group="O+",
            component=BloodComponentEnum.PACKED_RBC,
            units_needed=2,
            urgency=BloodRequestUrgencyEnum.URGENT,
            status=BloodRequestStatusEnum.PENDING,
        )
        db.add(blood_req)
        db.flush()
        print("Blood request created.")

        # ------------------------------------------------------------------ #
        # 10. INSURANCE CLAIMS                                                #
        # ------------------------------------------------------------------ #

        claims_data = [
            (rx1.prescription_id, "prescriptions", ClaimStatusEnum.PENDING,  4200.0),
            (rx3.prescription_id, "prescriptions", ClaimStatusEnum.APPROVED, 850.0),
            (rx4.prescription_id, "prescriptions", ClaimStatusEnum.REJECTED, 600.0),
        ]
        for res_id, res_type, status, amount in claims_data:
            db.add(InsuranceClaim(
                patient_id=pid,
                insurer_id=insurer_profile.insurer_id,
                resource_type=res_type,
                resource_id=res_id,
                status=status,
                amount=amount,
            ))
        db.flush()
        print("Insurance claims created.")

        # ------------------------------------------------------------------ #
        # 11. FRAUD ALERTS                                                    #
        # ------------------------------------------------------------------ #

        fraud_alerts = [
            FraudAlert(
                patient_id=pid,
                category=FraudAlertCategoryEnum.DOCTOR_SHOPPING,
                severity=SeverityEnum.SEVERE,
                status=FraudAlertStatusEnum.OPEN,
                description="Patient obtained prescriptions for Metformin from 2 distinct doctors within a 30-day window.",
                related_resource_ids=f"{rx1.prescription_id},{rx2.prescription_id}",
                detected_at=NOW - timedelta(hours=3),
            ),
            FraudAlert(
                patient_id=pid,
                category=FraudAlertCategoryEnum.PRESCRIPTION_TAMPERING,
                severity=SeverityEnum.MODERATE,
                status=FraudAlertStatusEnum.REVIEWED,
                description="2 signature-verification failures detected against prescription RX. Possible QR tampering attempt.",
                related_resource_ids=rx3.prescription_id,
                detected_at=NOW - timedelta(days=1),
            ),
        ]
        for fa in fraud_alerts:
            db.add(fa)
        db.flush()
        print("Fraud alerts created.")

        # ------------------------------------------------------------------ #
        # 12. NOTIFICATIONS                                                   #
        # ------------------------------------------------------------------ #

        notifications = [
            Notification(
                recipient_id=patient_user.user_id,
                type=NotificationTypeEnum.CONSENT_REQUEST,
                resource_type="consents",
                message="Dr. Lena Cross has requested access to your Prescriptions.",
                is_read=False,
                created_at=NOW - timedelta(hours=2),
            ),
            Notification(
                recipient_id=patient_user.user_id,
                type=NotificationTypeEnum.LAB_RESULT,
                resource_type="lab_reports",
                message="Your Lipid Panel report is ready for review.",
                is_read=False,
                created_at=NOW - timedelta(hours=5),
            ),
            Notification(
                recipient_id=patient_user.user_id,
                type=NotificationTypeEnum.PRESCRIPTION,
                resource_type="prescriptions",
                message="New prescription issued by Dr. Lena Cross.",
                is_read=True,
                created_at=NOW - timedelta(days=2),
            ),
            Notification(
                recipient_id=patient_user.user_id,
                type=NotificationTypeEnum.INSURANCE_UPDATE,
                resource_type="insurance_claims",
                message="Your insurance claim status has been updated to APPROVED.",
                is_read=True,
                created_at=NOW - timedelta(days=3),
            ),
        ]
        for n in notifications:
            db.add(n)
        db.flush()
        print("Notifications created.")

        db.commit()
        print("\n=== Database seeded successfully ===")
        print("\nDemo accounts (password for all: Password123)")
        print("  patient@example.com      — Patient     (Aarav Mehta)")
        print("  doctor@example.com       — Doctor      (Dr. Lena Cross)    [MFA enabled]")
        print("  nurse@example.com        — Nurse       (Priya Rao)         [MFA enabled]")
        print("  pharmacist@example.com   — Pharmacist  (Imran Sheikh)      [MFA enabled]")
        print("  lab@example.com          — Lab         (Apollo Diagnostics)")
        print("  insurer@example.com      — Insurer     (Northwind Health)")
        print("  bloodbank@example.com    — Blood Bank  (City Blood Bank)")
        print("  admin@example.com        — Admin       (K. Okafor)")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\nError seeding database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_db()
