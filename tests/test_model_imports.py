def test_all_models_registered():
    from app.main import Base
    expected_tables = {
        'users', 'patient_profiles', 'doctor_profiles', 'lab_profiles',
        'nurse_profiles', 'pharmacist_profiles', 'insurer_profiles',
        'blood_bank_profiles', 'hospital_admin_profiles', 'access_logs',
        'consent_requests', 'notifications', 'prescriptions', 'prescription_items',
        'allergies', 'vaccinations', 'lab_reports', 'dispense_records',
        'fraud_alerts', 'lab_test_requests', 'vital_signs',
        'emergency_access_tokens', 'blood_units', 'blood_requests', 'insurance_claims',
        'broadcast_cooldowns', 'action_rate_limits', 'ip_rate_limits',
        'used_jtis', 'mfa_states', 'refresh_tokens'
    }
    registered_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(registered_tables), f"Missing tables: {expected_tables - registered_tables}"
    assert expected_tables == registered_tables, f"Extra tables: {registered_tables - expected_tables}"
