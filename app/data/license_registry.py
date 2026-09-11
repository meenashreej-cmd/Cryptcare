"""
License Registry — Phase 1 Professional Verification Dataset.

This module provides a curated dataset of valid license numbers for each
professional role. During registration, the submitted license_number is
matched against this registry. If found, the professional profile is
automatically marked verified=True without requiring any admin action.

Dataset size: ~45 entries per role (270 total across 6 roles).

Naming conventions used:
  - DOCTOR:      MD-XXXXX  (Medical Doctor)
  - NURSE:       RN-XXXXX  (Registered Nurse)
  - LAB:         LT-XXXXX  (Lab Technician / facility)
  - PHARMACIST:  PH-XXXXX  (Pharmacist)
  - INSURER:     INS-XXXXX (Insurance company)
  - BLOOD_BANK:  BB-XXXXX  (Blood Bank facility)

In a production system this dataset would be fetched from an authoritative
licensing authority API (e.g. the national medical council registry). The
static dict here is the phase-1 stand-in until that integration is built.
"""

from app.models.user import RoleEnum

# ---------------------------------------------------------------------------
# Individual role registries
# ---------------------------------------------------------------------------

_DOCTOR_LICENSES: set[str] = {
    "MD-10001", "MD-10002", "MD-10003", "MD-10004", "MD-10005",
    "MD-10006", "MD-10007", "MD-10008", "MD-10009", "MD-10010",
    "MD-10011", "MD-10012", "MD-10013", "MD-10014", "MD-10015",
    "MD-10016", "MD-10017", "MD-10018", "MD-10019", "MD-10020",
    "MD-10021", "MD-10022", "MD-10023", "MD-10024", "MD-10025",
    "MD-10026", "MD-10027", "MD-10028", "MD-10029", "MD-10030",
    "MD-10031", "MD-10032", "MD-10033", "MD-10034", "MD-10035",
    "MD-10036", "MD-10037", "MD-10038", "MD-10039", "MD-10040",
    "MD-10041", "MD-10042", "MD-10043", "MD-10044", "MD-10045",
}

_NURSE_LICENSES: set[str] = {
    "RN-20001", "RN-20002", "RN-20003", "RN-20004", "RN-20005",
    "RN-20006", "RN-20007", "RN-20008", "RN-20009", "RN-20010",
    "RN-20011", "RN-20012", "RN-20013", "RN-20014", "RN-20015",
    "RN-20016", "RN-20017", "RN-20018", "RN-20019", "RN-20020",
    "RN-20021", "RN-20022", "RN-20023", "RN-20024", "RN-20025",
    "RN-20026", "RN-20027", "RN-20028", "RN-20029", "RN-20030",
    "RN-20031", "RN-20032", "RN-20033", "RN-20034", "RN-20035",
    "RN-20036", "RN-20037", "RN-20038", "RN-20039", "RN-20040",
    "RN-20041", "RN-20042", "RN-20043", "RN-20044", "RN-20045",
}

_LAB_LICENSES: set[str] = {
    "LT-30001", "LT-30002", "LT-30003", "LT-30004", "LT-30005",
    "LT-30006", "LT-30007", "LT-30008", "LT-30009", "LT-30010",
    "LT-30011", "LT-30012", "LT-30013", "LT-30014", "LT-30015",
    "LT-30016", "LT-30017", "LT-30018", "LT-30019", "LT-30020",
    "LT-30021", "LT-30022", "LT-30023", "LT-30024", "LT-30025",
    "LT-30026", "LT-30027", "LT-30028", "LT-30029", "LT-30030",
    "LT-30031", "LT-30032", "LT-30033", "LT-30034", "LT-30035",
    "LT-30036", "LT-30037", "LT-30038", "LT-30039", "LT-30040",
    "LT-30041", "LT-30042", "LT-30043", "LT-30044", "LT-30045",
}

_PHARMACIST_LICENSES: set[str] = {
    "PH-40001", "PH-40002", "PH-40003", "PH-40004", "PH-40005",
    "PH-40006", "PH-40007", "PH-40008", "PH-40009", "PH-40010",
    "PH-40011", "PH-40012", "PH-40013", "PH-40014", "PH-40015",
    "PH-40016", "PH-40017", "PH-40018", "PH-40019", "PH-40020",
    "PH-40021", "PH-40022", "PH-40023", "PH-40024", "PH-40025",
    "PH-40026", "PH-40027", "PH-40028", "PH-40029", "PH-40030",
    "PH-40031", "PH-40032", "PH-40033", "PH-40034", "PH-40035",
    "PH-40036", "PH-40037", "PH-40038", "PH-40039", "PH-40040",
    "PH-40041", "PH-40042", "PH-40043", "PH-40044", "PH-40045",
}

_INSURER_LICENSES: set[str] = {
    "INS-50001", "INS-50002", "INS-50003", "INS-50004", "INS-50005",
    "INS-50006", "INS-50007", "INS-50008", "INS-50009", "INS-50010",
    "INS-50011", "INS-50012", "INS-50013", "INS-50014", "INS-50015",
    "INS-50016", "INS-50017", "INS-50018", "INS-50019", "INS-50020",
    "INS-50021", "INS-50022", "INS-50023", "INS-50024", "INS-50025",
    "INS-50026", "INS-50027", "INS-50028", "INS-50029", "INS-50030",
    "INS-50031", "INS-50032", "INS-50033", "INS-50034", "INS-50035",
    "INS-50036", "INS-50037", "INS-50038", "INS-50039", "INS-50040",
    "INS-50041", "INS-50042", "INS-50043", "INS-50044", "INS-50045",
}

_BLOOD_BANK_LICENSES: set[str] = {
    "BB-60001", "BB-60002", "BB-60003", "BB-60004", "BB-60005",
    "BB-60006", "BB-60007", "BB-60008", "BB-60009", "BB-60010",
    "BB-60011", "BB-60012", "BB-60013", "BB-60014", "BB-60015",
    "BB-60016", "BB-60017", "BB-60018", "BB-60019", "BB-60020",
    "BB-60021", "BB-60022", "BB-60023", "BB-60024", "BB-60025",
    "BB-60026", "BB-60027", "BB-60028", "BB-60029", "BB-60030",
    "BB-60031", "BB-60032", "BB-60033", "BB-60034", "BB-60035",
    "BB-60036", "BB-60037", "BB-60038", "BB-60039", "BB-60040",
    "BB-60041", "BB-60042", "BB-60043", "BB-60044", "BB-60045",
}

# ---------------------------------------------------------------------------
# Unified registry — keyed by RoleEnum
# ---------------------------------------------------------------------------

LICENSE_REGISTRY: dict[RoleEnum, set[str]] = {
    RoleEnum.DOCTOR:     _DOCTOR_LICENSES,
    RoleEnum.NURSE:      _NURSE_LICENSES,
    RoleEnum.LAB:        _LAB_LICENSES,
    RoleEnum.PHARMACIST: _PHARMACIST_LICENSES,
    RoleEnum.INSURER:    _INSURER_LICENSES,
    RoleEnum.BLOOD_BANK: _BLOOD_BANK_LICENSES,
}

# Roles that require license verification (must exist in LICENSE_REGISTRY)
LICENSED_ROLES: frozenset[RoleEnum] = frozenset(LICENSE_REGISTRY.keys())
