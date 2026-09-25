# CryptCare — Threat Model & Attack Surface Analysis

**Version:** 1.0  
**Date:** 2026-09-10  
**Scope:** Backend API (`app/`) — Phases 1–6 security hardening  
**Framework:** STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege)

---

## 1. System Overview

CryptCare is a patient-sovereign healthcare API. Patients own their data; professionals access it only with consent. The system handles PHI (Protected Health Information) under HIPAA constraints.

**Trust boundaries:**

```
[Browser / Mobile App]
        │  HTTPS
        ▼
[FastAPI Backend :8000]  ◄──── .env (secrets outside process)
        │
        ├── [SQLite/MySQL DB]        ← PHI encrypted at field level
        ├── [Local Ollama LLM]       ← localhost only, never sees full records
        └── [File Storage /uploads]  ← encrypted at rest, per-patient dirs
```

**Actors:**

| Actor | Trust Level | Notes |
|---|---|---|
| Patient | Low-medium | Owns their data; limited scope |
| Doctor | Medium | Verified license; MFA required |
| Nurse | Medium | Delegated access only; consent-gated |
| Pharmacist | Medium | Read-only prescription verification |
| Lab Technician | Medium | Assigned requests only |
| Insurer | Low | Claims only; no clinical data |
| Blood Bank | Medium | Emergency broadcasts; consent-gated |
| Hospital Admin | High | User management; no clinical data |
| ADMIN | Very High | System-level; provisioned out-of-band |
| Unauthenticated | Untrusted | Minimal public surface |
| Attacker (external) | Adversarial | Network access assumed |
| Attacker (insider) | Adversarial | Compromised professional credential |

---

## 2. Attack Surface Inventory

### 2.1 Network-Exposed Endpoints

| Surface | Public? | Auth | Notes |
|---|---|---|---|
| `POST /api/v1/auth/register` | Yes | None | Rate-limited; license verified |
| `POST /api/v1/auth/login` | Yes | None | Rate-limited; lockout after 5 failures |
| `POST /api/v1/auth/verify-otp` | Yes | Preauth token | JTI one-time use |
| `POST /api/v1/auth/refresh` | Yes | HttpOnly cookie | CSRF header required |
| `GET /api/v1/emergency/access/{token}` | Yes | None | Short-lived QR token only |
| `GET /health` | Yes | None | No data returned |
| All other `/api/v1/*` | No | Bearer JWT | Deny-by-default enforced at startup |
| OpenAPI `/docs`, `/redoc`, `/openapi.json` | No (non-dev) | Disabled | Hidden in production |

### 2.2 Data Stores

| Store | Contains PHI? | Protection |
|---|---|---|
| Database (users table) | Yes (indirect) | Passwords bcrypt-hashed; MFA secrets AES-256-GCM encrypted |
| Database (vault tables) | Yes | All clinical fields AES-256-GCM encrypted with AAD binding |
| Database (audit log) | Partial (IDs) | SHA-256 hash chain; append-only pattern |
| File uploads (`/uploads`) | Yes | Stored as `<uuid>_<type>.<ext>`; original filename discarded |
| `.env` file | Yes (keys) | Excluded from git; startup rejects placeholder values |
| In-memory OTP store | Yes (OTP) | Expires in 5 min; process-local |

### 2.3 AI Boundary

| Input | Protection |
|---|---|
| Patient chat message | PHI redaction + injection detection before reaching LLM |
| LLM response | PHI redaction + system marker stripping + 2000-char truncation |
| LLM network | localhost Ollama only; no external API calls |
| Clinical safety findings | Structured dict only; never full patient record |

---

## 3. STRIDE Threat Analysis

### 3.1 Spoofing

| Threat | Attack | Control | Residual Risk |
|---|---|---|---|
| S1 | Attacker logs in as another user (stolen password) | bcrypt hashing; account lockout; IP rate limiting | Low — lockout triggers after 5 attempts |
| S2 | Attacker forges a JWT | HS256 with `JWT_SECRET_KEY`; type/purpose claim enforcement | Low — requires key compromise |
| S3 | Attacker replays a stolen refresh token | Token rotation + family invalidation; DB revocation | Low — reuse triggers full session wipe |
| S4 | Attacker replays a preauth token | JTI one-time use (UsedJTI table) | Low — token consumed on first use |
| S5 | Attacker replays a TOTP code | Monotonic step tracking (MfaState table) | Low — same step rejected after use |
| S6 | Attacker self-registers as DOCTOR | License number checked against verified dataset | Low — invalid license rejected |
| S7 | Attacker self-registers as ADMIN | ADMIN excluded from public registration | Eliminated |
| S8 | Attacker uses a valid but stale JWT after role downgrade | DB-authoritative role fetched on every request | Eliminated — JWT role ignored |

### 3.2 Tampering

| Threat | Attack | Control | Residual Risk |
|---|---|---|---|
| T1 | Attacker modifies stored PHI in DB | AES-256-GCM authenticated encryption — tampered ciphertext → decrypt failure | Low |
| T2 | Attacker copies a ciphertext between patient records | AAD binding ties ciphertext to patient_id + resource — transplant fails decryption | Low |
| T3 | Attacker forges a prescription | Ed25519 signature with doctor_id binding; length-prefix canonicalization | Low |
| T4 | Attacker alters audit log entries | SHA-256 hash chain — any row change breaks all subsequent hashes | Low |
| T5 | Attacker tampers with an uploaded file | File stored under UUID; original name discarded; MIME + magic-byte check on upload | Low |
| T6 | Attacker injects SQL via API inputs | Pydantic validators + injection pattern scanning; SQLAlchemy ORM (parameterized queries) | Low |
| T7 | Attacker injects template/script content in text fields | `validate_no_injection()` on all free-text fields (10 patterns) | Low |
| T8 | Attacker sends malicious file (disguised executable) | MIME allowlist + magic byte verification + malware signature scan | Low |

### 3.3 Repudiation

| Threat | Attack | Control | Residual Risk |
|---|---|---|---|
| R1 | Professional denies accessing a patient's record | AccessLog records every READ/WRITE/DENIED with user_id + timestamp + patient_id | Low |
| R2 | Doctor denies issuing a prescription | Ed25519 signature binds doctor_id to prescription content | Low |
| R3 | Attacker deletes audit entries to hide activity | Hash chain makes deletion detectable; rows should be append-only in production | Medium — DB admin could truncate; mitigate with DB-level write-only role |
| R4 | User denies performing an auth action (login, MFA enroll) | AUTH_LOGIN / AUTH_FAILED / MFA_ENROLLED events logged | Low |

### 3.4 Information Disclosure

| Threat | Attack | Control | Residual Risk |
|---|---|---|---|
| I1 | Attacker enumerates valid emails via login response | Identical 401 for wrong password vs non-existent user; timing-safe dummy hash | Low |
| I2 | Attacker reads PHI from stolen DB dump | AES-256-GCM field encryption; keys stored separately in `.env` | Low — requires both DB + key compromise |
| I3 | PHI leaks via browser cache | `Cache-Control: no-store` on all `/api/` responses | Low |
| I4 | PHI leaks via Referer header | `Referrer-Policy: strict-origin-when-cross-origin` | Low |
| I5 | PHI leaks via error messages | Crypto errors return generic message; no stack traces in prod | Low |
| I6 | PHI leaks through AI response | PHI redacted from LLM output; response truncated to 2000 chars | Low |
| I7 | Attacker reads another patient's records (IDOR/BOLA) | Consent gate on all cross-patient access; ownership checks in service layer | Low |
| I8 | API spec leaks internal route structure | OpenAPI/Swagger disabled in non-dev environments | Low |
| I9 | Signing key leakage via zero-key deployment | Startup rejects all-zeros signing key; Pydantic validator also rejects at load time | Eliminated |
| I10 | Attacker reads files of other patients via path traversal | Path traversal prevention in `file_security.py`; files stored under patient UUID dir | Low |
| I11 | XSS exfiltrates session data | HttpOnly cookie for refresh token; CSP blocks inline script; X-Content-Type-Options | Low |
| I12 | Clickjacking tricks user into actions | `X-Frame-Options: DENY`; CSP `frame-ancestors 'none'` | Low |

### 3.5 Denial of Service

| Threat | Attack | Control | Residual Risk |
|---|---|---|---|
| D1 | Brute-force login floods server | IP rate limiting (5/60s); account lockout; dual-layer middleware + DB | Low |
| D2 | Oversized file upload floods disk | Per-type file size limits (max 500MB absolute); checked before write | Low |
| D3 | Oversized request body floods memory | `python-multipart` limits; Pydantic field max_length on all string inputs | Low |
| D4 | LLM semaphore exhaustion (CPU starvation) | `BoundedSemaphore(2)` in ai.py; 503 if at capacity | Low |
| D5 | OTP flood (resend spam) | `resend_otp` limited to 1/60s per user, 5/60s per IP | Low |
| D6 | Concurrent blood-bank broadcast flood | DB-level cooldown per blood group + component | Low |
| D7 | API scan via automated tools | Rate limiter middleware (100 req/60s default per IP) | Medium — in-memory; survives only one instance |

### 3.6 Elevation of Privilege

| Threat | Attack | Control | Residual Risk |
|---|---|---|---|
| E1 | Patient accesses another patient's vault | Consent gate; ownership check; deny-by-default RBAC | Low |
| E2 | Nurse accesses data outside delegation | Nurse delegation model requires explicit consent grant | Low |
| E3 | Insurer reads clinical data | Role gate at endpoint level; consent gate at service level | Low |
| E4 | Attacker finds unprotected route | Startup deny-by-default enforcement — app crashes if any route lacks auth | Eliminated |
| E5 | Attacker uses suspended account token | Active-status check on every `get_current_user()` call | Eliminated |
| E6 | JWT with stale high role used after downgrade | DB-authoritative role check — JWT role claim ignored | Eliminated |
| E7 | MFA-bypass on privileged role login | MFA enforced for DOCTOR / PHARMACIST / ADMIN; secret encrypted at rest | Low |
| E8 | AI assistant used to extract data outside patient's own record | AI endpoint restricted to PATIENT role; LLM never receives full record | Low |

---

## 4. High-Risk Areas & Recommended Mitigations

| # | Area | Current State | Recommended Next Step |
|---|---|---|---|
| HR1 | Audit log deletion | Hash chain detects tampering but a DB admin can truncate | Grant `INSERT`-only DB role for audit table in production; consider immutable log store (e.g. CloudWatch, Loki) |
| HR2 | In-memory OTP store | Process-local; lost on restart; not multi-instance safe | Migrate to Redis with TTL for horizontal scaling |
| HR3 | In-memory rate limiter | `RateLimitMiddleware` uses a per-process dict | Move to Redis-backed sliding window for multi-node deployments |
| HR4 | SMTP credentials | Stored in `.env`; no rotation mechanism | Use a secrets manager (Vault, AWS Secrets Manager) with lease rotation |
| HR5 | Encryption key management | Keys loaded from `.env`; no HSM | Integrate a KMS (AWS KMS / HashiCorp Vault) for envelope encryption in production |
| HR6 | File storage | Local disk under `/uploads` | Move to S3-compatible encrypted object storage with server-side encryption and access logging |
| HR7 | TOTP window size | Default ±1 step (90s grace) | Consider ±0 (30s strict) for highest-privilege roles (ADMIN) |
| HR8 | No MFA on NURSE/LAB roles | Only DOCTOR/PHARMACIST/ADMIN enforce MFA | Evaluate enabling optional MFA for all professional roles |

---

## 5. Data Flow Diagram — Critical Path (Prescription Creation)

```
Patient Browser
    │
    │ HTTPS POST /api/v1/vault/prescriptions
    │ Bearer: <access_token>
    ▼
FastAPI Route (require_role("DOCTOR"))
    │ 1. verify_access_token() → TokenError if invalid/expired
    │ 2. DB fetch user → check status=ACTIVE, role=DOCTOR
    │ 3. Pydantic validation → injection scan, field regex
    ▼
vault_service.create_prescription()
    │ 4. check_vault_access() → consent gate for patient
    │ 5. clinical_safety_service → drug interaction check
    │ 6. encrypt(diagnosis, aad=patient_id+resource_id)
    │ 7. sign_prescription(content, doctor_id) → Ed25519 sig
    │ 8. db.add(Prescription) → commit
    │ 9. write_access_log(WRITE) → SHA-256 chain prev_hash
    ▼
Response (PrescriptionResponse)
    │ Cache-Control: no-store
    │ Security headers applied by SecurityHeadersMiddleware
    ▼
Patient Browser
```

---

## 6. Compliance Mapping (HIPAA Technical Safeguards)

| HIPAA § | Requirement | Implementation |
|---|---|---|
| 164.312(a)(1) | Access control | RBAC (`require_role`), consent gates, deny-by-default |
| 164.312(a)(2)(i) | Unique user identification | UUID user IDs; email uniqueness enforced |
| 164.312(a)(2)(iii) | Automatic logoff | JWT expiry (15 min access); refresh revocation on logout |
| 164.312(b) | Audit controls | `AccessLog` with 22-action taxonomy + hash chain |
| 164.312(c)(1) | Integrity | AES-256-GCM authenticated encryption; Ed25519 signatures |
| 164.312(c)(2) | Integrity mechanisms | Hash-chained audit log; AAD-bound ciphertext |
| 164.312(d) | Person authentication | bcrypt passwords + TOTP MFA for privileged roles |
| 164.312(e)(1) | Transmission security | HSTS enforced; TLS required (HTTPS-only headers) |
| 164.312(e)(2)(ii) | Encryption in transit | HSTS + CSP `upgrade-insecure-requests` |
