#!/usr/bin/env python3
"""Run every check this repo has and print one PASS/FAIL line per check.

    python3 tools/test_all.py            # everything
    python3 tools/test_all.py --quick    # contracts + hooks corpus only (skips the slow runner suite)

Exit 0 only when every check passes. Each test script runs from its own skill folder, the
way its docstring says to run it. Zero dependencies; Python 3.8+.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SK = ROOT / ".claude" / "skills"

# (label, cwd, argv). Order: cheap and broad first.
CHECKS = [
    ("contracts", ROOT, [sys.executable, "tools/check_contracts.py"]),
    ("hooks corpus", ROOT, [sys.executable, "hooks/_test_hooks.py"]),
    ("drive-screen autodrive", SK / "drive-screen", [sys.executable, "scripts/_test_autodrive.py"]),
    ("drive-screen screenctl", SK / "drive-screen", [sys.executable, "scripts/_test_screenctl.py"]),
    ("dark-factory audit runner", SK / "build-dark-factory", [sys.executable, "scripts/_test_audit_runner.py"]),
    ("dark-factory doctor", SK / "build-dark-factory", [sys.executable, "scripts/_test_factory_doctor.py"]),
    ("dark-factory runner (slow)", SK / "build-dark-factory", [sys.executable, "scripts/_test_runner.py"]),
]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quick", action="store_true", help="skip the slow suites")
    args = ap.parse_args(argv)

    failed = 0
    for label, cwd, cmd in CHECKS:
        if args.quick and "(slow)" in label:
            print(f"SKIP  {label}")
            continue
        t0 = time.time()
        try:
            r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=1800)
            code = r.returncode
            tail = (r.stdout.strip().splitlines() or r.stderr.strip().splitlines() or [""])[-1]
        except subprocess.TimeoutExpired:
            code, tail = 124, "timed out"
        except FileNotFoundError as e:
            code, tail = 127, str(e)
        status = "PASS" if code == 0 else "FAIL"
        failed += code != 0
        print(f"{status}  {label:28} {time.time() - t0:6.1f}s  {tail[:100]}")
        if code != 0:
            print("      " + "\n      ".join((r.stdout + r.stderr).strip().splitlines()[-15:]) if 'r' in locals() else "")
    print(f"\n{'PASS' if not failed else 'FAIL'}: {len(CHECKS) - failed}/{len(CHECKS)} checks green")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
