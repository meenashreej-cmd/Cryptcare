#!/usr/bin/env python3
"""
Phase 6.2 — Dependency Vulnerability Audit
============================================
Runs pip-audit against requirements.txt and reports any known CVEs.

Usage:
    python scripts/dep_audit.py

Exit codes:
    0 — no known vulnerabilities
    1 — vulnerabilities found or pip-audit not available
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
REQ = ROOT / "requirements.txt"


def run_audit() -> int:
    print("CryptCare Dependency Audit — Phase 6.2")
    print(f"Requirements: {REQ}\n")

    # Run pip-audit with JSON output for structured parsing
    result = subprocess.run(
        [sys.executable, "-m", "pip_audit", "-r", str(REQ), "--format", "json", "--progress-spinner", "off"],
        capture_output=True,
        text=True,
    )

    # pip-audit exits 1 when vulnerabilities are found, 0 when clean.
    # It also exits 1 on tool errors — distinguish by parsing output.
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        # pip-audit not installed or non-JSON error
        print("ERROR: Could not parse pip-audit output. Is pip-audit installed?")
        print("  Install with: pip install pip-audit")
        if result.stderr:
            print(result.stderr[:500])
        return 1

    packages_with_vulns = [p for p in data.get("dependencies", []) if p.get("vulns")]

    if not packages_with_vulns:
        total = len(data.get("dependencies", []))
        print(f"✓ CLEAN — {total} packages audited, 0 vulnerabilities found.")
        return 0

    total_vulns = sum(len(p["vulns"]) for p in packages_with_vulns)
    print(f"✗ FOUND {total_vulns} vulnerabilities in {len(packages_with_vulns)} packages:\n")

    for pkg in packages_with_vulns:
        print(f"  Package : {pkg['name']} {pkg['version']}")
        for vuln in pkg["vulns"]:
            fix_versions = ", ".join(vuln.get("fix_versions", [])) or "No fix available"
            aliases = ", ".join(vuln.get("aliases", [])) or vuln["id"]
            print(f"    [{aliases}]")
            print(f"      Fix: {fix_versions}")
            desc = vuln.get("description", "")
            if desc:
                print(f"      Detail: {desc[:200]}")
            print()

    print("Action required: upgrade the packages listed above to their fix versions.")
    return 1


if __name__ == "__main__":
    sys.exit(run_audit())
