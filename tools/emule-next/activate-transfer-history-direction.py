#!/usr/bin/env python3
"""Show upload/download direction and split traffic totals in Download Intelligence."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "DownloadIntelligenceWnd.cpp"


def load() -> tuple[str, str]:
    raw = PATH.read_bytes()
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    newline = "\r\n" if crlf >= lf and crlf else "\n"
    return raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n"), newline


def save(text: str, newline: str) -> None:
    if newline != "\n":
        text = text.replace("\n", newline)
    PATH.write_bytes(text.encode("latin-1"))


def main() -> int:
    text, newline = load()

    old_columns = '''    m_transfers.InsertColumn(0, _T("Finished"), LVCFMT_LEFT, 135);\n    m_transfers.InsertColumn(1, _T("File"), LVCFMT_LEFT, 260);\n    m_transfers.InsertColumn(2, _T("Network name"), LVCFMT_LEFT, 145);\n    m_transfers.InsertColumn(3, _T("Alias"), LVCFMT_LEFT, 125);\n    m_transfers.InsertColumn(4, _T("Transferred"), LVCFMT_RIGHT, 100);\n    m_transfers.InsertColumn(5, _T("Average"), LVCFMT_RIGHT, 100);\n    m_transfers.InsertColumn(6, _T("Status"), LVCFMT_LEFT, 80);\n    m_transfers.InsertColumn(7, _T("Result"), LVCFMT_LEFT, 220);\n'''
    new_columns = '''    m_transfers.InsertColumn(0, _T("Finished"), LVCFMT_LEFT, 135);\n    m_transfers.InsertColumn(1, _T("Direction"), LVCFMT_LEFT, 75);\n    m_transfers.InsertColumn(2, _T("File"), LVCFMT_LEFT, 245);\n    m_transfers.InsertColumn(3, _T("Network name"), LVCFMT_LEFT, 140);\n    m_transfers.InsertColumn(4, _T("Alias"), LVCFMT_LEFT, 120);\n    m_transfers.InsertColumn(5, _T("Transferred"), LVCFMT_RIGHT, 100);\n    m_transfers.InsertColumn(6, _T("Average"), LVCFMT_RIGHT, 100);\n    m_transfers.InsertColumn(7, _T("Status"), LVCFMT_LEFT, 80);\n    m_transfers.InsertColumn(8, _T("Result"), LVCFMT_LEFT, 210);\n'''
    if 'm_transfers.InsertColumn(1, _T("Direction")' not in text:
        if old_columns not in text:
            raise RuntimeError("Transfer history column block not found")
        text = text.replace(old_columns, new_columns, 1)

    old_populate = '''        const int row = m_transfers.InsertItem(static_cast<int>(i), DateText(item.finishedAt));\n        m_transfers.SetItemText(row, 1, file);\n        m_transfers.SetItemText(row, 2, user);\n        m_transfers.SetItemText(row, 3, alias);\n        m_transfers.SetItemText(row, 4, CastItoXBytes(item.bytesTransferred, false, false, 1));\n        CString speed;\n        speed.Format(_T("%s/s"), (LPCTSTR)CastItoXBytes(item.averageBytesPerSecond, false, false, 1));\n        m_transfers.SetItemText(row, 5, speed);\n        m_transfers.SetItemText(row, 6, item.successful ? _T("Success") : _T("Failed"));\n        m_transfers.SetItemText(row, 7, CString(item.result));\n'''
    new_populate = '''        const int row = m_transfers.InsertItem(static_cast<int>(i), DateText(item.finishedAt));\n        CString direction(item.direction);\n        if (direction.IsEmpty())\n            direction = _T("unknown");\n        m_transfers.SetItemText(row, 1, direction);\n        m_transfers.SetItemText(row, 2, file);\n        m_transfers.SetItemText(row, 3, user);\n        m_transfers.SetItemText(row, 4, alias);\n        m_transfers.SetItemText(row, 5, CastItoXBytes(item.bytesTransferred, false, false, 1));\n        CString speed;\n        speed.Format(_T("%s/s"), (LPCTSTR)CastItoXBytes(item.averageBytesPerSecond, false, false, 1));\n        m_transfers.SetItemText(row, 6, speed);\n        m_transfers.SetItemText(row, 7, item.successful ? _T("Success") : _T("Failed"));\n        m_transfers.SetItemText(row, 8, CString(item.result));\n'''
    if 'm_transfers.SetItemText(row, 1, direction);' not in text:
        if old_populate not in text:
            raise RuntimeError("Transfer history populate block not found")
        text = text.replace(old_populate, new_populate, 1)

    start = text.find('void CDownloadIntelligenceWnd::UpdateSummary()\n{')
    end = text.find('\nCString CDownloadIntelligenceWnd::DateText', start)
    if start < 0 or end < 0:
        raise RuntimeError("Download Intelligence summary function not found")
    if 'Download: %s   Upload: %s' not in text[start:end]:
        summary = '''void CDownloadIntelligenceWnd::UpdateSummary()\n{\n    uint64 downloadBytes = 0;\n    uint64 uploadBytes = 0;\n    uint64 weightedSpeedBytes = 0;\n    uint64 weightedTransferred = 0;\n    size_t successful = 0;\n    size_t downloads = 0;\n    size_t uploads = 0;\n    for (size_t i = 0; i < m_rows.size(); ++i) {\n        const EmuleNextTransferHistoryRecord& item = m_rows[i];\n        if (item.direction.CompareNoCase(L"upload") == 0) {\n            ++uploads;\n            uploadBytes += item.bytesTransferred;\n        }\n        else {\n            ++downloads;\n            downloadBytes += item.bytesTransferred;\n        }\n        if (item.successful)\n            ++successful;\n        if (item.bytesTransferred > 0 && item.averageBytesPerSecond > 0) {\n            weightedSpeedBytes += static_cast<uint64>(item.averageBytesPerSecond) * item.bytesTransferred;\n            weightedTransferred += item.bytesTransferred;\n        }\n    }\n    const uint64 average = weightedTransferred > 0 ? weightedSpeedBytes / weightedTransferred : 0;\n    CString text;\n    text.Format(_T("Recent: %u (down %u / up %u)   Success: %u   Sources: %u   Download: %s   Upload: %s   Avg: %s/s"),\n        static_cast<unsigned>(m_rows.size()), static_cast<unsigned>(downloads), static_cast<unsigned>(uploads),\n        static_cast<unsigned>(successful), static_cast<unsigned>(m_sourceRows.size()),\n        (LPCTSTR)CastItoXBytes(downloadBytes, false, false, 1),\n        (LPCTSTR)CastItoXBytes(uploadBytes, false, false, 1),\n        (LPCTSTR)CastItoXBytes(average, false, false, 1));\n    m_summary.SetWindowText(text);\n}\n'''
        text = text[:start] + summary + text[end:]

    save(text, newline)
    print("eMule Next transfer history direction and traffic summary active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
