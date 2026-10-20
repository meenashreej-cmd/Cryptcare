import React from "react";
import { ShieldCheck, X, FileText, Lock } from "lucide-react";

export default function LegalModal({ type, onClose }) {
  if (!type) return null;

  const isTerms = type === "terms";
  const title = isTerms ? "Terms of Service" : "Privacy Policy";
  const Icon = isTerms ? FileText : Lock;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-2xl bg-white rounded-3xl shadow-2xl border border-slate-100 overflow-hidden max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/70">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-teal-50 text-[#0FB6AA] flex items-center justify-center">
              <Icon size={18} />
            </div>
            <div>
              <h3 className="font-bold text-slate-800 text-base font-display">{title}</h3>
              <p className="text-xs text-slate-400">CryptCare Sovereign Patient Network</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto text-sm text-slate-600 space-y-4 leading-relaxed">
          {isTerms ? (
            <>
              <p className="font-semibold text-slate-800">
                1. Acceptance of Terms & Patient Sovereignty
              </p>
              <p>
                By creating an account on CryptCare (&ldquo;Platform&rdquo;), you enter into a binding agreement
                affirming that your health records, personal health information (PHI), and medical vault
                remain your exclusive sovereign property under HIPAA and international cryptographic data protection laws.
              </p>

              <p className="font-semibold text-slate-800">
                2. Zero-Knowledge Cryptographic Guarantees
              </p>
              <p>
                All personal health records deposited into CryptCare are encrypted client-side or at the envelope
                boundary with AES-256-GCM authenticated cipher suites. CryptCare operators cannot decrypt, sell,
                mine, or transfer your medical data without explicit, time-bounded cryptographic consent tokens.
              </p>

              <p className="font-semibold text-slate-800">
                3. Provider Access & Dynamic Consent
              </p>
              <p>
                Authorized medical providers (Doctors, Nurses, Pharmacists, Laboratories) only receive access
                upon explicit, auditable patient authorization. All state transitions, approvals, and emergency
                break-glass overrides are recorded on an immutable SHA-256 tamper-evident audit ledger.
              </p>

              <p className="font-semibold text-slate-800">
                4. Account Responsibilities & Credential Integrity
              </p>
              <p>
                You are responsible for safeguarding your multi-factor credentials, recovery tokens, and authenticator keys.
                CryptCare employs rigorous anti-brute force, Argon2id/bcrypt hashing, and automated anomaly detection to
                protect your account.
              </p>
            </>
          ) : (
            <>
              <p className="font-semibold text-slate-800">
                1. Zero-PHI Leakage Architecture
              </p>
              <p>
                CryptCare is engineered around the principle of Zero-Knowledge PHI. We do not maintain unencrypted
                data stores of diagnostic reports, blood bank records, prescription formulations, or clinical notes.
              </p>

              <p className="font-semibold text-slate-800">
                2. Information Collected & Verification Data
              </p>
              <p>
                During registration, we collect your Full Name, Email, and Phone number strictly to establish your
                cryptographic identity shard and deliver one-time verification codes (OTP). Professional accounts
                (Doctors, Nurses) are additionally cross-checked against authorized medical licensing registries.
              </p>

              <p className="font-semibold text-slate-800">
                3. Immutable Audit Trails
              </p>
              <p>
                Every access attempt, authorization grant, revocation, and data download is logged into an append-only
                hash chain with cryptographic verification tags. You retain the real-time right to inspect all audit
                entries impacting your record at any time through your dashboard.
              </p>

              <p className="font-semibold text-slate-800">
                4. Cryptographic Shredding & Account Deletion
              </p>
              <p>
                Under our cryptographic shredding policy, deleting a record or terminating your account immediately
                destroys the encryption keys required to read that vault block, rendering historical ciphertexts
                mathematically irrecoverable across all physical storage media.
              </p>
            </>
          )}

          <div className="p-3.5 rounded-xl bg-teal-50/70 border border-teal-100 flex items-start gap-2.5 text-xs text-teal-800 mt-4">
            <ShieldCheck size={16} className="text-[#0FB6AA] shrink-0 mt-0.5" />
            <span>
              CryptCare operates in strict compliance with HIPAA Security Standards, GDPR Privacy Shield principles, and RFC 6238 TOTP specifications.
            </span>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-100 bg-slate-50/70 flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2.5 rounded-xl font-semibold text-sm bg-gradient-to-r from-[#1D64EC] to-[#0FB6AA] text-white shadow-md hover:brightness-105 transition"
          >
            I Understand & Agree
          </button>
        </div>
      </div>
    </div>
  );
}
