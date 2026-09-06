#!/usr/bin/env python3
"""Apply narrow post-materialization hardening to Dashboard Intelligence 2.0."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "EmuleNextDashboardWnd.cpp"


def read_text() -> tuple[str, str]:
    raw = PATH.read_bytes()
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def main() -> int:
    text, encoding = read_text()
    changed = False

    old_switch = '''        switch (m_sortColumn) {
        case 0: compare = a.file->GetFileName().CompareNoCase(b.file->GetFileName()); break;
        case 1: compare = a.file->GetPercentCompleted() < b.file->GetPercentCompleted() ? -1 : (a.file->GetPercentCompleted() > b.file->GetPercentCompleted() ? 1 : 0); break;
        case 2: compare = a.signals.currentBytesPerSecond < b.signals.currentBytesPerSecond ? -1 : (a.signals.currentBytesPerSecond > b.signals.currentBytesPerSecond ? 1 : 0); break;
        case 3: compare = a.historicalBytesPerSecond < b.historicalBytesPerSecond ? -1 : (a.historicalBytesPerSecond > b.historicalBytesPerSecond ? 1 : 0); break;
        case 4: compare = a.signals.usableSources < b.signals.usableSources ? -1 : (a.signals.usableSources > b.signals.usableSources ? 1 : 0); break;
        case 5: compare = a.averageSourceQuality < b.averageSourceQuality ? -1 : (a.averageSourceQuality > b.averageSourceQuality ? 1 : 0); break;
        case 6: compare = a.health < b.health ? -1 : (a.health > b.health ? 1 : 0); break;
        case 8: compare = a.eta.seconds < b.eta.seconds ? -1 : (a.eta.seconds > b.eta.seconds ? 1 : 0); break;
        case 9: compare = a.a4afScore < b.a4afScore ? -1 : (a.a4afScore > b.a4afScore ? 1 : 0); break;
        case 10: compare = a.attention < b.attention ? -1 : (a.attention > b.attention ? 1 : 0); break;
        case 12: compare = static_cast<int>(a.schedulerApplied) - static_cast<int>(b.schedulerApplied); break;
        case 13: compare = a.lastInterventionAt < b.lastInterventionAt ? -1 : (a.lastInterventionAt > b.lastInterventionAt ? 1 : 0); break;
        case 14: compare = a.lastUsefulSourceAt < b.lastUsefulSourceAt ? -1 : (a.lastUsefulSourceAt > b.lastUsefulSourceAt ? 1 : 0); break;
        default: compare = a.attention < b.attention ? -1 : (a.attention > b.attention ? 1 : 0); break;
        }'''
    new_switch = '''        switch (m_sortColumn) {
        case 0: compare = a.file->GetFileName().CompareNoCase(b.file->GetFileName()); break;
        case 1: compare = a.file->GetPercentCompleted() < b.file->GetPercentCompleted() ? -1 : (a.file->GetPercentCompleted() > b.file->GetPercentCompleted() ? 1 : 0); break;
        case 2: compare = a.signals.currentBytesPerSecond < b.signals.currentBytesPerSecond ? -1 : (a.signals.currentBytesPerSecond > b.signals.currentBytesPerSecond ? 1 : 0); break;
        case 3: compare = a.historicalBytesPerSecond < b.historicalBytesPerSecond ? -1 : (a.historicalBytesPerSecond > b.historicalBytesPerSecond ? 1 : 0); break;
        case 4: compare = a.signals.usableSources < b.signals.usableSources ? -1 : (a.signals.usableSources > b.signals.usableSources ? 1 : 0); break;
        case 5: compare = a.averageSourceQuality < b.averageSourceQuality ? -1 : (a.averageSourceQuality > b.averageSourceQuality ? 1 : 0); break;
        case 6: compare = a.health < b.health ? -1 : (a.health > b.health ? 1 : 0); break;
        case 7: compare = StallText(a.stall).CompareNoCase(StallText(b.stall)); break;
        case 8:
            if (a.eta.known != b.eta.known) compare = a.eta.known ? 1 : -1;
            else compare = a.eta.seconds < b.eta.seconds ? -1 : (a.eta.seconds > b.eta.seconds ? 1 : 0);
            break;
        case 9: compare = a.a4afScore < b.a4afScore ? -1 : (a.a4afScore > b.a4afScore ? 1 : 0); break;
        case 10: compare = a.attention < b.attention ? -1 : (a.attention > b.attention ? 1 : 0); break;
        case 11: compare = static_cast<int>(a.schedulerAction) - static_cast<int>(b.schedulerAction); break;
        case 12: compare = static_cast<int>(a.schedulerApplied) - static_cast<int>(b.schedulerApplied); break;
        case 13: compare = a.lastInterventionAt < b.lastInterventionAt ? -1 : (a.lastInterventionAt > b.lastInterventionAt ? 1 : 0); break;
        case 14: compare = a.lastUsefulSourceAt < b.lastUsefulSourceAt ? -1 : (a.lastUsefulSourceAt > b.lastUsefulSourceAt ? 1 : 0); break;
        case 15:
            compare = a.strongSources < b.strongSources ? -1 : (a.strongSources > b.strongSources ? 1 : 0);
            if (compare == 0) compare = a.averageSourceQuality < b.averageSourceQuality ? -1 : (a.averageSourceQuality > b.averageSourceQuality ? 1 : 0);
            break;
        default: compare = 0; break;
        }'''
    if old_switch in text:
        text = text.replace(old_switch, new_switch, 1)
        changed = True
    elif "case 15:" not in text or "StallText(a.stall).CompareNoCase" not in text:
        raise SystemExit("Dashboard Intelligence 2 fixes: sortable-column anchor changed")

    old_selection = '''void CEmuleNextDashboardWnd::OnDownloadSelectionChanged(NMHDR*, LRESULT* result)
{
    m_persistedSummary.Empty();
    m_persistedHashValid = false;
    UpdateDetails();
    if (result != NULL) *result = 0;
}'''
    new_selection = '''void CEmuleNextDashboardWnd::OnDownloadSelectionChanged(NMHDR*, LRESULT* result)
{
    CPartFile* selected = GetSelectedFile();
    bool samePersistedFile = false;
    if (selected != NULL && m_persistedHashValid) {
        std::array<unsigned char, 16> hash;
        memcpy(hash.data(), selected->GetFileHash(), 16);
        samePersistedFile = hash == m_persistedHash;
    }
    if (!samePersistedFile) {
        m_persistedSummary.Empty();
        m_persistedHashValid = false;
    }
    UpdateDetails();
    if (result != NULL) *result = 0;
}'''
    if old_selection in text:
        text = text.replace(old_selection, new_selection, 1)
        changed = True
    elif "samePersistedFile" not in text:
        raise SystemExit("Dashboard Intelligence 2 fixes: selection-cache anchor changed")

    if changed:
        PATH.write_bytes(text.encode(encoding))
        print("Dashboard Intelligence 2.0 hardening materialized")
    else:
        print("Dashboard Intelligence 2.0 hardening already materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
