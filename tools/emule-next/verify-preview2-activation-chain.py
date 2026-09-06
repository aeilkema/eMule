#!/usr/bin/env python3
'''Verify the late Preview 2 activation chain inside the clean activation overlay.

This verifier intentionally inspects only files copied into the activation
overlay. Repository-level build and release scripts are verified separately by
the repository-level release verifier.

The gate is structural: it parses Python ASTs instead of depending on variable
names, whitespace or exact source formatting.
'''
from __future__ import annotations

import ast
import pathlib

HERE = pathlib.Path(__file__).resolve().parent


def read(path: pathlib.Path) -> str:
    if not path.exists():
        raise SystemExit(f"Preview2 activation-chain verification: missing overlay file {path.name}")
    return path.read_text(encoding="utf-8-sig", errors="ignore")


def parse(path: pathlib.Path) -> ast.AST:
    text = read(path)
    try:
        return ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        raise SystemExit(
            f"Preview2 activation-chain verification: syntax error in {path.name} "
            f"line {exc.lineno}: {exc.msg}"
        )


def is_name(node: ast.AST, name: str) -> bool:
    return isinstance(node, ast.Name) and node.id == name


def is_string_constant(node: ast.AST, value: str) -> bool:
    return isinstance(node, ast.Constant) and node.value == value


def preview2_call_line(tree: ast.AST) -> int:
    preview_vars: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if not isinstance(value, ast.BinOp) or not isinstance(value.op, ast.Div):
            continue
        if not (is_name(value.left, "HERE") and is_string_constant(value.right, "activate-preview2.py")):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if isinstance(target, ast.Name):
                preview_vars.add(target.id)
    if not preview_vars:
        raise SystemExit("Preview2 activation-chain verification: activate-features does not resolve activate-preview2.py")

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "run_path" and is_name(func.value, "runpy")):
            continue
        if not node.args:
            continue
        first = node.args[0]
        if not (
            isinstance(first, ast.Call) and is_name(first.func, "str") and len(first.args) == 1
            and isinstance(first.args[0], ast.Name) and first.args[0].id in preview_vars
        ):
            continue
        if any(keyword.arg == "run_name" and is_string_constant(keyword.value, "__main__") for keyword in node.keywords):
            return node.lineno
    raise SystemExit("Preview2 activation-chain verification: activate-features does not structurally execute Preview2")


def base_gate_line(tree: ast.AST) -> int:
    lines = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Constant) and node.value == "fix-preview1-build.py"]
    if not lines:
        raise SystemExit("Preview2 activation-chain verification: base compatibility gate missing")
    return max(lines)


def preview2_steps(tree: ast.AST) -> list[str]:
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(target, ast.Name) and target.id == "PREVIEW2_STEPS" for target in targets):
            continue
        value = node.value
        if not isinstance(value, (ast.Tuple, ast.List)):
            break
        return [item.value for item in value.elts if isinstance(item, ast.Constant) and isinstance(item.value, str)]
    raise SystemExit("Preview2 activation-chain verification: PREVIEW2_STEPS declaration unavailable")


def main() -> int:
    features_tree = parse(HERE / "activate-features.py")
    preview_tree = parse(HERE / "activate-preview2.py")

    if preview2_call_line(features_tree) <= base_gate_line(features_tree):
        raise SystemExit("Preview2 activation-chain verification: Preview2 is not the final product layer")

    steps = preview2_steps(preview_tree)
    required_order = (
        "activate-preview2-main-shell.py",
        "activate-preview2-ux-completion.py",
        "activate-preview2-settings-complete.py",
        "activate-preview2-settings-complete-hardening.py",
        "activate-preview2-search-ux.py",
        "activate-preview2-header-status.py",
        "activate-preview2-legacy-theme-routing.py",
        "activate-preview2-theme-coverage.py",
        "activate-preview2-warning-cleanup.py",
        "activate-preview2-build-identity.py",
        "verify-preview2-activation-chain.py",
        "verify-preview2-warning-cleanup.py",
        "verify-preview2-settings-theme.py",
        "verify-preview2-ux-completion.py",
        "verify-preview2-product.py",
    )
    positions: list[int] = []
    for marker in required_order:
        if marker not in steps:
            raise SystemExit(f"Preview2 activation-chain verification: orchestrator missing {marker}")
        positions.append(steps.index(marker))
    if positions != sorted(positions):
        raise SystemExit("Preview2 activation-chain verification: unsafe late product ordering")

    print("eMule Next Preview 2 clean activation-chain verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
