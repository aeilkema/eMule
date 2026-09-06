#!/usr/bin/env python3
"""Ensure canonical transfer insights use bounded live source-quality sampling."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "EmuleNextTransferInsights.cpp"


def main() -> int:
    if not PATH.exists():
        raise SystemExit("Transfer insights bounds: source missing")
    text = PATH.read_bytes().decode("latin-1", errors="ignore")
    required = (
        "kMaxSourceQualitySamples = 32",
        "kMaxPartChecksPerSource = 256",
        "kUsefulPartsSaturation = 8",
        "sampled < kMaxSourceQualitySamples",
        "source.usefulPartCount < kUsefulPartsSaturation",
        "CDownloadIntelligence::SourceQuality(source)",
        "insight.bestSourceQuality = BuildBoundedBestSourceQuality(file);",
        "p.bestSourceQuality = static_cast<double>(insight.bestSourceQuality);",
    )
    for marker in required:
        if marker not in text:
            raise SystemExit(f"Transfer insights bounds: missing {marker}")
    if "bestSourceQuality(500)" in text or "p.bestSourceQuality = 500.0" in text:
        raise SystemExit("Transfer insights bounds: fixed source-quality placeholder remains")
    print("Bounded live source-quality verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
