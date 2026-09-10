# CryptCare Backend — Full 13-Phase Build

Working FastAPI implementation of the entire architecture:
- **Phase 1** — User Registration & Digital Identity (register, OTP verification, license verification, login, JWT refresh)
- **Phase 2** — Cryptographic Health Vault (prescriptions, allergies, vaccinations — AES-256-GCM encrypted, consent-gated access)
- **Phase 3** — Laboratory Management (test request → in-progress → report upload → consent-gated viewing)
- **Phase 4** — Consent Management (request/approve/reject/revoke, break-glass, caregiver access, activity timeline, notifications)
- **Phase 5** — Security Hardening (real TOTP MFA, encryption key rotation, rate limiting)
- **Phase 6** — Nurse Role & Vitals
- **Phase 7** — Clinical Safety Validation (real drug-interaction/allergy/duplicate checking)
- **Phase 8** — Pharmacy (scan-to-verify, dispense tracking)
- **Phase 9** — Fraud Detection
- **Phase 10** — Emergency QR Access
- **Phase 11** — Blood Bank (inventory, requests, fulfillment)
- **Phase 12** — Insurance Provider Claims (creation, approval/rejection)
- **Phase 13** — Audit Dashboard & Hospital Admin (system-wide access logs, pending verifications)

This has been run end-to-end against an in-memory SQLite test database. It has **not** been run against a live MySQL instance — see Setup below.

> **Note on phase numbering:** `CryptCare_Architecture.md` and `CryptCare_Phase_Specs.md`, referenced elsewhere in this README as the source of full phase-by-phase pseudocode, weren't included in this working copy — only the backend code itself was available to build against. Phase 6 (Nurse role) was scoped from gaps visible in the code; Phase 7 had a clear anchor — the pre-existing stub in `clinical_safety_service.py` explicitly said "full implementation ships with Phase 7." If your actual specs differ from what's built here, treat these as additive rather than a replacement.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# then edit .env:
#   - set a real JWT_SECRET_KEY
#   - generate ENCRYPTION_KEY_V1 with:
python3 -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"
#   - point DATABASE_URL at your MySQL instance (or use sqlite:///./dev.db for quick local testing)

uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` for interactive Swagger UI covering all Phase 1-3 endpoints.

## What's stubbed / simplified for this milestone

- **Prescription signing (`app/core/signing.py`)** — uses HMAC-SHA256 keyed off a per-doctor derived secret, not full RSA-4096/ECC keypairs. This still demonstrates tamper-evidence (the property that matters for Phase 8's signature-verification step) but should be upgraded to real asymmetric signing for a production/thesis-grade security writeup.
- **OTP delivery** — printed to console (`[DEV] OTP for...`) instead of an actual SMS/email gateway. Swap `_send_otp()` in `auth_service.py` for a real gateway call.
- **MFA recovery** — if a DOCTOR/PHARMACIST/ADMIN loses their authenticator device, there's no re-provisioning endpoint yet (the provisioning URI is shown exactly once, at registration, by design — same as GitHub/AWS recovery codes). A real deployment needs an admin-mediated "reset MFA" flow with its own audit trail; flagged as a follow-up, not built here.
- **Rate limiting store** — in-memory per-process (`app/middleware/rate_limit.py`). Correct for a single instance; a horizontally-scaled deployment needs a shared backend (Redis INCR+EXPIRE) so limits are enforced across instances rather than reset per-pod.
- **Lab report file storage** — writes encrypted files to local disk (`/tmp/cryptcare_lab_reports` by default) rather than S3-compatible object storage. Fine for a demo; swap `_store_encrypted_file()` for a real object-storage client in production.
- **`doctor_id` on Prescription/LabTestRequest** — currently stores the JWT's `user_id` directly for simplicity. In the full build, resolve this to the `doctor_profiles.doctor_id` (join on `user_id`) before persisting, since that's the FK target per the schema in `CryptCare_Architecture.md`.
- **Startup table creation** — `app/main.py`'s startup event calls `Base.metadata.create_all()` against whatever `DATABASE_URL` resolves to. Running locally/in CI without a MySQL instance reachable still works — just point `DATABASE_URL` at a SQLite file (e.g. `sqlite:////tmp/cryptcare_dev.db`); the test suite already does this via its own override for the request-scoped DB, but the startup event itself always needs *some* reachable `DATABASE_URL` to succeed against.

## What's fully implemented and testable end-to-end

1. Register a Patient → verify OTP → login → GET `/api/v1/auth/me`
2. Register a Doctor → Admin approves license via `PUT /api/v1/auth/verify-license/{id}` → Doctor logs in
3. A Doctor **cannot** write a prescription for a patient without an approved `consent_requests` row (returns 403) — you'll need to manually insert a test consent row until Phase 4's endpoints exist, since Phase 4 hasn't been built yet
4. Full lab workflow: Doctor creates a test request → Lab starts processing → Lab uploads report (multipart file + summary) → Patient/Doctor views decrypted summary
5. Every vault/lab read-write is written to `access_logs`, viewable directly in the DB (Phase 13's dashboard endpoints aren't built yet, but the underlying log rows are already being produced)

## Fixes applied in this pass (post code-review)

- **Critical:** `vault_service.get_prescriptions()` and `lab_service.get_report()` were decrypting fields in place on session-attached rows, then calling `db.commit()` — which flushed the *decrypted* plaintext back into the encrypted database columns on every read. Fixed by committing first, then `db.expunge()`-ing rows before decrypting them for the response, so the in-memory mutation never reaches the database.
- OTP generation switched from `random.choices` (not cryptographically secure) to `secrets.choice`.
- OTP comparison switched to `hmac.compare_digest` for consistency with the constant-time signature check elsewhere.
- `login()` now always calls `verify_password()`, even for a nonexistent email, against a lazily-computed dummy hash — removes a timing side-channel that let an attacker distinguish "no such account" from "wrong password."
- Added an explicit `⚠️ SECURITY STUB` comment on the MFA bypass in `login()` so it can't be mistaken for a finished check in a later pass.
- `requirements.txt`: added missing `email-validator` (required by `EmailStr` in `schemas/auth.py` — the app didn't actually import without it) and pinned `bcrypt==4.0.1` (passlib 1.7.4 fails its backend init against bcrypt 4.1+/5.x).
- Removed a redundant duplicate `check_vault_access()` call in `lab_service.get_report()`.

## Phase 4 — Consent Management (new)

Workflow: DOCTOR/LAB requests access to a specific resource type → PATIENT approves (sets a time-limited `expires_at`) or rejects → `check_vault_access()` (used by Phases 2–3) now enforces it automatically. Patients can revoke an approved grant early.

**Endpoints:**
| Method | Path | Who |
|---|---|---|
| POST | `/api/v1/consent/request` | DOCTOR, LAB |
| GET | `/api/v1/consent/my-requests` | DOCTOR, LAB — their own requests, any status |
| PUT | `/api/v1/consent/{consent_id}/approve` | PATIENT |
| PUT | `/api/v1/consent/{consent_id}/reject` | PATIENT |
| POST | `/api/v1/consent/revoke/{consent_id}` | PATIENT |
| GET | `/api/v1/consent/my-consents` | PATIENT — currently ACTIVE grants |
| GET | `/api/v1/consent/history` | PATIENT — every status, past and present |
| GET | `/api/v1/consent/all` | ADMIN — read-only, everything |

**Design notes:**
- One consent row = one grantee + one resource type + one permission level (READ/WRITE/BOTH). A doctor needing both prescriptions and lab_reports access holds two separate rows — each independently approvable/revocable/auditable, rather than one row with a multi-value scope.
- `resource_type: "all"` grants cover every resource type in a single row (used sparingly — most requests should be scoped to what's actually needed).
- Expiry is lazy: `expire_stale_consents()` flips `ACTIVE` rows past `expires_at` to `EXPIRED` at check/list time. No scheduler needed for an academic build; note this in your write-up as "eventually consistent within one request," not a background cron job.
- Every grant/approve/reject/revoke writes an `AccessLog` row (`CONSENT_REQUESTED`/`CONSENT_APPROVED`/`CONSENT_REJECTED`/`CONSENT_REVOKED`) — Phase 13's Audit Dashboard has real data to show from day one.
- `check_vault_access()`'s function signature is unchanged, so `vault_service.py` and `lab_service.py` needed zero code changes to pick this up.

## Phase 2/3/4 extensions (new)

Six additions layered onto the existing phases, per an enhanced roadmap review — none needed a new phase, each slots into the phase that already owns that data/workflow.

**Phase 2 — Prescription QR codes**
- `GET /api/v1/vault/prescriptions/{id}/qr` — returns a PNG QR code, access-gated identically to reading the prescription itself.
- The QR payload is `cryptcare:prescription:{id}:{signature}` — a reference + the existing Ed25519/HMAC signature, **never the prescription's actual content**. A photographed/leaked QR image can't leak PHI; resolving it still requires going through the normal authenticated + consent-gated API.
- `app/core/qr.py` also has `parse_prescription_qr_payload()`, ready for a future Phase 8 (Pharmacy) scan-to-verify endpoint.

**Phase 3 — Encrypted imaging/document uploads**
- `LabReport` gained `document_type` (`MRI`/`CT_SCAN`/`XRAY`/`PDF_REPORT`/`LAB_SUMMARY`/`OTHER`), `original_filename_encrypted`, and `file_size_bytes`.
- `POST /api/v1/lab/requests/{id}/report` now takes a `document_type` form field. Uploads are validated against a 25MB size cap and a per-type extension allowlist (e.g. `PDF_REPORT` only accepts `.pdf`) before encryption — **extension-based, not content-sniffed**; a real deployment should verify actual file signatures/magic bytes before trusting `document_type`, flagged as a follow-up hardening item, not done here.
- Same envelope-encryption path as before (`_store_encrypted_file`) — imaging files just flow through the existing per-file encryption, no new crypto primitive.

**Phase 4 — Break-glass emergency access**
- `POST /api/v1/consent/break-glass` (DOCTOR/LAB) — grants immediate access with **no approval step**, compensated for on three fronts, all mandatory: (1) hard time-boxed to 1 hour regardless of what's requested, (2) logged with a distinct `AccessActionEnum.BREAK_GLASS_ACCESS` action, never conflated with a normal consent-gated read, (3) triggers an immediate patient notification — in the *same transaction* as the grant, not best-effort — disclosing who accessed what, why (a `reason` field is mandatory, min 10 chars), and when it expires.
- Reuses the existing `ConsentRequest` table (`is_break_glass=True` flag) and the *unmodified* `check_vault_access()` — an ACTIVE break-glass row is evaluated exactly like any other ACTIVE row, so the access-control choke point needed zero special-casing.

**Phase 4 — Delegated caregiver/family access**
- `POST /api/v1/consent/caregiver/grant` (PATIENT) — patient grants a named caregiver (by email, must have an existing account) a scoped subset of their own access, immediately ACTIVE (patient IS the approver, no request/approve round-trip).
- Also reuses `ConsentRequest` (`grantee_type=CAREGIVER`) — revoking a caregiver grant uses the same generic `POST /api/v1/consent/revoke/{consent_id}` as any other grant.

**Phase 4 — Patient activity timeline**
- `GET /api/v1/consent/timeline` (PATIENT) — chronological feed over the existing append-only `AccessLog` table, filtered to the logged-in patient's own records. `AccessLog` gained a `patient_id` column (nullable, separate from `user_id` the actor) specifically to make this query possible; every service's audit-log calls were updated to pass it through.
- No new logging mechanism — purely a read-only projection over audit data that already existed.

**Phase 4 — Real-time notifications**
- New `Notification` model + `notification_service.py` + `GET /api/v1/notifications` / `PUT /api/v1/notifications/{id}/read`.
- Wired into: consent requests, consent approvals (implicitly via the request), break-glass access, new prescriptions, and new lab results. Insurance updates (`NotificationTypeEnum.INSURANCE_UPDATE`) are defined but have no producer yet — that's Phase 9.
- **"Real-time" here means event-driven at write time, not push-delivered** — clients poll `GET /notifications`. Actual device push (FCM/APNs) would sit behind this table as a delivery mechanism later, same relationship OTP-to-console has to OTP-to-SMS. Notification payloads carry a reference + short message only, never full record content — deliberate, so a notification can't become a side-channel that leaks PHI to a lock screen.

## Phase 5 — Security hardening (new)

**Real TOTP MFA**
- DOCTOR/PHARMACIST/ADMIN registrations now generate a real `pyotp` TOTP secret immediately, encrypted at rest with the same AES-256-GCM field encryption used for PHI, and stored on `users.mfa_secret`.
- `POST /api/v1/auth/register`'s response includes a one-time `mfa_provisioning_uri` (`otpauth://totp/...`) for these roles — scan it into an authenticator app (Google Authenticator, Authy, etc.) immediately, since it is never returned again. Losing it means an admin-mediated reset (not built — see stubs above).
- `login()` now does a real `pyotp.TOTP(secret).verify(otp_code, valid_window=1)` check instead of accepting any non-empty code, plus single-use replay protection: the same 30-second code can't be reused for a second login even while still inside its validity window.

**Encryption key rotation**
- `app/core/encryption.py` gained `register_key_version()` — hot-registers an additional AES-256-GCM key into the in-process registry (what a KMS-refresh hook would call in production) without needing a restart.
- Ciphertext blobs already carried their key version (`"v1:nonce:ciphertext"`), so rotation is just: register the new key, flip `ACTIVE_ENCRYPTION_KEY_VERSION`, and new writes use it — old rows keep decrypting against their original version with no re-encryption pass required. See `tests/test_key_rotation.py` for the full before/after/rotate/decrypt cycle.

**Rate limiting middleware**
- `app/middleware/rate_limit.py` — in-memory sliding-window limiter, applied globally via `app.add_middleware()`. `/auth/login` and `/auth/verify-otp` get tighter limits (5 requests per 60s / 300s respectively) than the general API default (100/60s), to blunt credential-stuffing and OTP brute-forcing without throttling normal usage. Returns `429` with a `Retry-After` header once exceeded.

## Phase 6 — Nurse role & vital signs (new)

**New role:** `NURSE` added to `RoleEnum`, with its own `NurseProfile` (license number, hospital, department) provisioned at registration — same license-required + OTP + admin-verification pattern as DOCTOR/LAB/PHARMACIST/INSURER. MFA is required for NURSE too (alongside DOCTOR/PHARMACIST/ADMIN), since nurses handle the same class of PHI.

**New resource type:** `vitals` added to `ResourceTypeEnum`, flowing through the exact same consent machinery every other resource already uses — a nurse is just another `grantee_id` in `consent_requests`, with **no implicit inheritance** of a supervising doctor's consent grant. A patient (or emergency break-glass) is what grants a nurse access, never another clinician — this was a deliberate least-privilege choice, not an oversight.

**New endpoints** (`app/api/v1/endpoints/nursing.py`):
- `POST /api/v1/nursing/vitals` — nurse records a vitals observation (heart rate, blood pressure, temperature, respiratory rate, SpO2, free-text notes) for a patient. Requires an ACTIVE `vitals:write` (or `BOTH`) consent grant. Free-text notes are AES-256-GCM encrypted at rest, same as diagnosis/prescription notes.
- `GET /api/v1/nursing/patients/{patient_id}/vitals` — read a patient's vitals history, newest first. The patient always sees their own (ownership check, no grant needed); anyone else needs an ACTIVE `vitals:read` grant.

**Consent flow extended:** `POST /api/v1/consent/request` and `GET /api/v1/consent/my-requests` now accept NURSE alongside DOCTOR/LAB. Break-glass emergency access (`POST /api/v1/consent/break-glass`) was deliberately **not** extended to NURSE in this pass — kept DOCTOR/LAB-only to limit the blast radius of a new, lower-trust role; revisit this if your actual clinical workflow needs nurses to have emergency override too.

**Role check lives in the service, not the endpoint:** `nursing_service.record_vitals()` checks `current_user.role != "NURSE"` itself (see `test_non_nurse_role_cannot_record_vitals_even_with_consent`), matching `vault_service.create_prescription()`'s existing pattern — the endpoint layer uses `get_current_user`, not `require_role`, so all vault-style read/write authorization logic stays in one place.

## Phase 7 — Clinical Safety Validation (new)

**⚠️ The curated interaction/allergy dataset is illustrative, not clinically authoritative.** `app/data/drug_knowledge_base.py` has ~15 well-known textbook interactions and a handful of allergy classes — enough to make the architecture demonstrable and testable, nowhere near enough to be a real safety net. Read the disclaimer at the top of that file before this touches anything beyond a demo. A real deployment needs a licensed, regularly-updated drug database behind this, not this module.

**Real checks, replacing the always-safe stub:**
- **Interactions** — pairwise lookup, checked both within a new prescription's own items and against the patient's other ACTIVE prescriptions. `SEVERE` blocks (422); `MODERATE` is surfaced as a non-blocking warning.
- **Allergies** — cross-checks each prescribed drug's allergen class against the patient's recorded `Allergy` rows. Any match blocks.
- **Duplicates** — flags a drug the patient already has an ACTIVE prescription for. Never blocks by design — legitimate reasons for intentional duplicate therapy exist that this system can't distinguish from a real mistake.

**FAISS-based fuzzy drug-name matching** (`app/core/drug_matching.py`) resolves a doctor's free-text `medicine_name` ("Amoxicillin 500mg", a typo like "ibuprofin") to a canonical drug before any rule lookup, via `app/core/text_embeddings.py` — a dependency-free character-trigram hashing embedding (no pretrained model, no internet access needed, fully deterministic across restarts). A drug outside the curated dataset is reported as `unmatched_drugs` but never blocks — absence from this small list says nothing about actual safety.

**Local LLM explanations** (`app/core/local_llm.py`) — best-effort call to a local Ollama instance to turn the structured findings into a plain-language summary for the prescribing doctor. Strict separation of concerns: the LLM only explains findings that were already computed deterministically; it's never consulted for the block/no-block decision, and if Ollama isn't running (true in this test environment, and possibly in yours), every check falls back to a deterministic templated explanation — the safety outcome never depends on the model being available.

**API changes:** `POST /api/v1/vault/prescriptions` now returns a `safety_warnings` field (non-blocking findings — moderate interactions, duplicates, unmatched drugs) on a successful `201`, and a blocking check now returns real structured findings in the `422` response instead of an empty always-safe stub result.

## Next milestones

- MFA recovery flow (admin-mediated secret reset for a lost authenticator device)
- Shared (Redis-backed) rate-limit store for horizontally-scaled deployments
- Content-sniffing (not just extension-checking) for Phase 3 document uploads
- Write test suite for the newly added Phase 8-13 endpoints
