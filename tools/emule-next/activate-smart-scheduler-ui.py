#!/usr/bin/env python3
"""Idempotently surface Smart Scheduler runtime state in the Dashboard.

This activator deliberately does not introduce database reads. Dashboard reads
only scheduler snapshots and the in-memory history mirror; SQLite persistence
runs on the dedicated history worker.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "EmuleNextDashboardWnd.cpp"


def read_text(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def main() -> int:
    text, encoding = read_text(PATH)
    changed = False

    include = '#include "EmuleNextSmartScheduler.h"'
    if include not in text:
        anchor = '#include "DownloadIntelligence.h"'
        if anchor not in text:
            raise SystemExit("Smart Scheduler UI: Dashboard include anchor missing")
        text = text.replace(anchor, anchor + "\n" + include, 1)
        changed = True

    if 'm_downloads.InsertColumn(14, _T("Scheduler")' not in text:
        anchor = '    m_downloads.InsertColumn(13, _T("Attention"), LVCFMT_RIGHT, 75);'
        addition = anchor + '\n    m_downloads.InsertColumn(14, _T("Scheduler"), LVCFMT_LEFT, 110);\n    m_downloads.InsertColumn(15, _T("Applied"), LVCFMT_LEFT, 62);\n    m_downloads.InsertColumn(16, _T("Hist. rate"), LVCFMT_RIGHT, 82);'
        if anchor not in text:
            raise SystemExit("Smart Scheduler UI: Dashboard column anchor missing")
        text = text.replace(anchor, addition, 1)
        changed = True
    elif 'm_downloads.InsertColumn(16, _T("Hist. rate")' not in text:
        anchor = '    m_downloads.InsertColumn(15, _T("Applied"), LVCFMT_LEFT, 62);'
        if anchor not in text:
            raise SystemExit("Smart Scheduler UI: historical-rate column anchor missing")
        text = text.replace(anchor, anchor + '\n    m_downloads.InsertColumn(16, _T("Hist. rate"), LVCFMT_RIGHT, 82);', 1)
        changed = True

    row_anchor = '        text.Format(_T("%u"), rowData.attention);\n        m_downloads.SetItemText(row, 13, text);'
    if 'EmuleNextSchedulerSnapshot schedulerSnapshot;' not in text:
        block = row_anchor + '\n\n        EmuleNextSchedulerSnapshot schedulerSnapshot;\n        if (theEmuleNextScheduler.GetSnapshot(file->GetFileHash(), schedulerSnapshot)) {\n            m_downloads.SetItemText(row, 14, CDownloadIntelligence::SchedulingActionText(schedulerSnapshot.decision.primaryAction));\n            m_downloads.SetItemText(row, 15, schedulerSnapshot.applied ? _T("yes") : _T("no"));\n        } else {\n            m_downloads.SetItemText(row, 14, _T("pending"));\n            m_downloads.SetItemText(row, 15, _T("--"));\n        }\n        EmuleNextFileHistory history;\n        if (theEmuleNextScheduler.History().GetHistory(file->GetFileHash(), history)) {\n            text.Format(_T("%.1f KB/s"), history.ewmaBytesPerSecond / 1024.0);\n            m_downloads.SetItemText(row, 16, text);\n        } else {\n            m_downloads.SetItemText(row, 16, _T("--"));\n        }'
        if row_anchor not in text:
            raise SystemExit("Smart Scheduler UI: Dashboard row anchor missing")
        text = text.replace(row_anchor, block, 1)
        changed = True
    elif 'theEmuleNextScheduler.History().GetHistory(file->GetFileHash(), history)' not in text:
        anchor = '            m_downloads.SetItemText(row, 15, _T("--"));\n        }'
        history_block = anchor + '\n        EmuleNextFileHistory history;\n        if (theEmuleNextScheduler.History().GetHistory(file->GetFileHash(), history)) {\n            text.Format(_T("%.1f KB/s"), history.ewmaBytesPerSecond / 1024.0);\n            m_downloads.SetItemText(row, 16, text);\n        } else {\n            m_downloads.SetItemText(row, 16, _T("--"));\n        }'
        if anchor not in text:
            raise SystemExit("Smart Scheduler UI: scheduler row block changed unexpectedly")
        text = text.replace(anchor, history_block, 1)
        changed = True

    summary_anchor = '    m_summary.SetWindowText(summary);'
    if 'theEmuleNextScheduler.GetRuntimeStatusText()' not in text:
        block = '    summary += _T("   |   Scheduler: ");\n    summary += theEmuleNextScheduler.GetRuntimeStatusText();\n' + summary_anchor
        if summary_anchor not in text:
            raise SystemExit("Smart Scheduler UI: Dashboard summary anchor missing")
        text = text.replace(summary_anchor, block, 1)
        changed = True

    details_anchor = '    CString details;\n    details.Format('
    if 'CString schedulerDetail;' not in text:
        prefix = '    CString schedulerDetail;\n    EmuleNextSchedulerSnapshot schedulerSnapshot;\n    if (theEmuleNextScheduler.GetSnapshot(file->GetFileHash(), schedulerSnapshot)) {\n        schedulerDetail.Format(_T("Scheduler: %s   Applied: %s   Reason: %s\\r\\n"),\n            (LPCTSTR)CDownloadIntelligence::SchedulingActionText(schedulerSnapshot.decision.primaryAction),\n            schedulerSnapshot.applied ? _T("yes") : _T("no"),\n            schedulerSnapshot.decision.reason.IsEmpty() ? _T("--") : (LPCTSTR)schedulerSnapshot.decision.reason);\n    } else {\n        schedulerDetail = _T("Scheduler: pending first analysis\\r\\n");\n    }\n    EmuleNextFileHistory fileHistory;\n    if (theEmuleNextScheduler.History().GetHistory(file->GetFileHash(), fileHistory)) {\n        const uint64 nowHistory = static_cast<uint64>(time(NULL));\n        const uint64 age = nowHistory >= fileHistory.lastObserved ? nowHistory - fileHistory.lastObserved : 0;\n        CString historyDetail;\n        historyDetail.Format(_T("History: %.1f KB/s EWMA   Samples: %u   Age: %llus   Store: %s\\r\\n"),\n            fileHistory.ewmaBytesPerSecond / 1024.0, fileHistory.samples, age,\n            theEmuleNextScheduler.History().PersistenceReady() ? _T("persistent") : _T("memory"));\n        schedulerDetail += historyDetail;\n    }\n\n' + details_anchor
        if details_anchor not in text:
            raise SystemExit("Smart Scheduler UI: Dashboard details anchor missing")
        text = text.replace(details_anchor, prefix, 1)
        set_anchor = '    m_details.SetWindowText(details);'
        if set_anchor not in text:
            raise SystemExit("Smart Scheduler UI: Dashboard detail output anchor missing")
        text = text.replace(set_anchor, '    details += _T("\\r\\n");\n    details += schedulerDetail;\n' + set_anchor, 1)
        changed = True

    if changed:
        PATH.write_bytes(text.encode(encoding))
        print("Smart Scheduler Dashboard runtime UI materialized")
    else:
        print("Smart Scheduler Dashboard runtime UI already materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
