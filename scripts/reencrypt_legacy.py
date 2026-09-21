import sys
import os

# Add the parent directory to sys.path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.vault import Prescription, LabReport
from app.models.nursing import VitalSign
from app.core.encryption import encrypt, decrypt
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reencrypt_all():
    db: Session = SessionLocal()
    try:
        # 1. Prescriptions
        logger.info("Migrating Prescriptions...")
        prescriptions = db.query(Prescription).all()
        for p in prescriptions:
            needs_update = False
            
            if p.diagnosis_encrypted and not p.diagnosis_encrypted.startswith("v2:"):
                # Decrypt without AAD
                plaintext = decrypt(p.diagnosis_encrypted, aad=None)
                aad = f"cryptcare:v2|prescriptions|{p.prescription_id}|diagnosis_encrypted|{p.patient_id}"
                p.diagnosis_encrypted = encrypt(plaintext, aad=aad)
                needs_update = True
                
            if p.notes_encrypted and not p.notes_encrypted.startswith("v2:"):
                plaintext = decrypt(p.notes_encrypted, aad=None)
                aad = f"cryptcare:v2|prescriptions|{p.prescription_id}|notes_encrypted|{p.patient_id}"
                p.notes_encrypted = encrypt(plaintext, aad=aad)
                needs_update = True
                
            if needs_update:
                db.add(p)
                
        # 2. Lab Reports
        logger.info("Migrating Lab Reports...")
        reports = db.query(LabReport).all()
        for r in reports:
            needs_update = False
            
            if r.original_filename_encrypted and not r.original_filename_encrypted.startswith("v2:"):
                plaintext = decrypt(r.original_filename_encrypted, aad=None)
                aad = f"cryptcare:v2|lab_reports|{r.report_id}|original_filename_encrypted|{r.patient_id}"
                r.original_filename_encrypted = encrypt(plaintext, aad=aad)
                needs_update = True
                
            if r.file_path_encrypted and not r.file_path_encrypted.startswith("v2:"):
                plaintext = decrypt(r.file_path_encrypted, aad=None)
                aad = f"cryptcare:v2|lab_reports|{r.report_id}|file_path_encrypted|{r.patient_id}"
                r.file_path_encrypted = encrypt(plaintext, aad=aad)
                needs_update = True
                
            if r.report_summary_encrypted and not r.report_summary_encrypted.startswith("v2:"):
                plaintext = decrypt(r.report_summary_encrypted, aad=None)
                aad = f"cryptcare:v2|lab_reports|{r.report_id}|report_summary_encrypted|{r.patient_id}"
                r.report_summary_encrypted = encrypt(plaintext, aad=aad)
                needs_update = True
                
            if needs_update:
                db.add(r)
                
        # 3. Vital Signs
        logger.info("Migrating Vital Signs...")
        vitals = db.query(VitalSign).all()
        for v in vitals:
            needs_update = False
            
            if v.notes_encrypted and not v.notes_encrypted.startswith("v2:"):
                plaintext = decrypt(v.notes_encrypted, aad=None)
                aad = f"cryptcare:v2|vital_signs|{v.vital_id}|notes_encrypted|{v.patient_id}"
                v.notes_encrypted = encrypt(plaintext, aad=aad)
                needs_update = True
                
            if needs_update:
                db.add(v)
                
        db.commit()
        logger.info("Migration completed successfully.")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    reencrypt_all()
