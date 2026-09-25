#!/usr/bin/env python3
"""
Phase 6.1 — Secret Scanner
===========================
Scans the CryptCare codebase for hardcoded secrets, credentials, and
sensitive values that should never be committed to source control.

Usage:
    python scripts/secret_scan.py [--strict]

Exit codes:
    0 — clean (or only whitelisted findings)
    1 — real secrets detected

Findings are split into:
  CRITICAL  — actual secret values (fails CI)
  WARNING   — default/placeholder values (acceptable in code, not in .env)
  INFO      — patterns that look suspicious but are likely false positives
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).parent.parent

# ── Directories and extensions to scan ──────────────────────────────────────

SCAN_EXTENSIONS = {".py", ".env", ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".txt"}
EXCLUDE_DIRS = {"venv", ".venv", ".git", "__pycache__", "node_modules", "dist", "build", ".pytest_cache", "uploads"}
EXCLUDE_FILES = {".env"}  # actual .env is excluded from git; scan .env.example instead

# ── Secret patterns ──────────────────────────────────────────────────────────

@dataclass
class SecretPattern:
    name: str
    pattern: re.Pattern
    severity: str          # CRITICAL | WARNING | INFO
    description: str
    # Files/lines where this match is expected (whitelisted)
    whitelist: list[str]   # strings that if present in the line, skip it


PATTERNS: list[SecretPattern] = [
    SecretPattern(
        name="AWS Access Key ID",
        pattern=re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
        severity="CRITICAL",
        description="AWS Access Key ID found — rotate immediately",
        whitelist=[],
    ),
    SecretPattern(
        name="AWS Secret Access Key",
        pattern=re.compile(r'(?i)aws.{0,20}secret.{0,20}["\x27][A-Za-z0-9/+]{40}["\x27]'),
        severity="CRITICAL",
        description="AWS Secret Access Key found",
        whitelist=[],
    ),
    SecretPattern(
        name="JWT Bearer Token",
        pattern=re.compile(r'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}'),
        severity="CRITICAL",
        description="Live JWT token committed to source",
        whitelist=["# example", "test", "dummy", "fake"],
    ),
    SecretPattern(
        name="RSA/EC Private Key",
        pattern=re.compile(r'BEGIN\s+(RSA|EC|OPENSSH|DSA)\s+PRIVATE\s+KEY'),
        severity="CRITICAL",
        description="Private key material found in source",
        whitelist=[],
    ),
    SecretPattern(
        name="Generic High-Entropy Secret",
        pattern=re.compile(r'(?i)(?:secret|password|passwd|pwd|api_key|apikey|auth_token)\s*[=:]\s*["\x27][A-Za-z0-9!@#$%^&*()\-_+=]{16,}["\x27]'),
        severity="CRITICAL",
        description="High-entropy credential value found",
        whitelist=[
            # Test fixtures use known values intentionally
            "SuperSecretPassword", "Password123", "test", "fixture",
            # Placeholder detection sets — these are fine
            "replace-with", "changeme", "your-secret", "placeholder",
            # Seed script marker
            "PASSWORD =",
        ],
    ),
    SecretPattern(
        name="Hardcoded Database Password",
        pattern=re.compile(r'(?i)mysql\+pymysql://[^:]+:[^@/]{4,}@'),
        severity="WARNING",
        description="Hardcoded database password in connection string",
        whitelist=[
            "changeme",          # default placeholder — acceptable in config.py default
            "cryptcare_user",    # documented default in .env.example
            "root:1234",         # test-only MariaDB fixture
            "conftest",          # test file
        ],
    ),
    SecretPattern(
        name="SMTP Password",
        pattern=re.compile(r'(?i)smtp.{0,30}password\s*[=:]\s*["\x27][^"\x27]{4,}["\x27]'),
        severity="WARNING",
        description="SMTP password in source",
        whitelist=["your-gmail-app-password", "example", ".env.example", "SMTP_PASSWORD="],
    ),
    SecretPattern(
        name="Placeholder Key",
        pattern=re.compile(r'(?i)(replace.with|changeme|your.secret.key|insert.your|todo.+key)', re.IGNORECASE),
        severity="INFO",
        description="Placeholder value — ensure .env overrides this",
        whitelist=[
            # These are intentional in the placeholder-detection sets
            "_PLACEHOLDER_JWT_SECRETS", "_PLACEHOLDER_ENC_KEYS",
            ".env.example", "main.py",
        ],
    ),
    SecretPattern(
        name="Hardcoded IP (non-loopback)",
        pattern=re.compile(r'\b(?!127\.|0\.0\.0\.0|localhost)(?:\d{1,3}\.){3}\d{1,3}\b'),
        severity="INFO",
        description="Non-loopback IP address hardcoded",
        whitelist=["# example", "127.0.0.1", "test", "conftest", "docker"],
    ),
]


# ── Scanner ──────────────────────────────────────────────────────────────────

@dataclass
class Finding:
    severity: str
    file: str
    line: int
    pattern_name: str
    description: str
    content: str


def _should_exclude(path: Path) -> bool:
    parts = set(path.parts)
    return bool(parts & EXCLUDE_DIRS) or path.name in EXCLUDE_FILES


def scan_file(filepath: Path) -> list[Finding]:
    findings = []
    try:
        text = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings

    for lineno, line in enumerate(text.splitlines(), start=1):
        for sp in PATTERNS:
            if sp.pattern.search(line):
                # Check whitelist — if any whitelist term appears in the line or filepath, skip
                whitelisted = any(
                    w.lower() in line.lower() or w.lower() in str(filepath).lower()
                    for w in sp.whitelist
                )
                if whitelisted:
                    continue

                findings.append(Finding(
                    severity=sp.severity,
                    file=str(filepath.relative_to(ROOT)),
                    line=lineno,
                    pattern_name=sp.name,
                    description=sp.description,
                    content=line.strip()[:120],
                ))
    return findings


def run_scan(strict: bool = False) -> int:
    all_findings: list[Finding] = []

    for ext in SCAN_EXTENSIONS:
        for path in ROOT.rglob(f"*{ext}"):
            if _should_exclude(path):
                continue
            all_findings.extend(scan_file(path))

    # Deduplicate by (file, line, pattern)
    seen = set()
    unique: list[Finding] = []
    for f in all_findings:
        key = (f.file, f.line, f.pattern_name)
        if key not in seen:
            seen.add(key)
            unique.append(f)

    # Sort by severity then file
    sev_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    unique.sort(key=lambda f: (sev_order.get(f.severity, 9), f.file, f.line))

    criticals = [f for f in unique if f.severity == "CRITICAL"]
    warnings  = [f for f in unique if f.severity == "WARNING"]
    infos     = [f for f in unique if f.severity == "INFO"]

    def _print_group(label: str, items: list[Finding]) -> None:
        if not items:
            return
        print(f"\n{'='*60}")
        print(f"  {label} ({len(items)} finding{'s' if len(items)!=1 else ''})")
        print(f"{'='*60}")
        for f in items:
            print(f"  [{f.severity}] {f.file}:{f.line}")
            print(f"    Pattern : {f.pattern_name}")
            print(f"    Detail  : {f.description}")
            print(f"    Line    : {f.content}")
            print()

    print("\nCryptCare Secret Scanner — Phase 6.1")
    print(f"Scanning: {ROOT}")
    _print_group("CRITICAL — Real secrets (must fix before commit)", criticals)
    _print_group("WARNING  — Defaults/placeholders (verify .env overrides)", warnings)
    _print_group("INFO     — Suspicious patterns (review manually)", infos)

    total = len(unique)
    print(f"\nSummary: {len(criticals)} critical, {len(warnings)} warnings, {len(infos)} info  ({total} total)")

    if criticals:
        print("\n✗ FAILED — Critical secrets detected. Do not commit.")
        return 1

    if strict and warnings:
        print("\n✗ FAILED (strict mode) — Warnings present.")
        return 1

    print("\n✓ PASSED — No critical secrets found.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CryptCare secret scanner")
    parser.add_argument("--strict", action="store_true", help="Fail on warnings too")
    args = parser.parse_args()
    sys.exit(run_scan(strict=args.strict))
