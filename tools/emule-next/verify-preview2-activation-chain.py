#!/usr/bin/env python3
'''Verify that clean local builds always execute the final Preview 2 layer.'''
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent


def read(path: pathlib.Path) -> str:
    if not path.exists():
        raise SystemExit(f"Preview2 activation-chain verification: missing {path.name}")
    return path.read_text(encoding="utf-8-sig", errors="ignore")


def main() -> int:
    build = read(ROOT / "build-local.ps1")
    features = read(HERE / "activate-features.py")
    preview = read(HERE / "activate-preview2.py")

    for marker in (
        'python (Join-Path $tools "activate-features.py")',
        'Preparing clean eMule Next activation overlay',
        'Sync-ActivatedOverlay $StageSource $SourceDir',
    ):
        if marker not in build:
            raise SystemExit(f"Preview2 activation-chain verification: build path missing {marker}")

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

    print("eMule Next Preview 2 clean activation-chain verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
