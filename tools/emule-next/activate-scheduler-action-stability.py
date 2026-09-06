#!/usr/bin/env python3
"""Add action-specific anti-flapping and preserve 30/120s outcome windows."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "EmuleNextSmartScheduler.cpp"


def read_text() -> tuple[str, str]:
    raw = PATH.read_bytes()
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def main() -> int:
    text, encoding = read_text()
    changed = False

    old_outcome = '''    {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_outcomes[key] = outcome;
    }
    m_telemetry.RecordOutcomeBaseline(file->GetFileHash(), file->GetFileName(), action,
        now, outcome.baselineBytesPerSecond, outcome.baselineUsableSources);'''
    new_outcome = '''    bool accepted = false;
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        const std::map<Key, EmuleNextInterventionOutcome>::const_iterator existing = m_outcomes.find(key);
        // Preserve an active measurement window long enough to collect +120s.
        // New interventions may still occur, but they do not erase the outcome
        // currently being evaluated.
        if (existing == m_outcomes.end() || existing->second.measured120
            || existing->second.startedAt == 0 || now < existing->second.startedAt
            || now - existing->second.startedAt >= 180) {
            m_outcomes[key] = outcome;
            accepted = true;
        }
    }
    if (accepted)
        m_telemetry.RecordOutcomeBaseline(file->GetFileHash(), file->GetFileName(), action,
            now, outcome.baselineBytesPerSecond, outcome.baselineUsableSources);'''
    if old_outcome in text:
        text = text.replace(old_outcome, new_outcome, 1)
        changed = True
    elif "Preserve an active measurement window" not in text:
        raise SystemExit("Scheduler stability: BeginOutcome anchor changed")

    old_mark = '''    const uint64 now = static_cast<uint64>(time(NULL));
    bool changed = false;
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        std::map<Key, EmuleNextSchedulerSnapshot>::iterator it = m_snapshots.find(key);
        if (it != m_snapshots.end()) {
            if (!it->second.applied)
                changed = true;
            it->second.applied = true;
            it->second.lastInterventionAt = now;
            if (action == ENSA_A4AF_PREFER)
                it->second.lastA4AFAt = now;
            else if (action == ENSA_RARE_PART_PROTECT)
                it->second.lastRarePartAt = now;
            else if (action == ENSA_DISCOVERY_BOOST)
                it->second.lastDiscoveryAt = now;
        }
    }
    if (changed) {
        BeginOutcome(file, action, now);
        if (theApp.GetProfileInt(_T("eMule Next"), _T("SmartTelemetry"), 1) != 0)
            m_telemetry.MarkAppliedIntervention(file->GetFileHash(), file->GetFileName());
    }'''
    new_mark = '''    const uint64 now = static_cast<uint64>(time(NULL));
    const uint32 cooldown = LoadSettings().interventionCooldownSeconds;
    bool reportIntervention = false;
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        std::map<Key, EmuleNextSchedulerSnapshot>::iterator it = m_snapshots.find(key);
        if (it != m_snapshots.end()) {
            uint64 previousActionAt = 0;
            if (action == ENSA_A4AF_PREFER)
                previousActionAt = it->second.lastA4AFAt;
            else if (action == ENSA_RARE_PART_PROTECT)
                previousActionAt = it->second.lastRarePartAt;
            else if (action == ENSA_DISCOVERY_BOOST)
                previousActionAt = it->second.lastDiscoveryAt;
            reportIntervention = previousActionAt == 0 || now < previousActionAt
                || now - previousActionAt >= cooldown;
            it->second.applied = true;
            if (reportIntervention) {
                it->second.lastInterventionAt = now;
                if (action == ENSA_A4AF_PREFER)
                    it->second.lastA4AFAt = now;
                else if (action == ENSA_RARE_PART_PROTECT)
                    it->second.lastRarePartAt = now;
                else if (action == ENSA_DISCOVERY_BOOST)
                    it->second.lastDiscoveryAt = now;
            }
        }
    }
    if (reportIntervention) {
        BeginOutcome(file, action, now);
        if (theApp.GetProfileInt(_T("eMule Next"), _T("SmartTelemetry"), 1) != 0)
            m_telemetry.MarkAppliedIntervention(file->GetFileHash(), file->GetFileName());
    }'''
    if old_mark in text:
        text = text.replace(old_mark, new_mark, 1)
        changed = True
    elif "previousActionAt" not in text:
        raise SystemExit("Scheduler stability: MarkApplied anchor changed")

    a4af_anchor = '''    const uint32 currentScore = hasCurrent ? current.decision.a4afScore : 0;
    const uint32 currentAttention = hasCurrent ? current.decision.attention : 0;

    if (!legacyPreference'''
    a4af_new = '''    const uint32 currentScore = hasCurrent ? current.decision.a4afScore : 0;
    const uint32 currentAttention = hasCurrent ? current.decision.attention : 0;

    const uint64 now = static_cast<uint64>(time(NULL));
    const uint32 cooldown = LoadSettings().interventionCooldownSeconds;
    if (candidate.lastA4AFAt != 0 && now >= candidate.lastA4AFAt
        && now - candidate.lastA4AFAt < cooldown)
        return legacyPreference;

    if (!legacyPreference'''
    if a4af_anchor in text:
        text = text.replace(a4af_anchor, a4af_new, 1)
        changed = True
    elif "now - candidate.lastA4AFAt < cooldown" not in text:
        raise SystemExit("Scheduler stability: A4AF cooldown anchor changed")

    if changed:
        PATH.write_bytes(text.encode(encoding))
        print("Smart Scheduler action stability materialized")
    else:
        print("Smart Scheduler action stability already materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
