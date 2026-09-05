#!/usr/bin/env python3
"""Static integrity checks for the eMule Next Smart Scheduling tranche."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"

CHECKS = {
    "DownloadIntelligence.h": (
        "enum EmuleNextSchedulingMode",
        "ENSM_ANALYSIS_ONLY",
        "ENSM_AUTOMATIC",
        "struct EmuleNextSchedulingSettings",
        "struct EmuleNextSchedulingDecision",
        "EvaluateScheduling(",
        "ShouldApplyDecision(",
    ),
    "DownloadIntelligence.cpp": (
        "CDownloadIntelligence::EvaluateScheduling",
        "CDownloadIntelligence::ShouldApplyDecision",
        "ENSA_A4AF_PREFER",
        "ENSA_RARE_PART_PROTECT",
        "interventionCooldownSeconds",
    ),
    "EmuleNextSettingsWnd.h": (
        "m_schedulerMode",
        "m_sourceDiscoveryIntelligence",
        "m_a4afIntelligence",
        "m_rarePartIntelligence",
        "m_etaHealthDisplay",
    ),
    "EmuleNextSettingsWnd.cpp": (
        'SmartSchedulingMode',
        'SmartSourceDiscovery',
        'SmartA4AF',
        'SmartRareParts',
        'SmartEtaHealthDisplay',
        'Analysis only (recommended)',
        'Automatic intervention',
    ),
}

missing: list[str] = []
for name, markers in CHECKS.items():
    path = SRC / name
    if not path.exists():
        missing.append(f"{name}: file missing")
        continue
    text = path.read_bytes().decode("latin-1", errors="ignore")
    for marker in markers:
        if marker not in text:
            missing.append(f"{name}: missing {marker!r}")

if missing:
    print("eMule Next Smart Scheduling verification FAILED")
    for item in missing:
        print(f"  - {item}")
    raise SystemExit(2)

print("eMule Next Smart Scheduling verification passed")
