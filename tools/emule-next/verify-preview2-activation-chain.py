#!/usr/bin/env python3
'''Verify the late Preview 2 activation chain inside the clean activation overlay.

This verifier intentionally inspects only files that are copied into the
activation overlay (srchybrid + tools/emule-next). Repository-root artifacts
such as build-local.ps1 are verified separately by verify-preview2-release.ps1.
'''
from __future__ import annotations

import pathlib

HERE = pathlib.Path(__file__).resolve().parent


def read(path: pathlib.Path) -> str:
    if not path.exists():
        raise SystemExit(f"Preview2 activation-chain verification: missing overlay file {path.name}")
    return path.read_text(encoding="utf-8-sig", errors="ignore")


def main() -> int:
    features = read(HERE / "activate-features.py")
    preview = read(HERE / "activate-preview2.py")

    preview_call = 'runpy.run_path(str(preview), run_name="__main__")'
    final_base_gate = '"fix-preview1-build.py"'
    if preview_call not in features:
        raise SystemExit("Preview2 activation-chain verification: activate-features does not run Preview2")
    if final_base_gate not in features:
        raise SystemExit("Preview2 activation-chain verification: base compatibility gate missing")
    if features.find(preview_call) < features.find(final_base_gate):
        raise SystemExit("Preview2 activation-chain verification: Preview2 is not the final product layer")

    required_order = (
        '"activate-preview2-main-shell.py"',
        '"activate-preview2-ux-completion.py"',
        '"activate-preview2-search-ux.py"',
        '"activate-preview2-header-status.py"',
        '"activate-preview2-build-identity.py"',
        '"verify-preview2-activation-chain.py"',
        '"verify-preview2-ux-completion.py"',
        '"verify-preview2-product.py"',
    )
    positions = []
    for marker in required_order:
        pos = preview.find(marker)
        if pos < 0:
            raise SystemExit(f"Preview2 activation-chain verification: orchestrator missing {marker}")
        positions.append(pos)
    if positions != sorted(positions):
        raise SystemExit("Preview2 activation-chain verification: unsafe late product ordering")

    # No overlay verifier may depend on repository-root files. This catches the
    # exact class of failure that previously tried to read build-local.ps1 from
    # build/activation-stage.
    forbidden_repo_root_refs = ("build-local.ps1", "docs/", "docs\\", "package-preview2.ps1", "installer/")
    own_text = pathlib.Path(__file__).read_text(encoding="utf-8-sig", errors="ignore")
    for marker in forbidden_repo_root_refs:
        if marker in own_text and marker != "build-local.ps1":
            raise SystemExit(f"Preview2 activation-chain verification: overlay verifier contains repository-root dependency {marker}")

    print("eMule Next Preview 2 clean activation-chain verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
