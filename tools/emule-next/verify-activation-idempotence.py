#!/usr/bin/env python3
"""Run eMule Next activation a second time and require an identical source tree.

The local build intentionally materializes legacy integration in the repository
overlay before copying it to the upstream source tree. A non-idempotent activator
therefore creates hard-to-reproduce builds. This verifier makes the second pass
a strict no-op and reports exactly which overlay files changed.
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
ACTIVATE = ROOT / "tools" / "emule-next" / "activate-features.py"


def snapshot() -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(SRC.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        result[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def main() -> int:
    before = snapshot()
    completed = subprocess.run([sys.executable, str(ACTIVATE)], cwd=str(ROOT), check=False)
    if completed.returncode != 0:
        print("eMule Next activation idempotence FAILED: second activation returned", completed.returncode)
        return completed.returncode or 1

    after = snapshot()
    changed = sorted({*before, *after} - {key for key in before.keys() & after.keys() if before[key] == after[key]})
    if changed:
        print("eMule Next activation idempotence FAILED: second pass changed source overlay")
        for rel in changed:
            state = "added" if rel not in before else ("removed" if rel not in after else "modified")
            print(f" - {state}: {rel}")
        return 1

    print(f"eMule Next activation idempotence passed ({len(after)} overlay files unchanged)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())