#!/usr/bin/env python3
"""Normalize activation-stage source newlines to LF without decoding text.

Windows Git checkouts commonly materialize CRLF even when repository blobs use
LF. Several source activators intentionally match multiline C++ fragments. To
make those matches deterministic, the isolated activation stage is normalized
before feature activation. Only the staging copy is touched; the real checkout
is never modified.
"""
from __future__ import annotations

import argparse
import pathlib

TEXT_SUFFIXES = {
    ".c", ".cc", ".cpp", ".cxx",
    ".h", ".hh", ".hpp", ".hxx", ".inl",
    ".rc", ".rc2",
    ".vcxproj", ".filters", ".props", ".targets",
}


def normalize_tree(root: pathlib.Path) -> tuple[int, int]:
    files_seen = 0
    files_changed = 0
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        files_seen += 1
        raw = path.read_bytes()
        normalized = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        if normalized != raw:
            path.write_bytes(normalized)
            files_changed += 1
    return files_seen, files_changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=pathlib.Path)
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        raise SystemExit(f"activation newline normalization: directory missing: {root}")

    files_seen, files_changed = normalize_tree(root)

    # Fail fast if a supported text file still contains CR bytes. This guards
    # the exact class of Windows-only multiline-anchor failures this step fixes.
    leftovers: list[pathlib.Path] = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES and b"\r" in path.read_bytes():
            leftovers.append(path)
            if len(leftovers) >= 10:
                break
    if leftovers:
        joined = ", ".join(str(path.relative_to(root)) for path in leftovers)
        raise SystemExit(f"activation newline normalization incomplete: {joined}")

    print(
        f"Activation-stage newlines normalized: {files_changed}/{files_seen} source/project files changed to LF"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
