//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#include "stdafx.h"
#include "EmuleNextDashboardWnd.h"

#include "emule.h"
#include "PartFile.h"
#include "DownloadQueue.h"
#include "UploadQueue.h"
#include "UpDownClient.h"
#include "DownloadIntelligence.h"
#include "EmuleNextTheme.h"
#include "OtherFunctions.h"

namespace
{
    enum
    {
        IDC_EN_DASH_SUMMARY = 0x7E40,
        IDC_EN_DASH_DOWNLOADS
    };

    const UINT_PTR TIMER_EN_DASH_REFRESH = 0x566;

    EmuleNextFileSignals BuildSignals(const CPartFile* file)
    {
        EmuleNextFileSignals signals;
        if (file == NULL)
            return signals;

        signals.totalSources = file->GetSourceCount();
        const int validSources = file->GetValidSourcesCount();
        signals.usableSources = validSources > 0 ? static_cast<uint32>(validSources) : 0;
        signals.queuedSources = file->GetSrcStatisticsValue(DS_ONQUEUE);
        signals.connectionFailures =
            file->GetSrcStatisticsValue(DS_ERROR)
            + file->GetSrcStatisticsValue(DS_TOOMANYCONNS)
            + file->GetSrcStatisticsValue(DS_TOOMANYCONNSKAD);
        signals.a4afCandidates = file->GetSrcA4AFCount();
        signals.currentBytesPerSecond = static_cast<double>(file->GetDatarate());
        signals.completionRatio = static_cast<double>(file->GetPercentCompleted()) / 100.0;
        signals.hashing = file->GetStatus() == PS_HASHING
            || file->GetStatus() == PS_WAITINGFORHASH
            || file->GetFileOp() == PFOP_HASHING;
        signals.highPriority = file->GetDownPriority() == PR_HIGH
            || file->GetDownPriority() == PR_VERYHIGH;

        // We have not wired per-cycle Kad discovery telemetry into the file yet.
        // Use 1 here so a zero-source file is reported as "No sources" instead
        // of incorrectly claiming that Kad itself failed.
        signals.kadResultsLastCycle = 1;

        const UINT partCount = file->GetPartCount();
        for (UINT part = 0; part < partCount; ++part) {
            if (file->IsComplete(part))
                continue;
            ++signals.neededParts;
            if (file->GetPartSourceFrequency(part) <= 2)
                ++signals.rareNeededParts;
        }
        return signals;
    }

    CString StallText(EmuleNextStallReason reason)
    {
        switch (reason) {
        case ENSR_NONE: return _T("Healthy");
        case ENSR_NO_SOURCES: return _T("No sources");
        case ENSR_NO_NEEDED_PARTS: return _T("No needed parts");
        case ENSR_ALL_REMOTE_QUEUED: return _T("All remote queued");
        case ENSR_RARE_PARTS: return _T("Rare parts");
        case ENSR_CONNECTION_FAILURE: return _T("Connection failures");
        case ENSR_KAD_DISCOVERY_FAILURE: return _T("Kad discovery");
        case ENSR_DISK_LIMITED: return _T("Disk limited");
        case ENSR_HASHING: return _T("Hashing");
        case ENSR_A4AF_CONFLICT: return _T("A4AF conflict");
        default: return _T("Unknown");
        }
    }

    CString EtaText(const EmuleNextEta& eta)
    {
        if (!eta.known)
            return _T("--");
        uint64 seconds = eta.seconds;
        const uint64 days = seconds / 86400ui64;
        seconds %= 86400ui64;
        const uint64 hours = seconds / 3600ui64;
        seconds %= 3600ui64;
        const uint64 minutes = seconds / 60ui64;
        CString result;
        if (days > 0)
            result.Format(_T("%llud %02lluh"), days, hours);
        else if (hours > 0)
            result.Format(_T("%lluh %02llum"), hours, minutes);
        else
            result.Format(_T("%llum"), minutes);
        return result;
    }
}

BEGIN_MESSAGE_MAP(CEmuleNextDashboardWnd, CWnd)
    ON_WM_CREATE()
    ON_WM_SIZE()
    ON_WM_TIMER()
    ON_WM_ERASEBKGND()
    ON_WM_CTLCOLOR()
END_MESSAGE_MAP()

CEmuleNextDashboardWnd::CEmuleNextDashboardWnd()
    : m_refreshTimer(0)
{
}

CEmuleNextDashboardWnd::~CEmuleNextDashboardWnd()
{
}

bool CEmuleNextDashboardWnd::Create(CWnd* parent)
{
    if (parent == NULL)
        return false;
    const CString className = AfxRegisterWndClass(CS_DBLCLKS,
        ::LoadCursor(NULL, IDC_ARROW),
        reinterpret_cast<HBRUSH>(COLOR_WINDOW + 1), NULL);
    CRect empty(0, 0, 0, 0);
    return CWnd::CreateEx(0, className, _T("eMule Next Dashboard"),
        WS_CHILD | WS_CLIPCHILDREN | WS_CLIPSIBLINGS,
        empty, parent, 0) != FALSE;
}

int CEmuleNextDashboardWnd::OnCreate(LPCREATESTRUCT createStruct)
{
    if (CWnd::OnCreate(createStruct) == -1)
        return -1;

    m_darkBrush.CreateSolidBrush(CEmuleNextTheme::BackgroundColor());
    CRect empty(0, 0, 0, 0);
    if (!m_summary.Create(_T("eMule Next Dashboard"), WS_CHILD | WS_VISIBLE | SS_LEFT,
            empty, this, IDC_EN_DASH_SUMMARY)
        || !m_downloads.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | LVS_REPORT | LVS_SINGLESEL | LVS_SHOWSELALWAYS,
            empty, this, IDC_EN_DASH_DOWNLOADS)) {
        return -1;
    }

    CFont* font = CFont::FromHandle(static_cast<HFONT>(::GetStockObject(DEFAULT_GUI_FONT)));
    m_summary.SetFont(font);
    m_downloads.SetFont(font);
    m_downloads.SetExtendedStyle(LVS_EX_FULLROWSELECT | LVS_EX_DOUBLEBUFFER | LVS_EX_GRIDLINES);
    m_downloads.InsertColumn(0, _T("File"), LVCFMT_LEFT, 300);
    m_downloads.InsertColumn(1, _T("Progress"), LVCFMT_RIGHT, 80);
    m_downloads.InsertColumn(2, _T("Speed"), LVCFMT_RIGHT, 90);
    m_downloads.InsertColumn(3, _T("Sources"), LVCFMT_RIGHT, 90);
    m_downloads.InsertColumn(4, _T("Health"), LVCFMT_RIGHT, 75);
    m_downloads.InsertColumn(5, _T("Diagnosis"), LVCFMT_LEFT, 150);
    m_downloads.InsertColumn(6, _T("Smart ETA"), LVCFMT_RIGHT, 95);
    m_downloads.InsertColumn(7, _T("Confidence"), LVCFMT_RIGHT, 85);
    m_downloads.InsertColumn(8, _T("Rare needed"), LVCFMT_RIGHT, 85);

    CEmuleNextTheme::ApplyToWindow(m_hWnd);
    m_refreshTimer = SetTimer(TIMER_EN_DASH_REFRESH, 2000, NULL);
    Refresh();
    return 0;
}

void CEmuleNextDashboardWnd::OnSize(UINT type, int cx, int cy)
{
    CWnd::OnSize(type, cx, cy);
    if (!::IsWindow(m_downloads.m_hWnd))
        return;
    const int margin = 8;
    m_summary.MoveWindow(margin, margin, max(0, cx - margin * 2), 22);
    m_downloads.MoveWindow(margin, margin + 26,
        max(0, cx - margin * 2), max(0, cy - margin * 2 - 26));
}

void CEmuleNextDashboardWnd::OnTimer(UINT_PTR timerId)
{
    if (timerId == TIMER_EN_DASH_REFRESH) {
        if (IsWindowVisible())
            Refresh();
        return;
    }
    CWnd::OnTimer(timerId);
}

void CEmuleNextDashboardWnd::Refresh()
{
    if (!::IsWindow(m_downloads.m_hWnd) || theApp.downloadqueue == NULL)
        return;

    m_downloads.SetRedraw(FALSE);
    m_downloads.DeleteAllItems();

    uint32 total = 0;
    uint32 transferring = 0;
    uint32 stalled = 0;
    uint32 rare = 0;
    uint32 noSources = 0;
    uint64 totalRate = 0;

    for (POSITION pos = NULL; ;) {
        CPartFile* file = theApp.downloadqueue->GetFileNext(pos);
        if (file != NULL) {
            ++total;
            totalRate += file->GetDatarate();
            if (file->GetTransferringSrcCount() > 0)
                ++transferring;

            EmuleNextFileSignals signals = BuildSignals(file);
            const EmuleNextStallReason stallReason = CDownloadIntelligence::DiagnoseStall(signals);
            if (stallReason != ENSR_NONE && file->GetStatus() != PS_COMPLETE)
                ++stalled;
            if (stallReason == ENSR_RARE_PARTS)
                ++rare;
            if (stallReason == ENSR_NO_SOURCES)
                ++noSources;

            const uint32 health = CDownloadIntelligence::FileAvailabilityHealth(signals);
            const uint64 completed = file->GetCompletedSize();
            const uint64 fileSize = file->GetFileSize();
            const uint64 remaining = fileSize > completed ? fileSize - completed : 0;
            const EmuleNextEta eta = CDownloadIntelligence::EstimateEta(signals, remaining);

            const int row = m_downloads.InsertItem(m_downloads.GetItemCount(), file->GetFileName());
            CString text;
            text.Format(_T("%.1f%%"), file->GetPercentCompleted());
            m_downloads.SetItemText(row, 1, text);
            text.Format(_T("%s/s"), (LPCTSTR)CastItoXBytes(file->GetDatarate(), false, false, 1));
            m_downloads.SetItemText(row, 2, text);
            text.Format(_T("%u / %u"), signals.usableSources, signals.totalSources);
            m_downloads.SetItemText(row, 3, text);
            text.Format(_T("%u%%"), (health + 5) / 10);
            m_downloads.SetItemText(row, 4, text);
            m_downloads.SetItemText(row, 5, StallText(stallReason));
            m_downloads.SetItemText(row, 6, EtaText(eta));
            if (eta.known) {
                text.Format(_T("%u%%"), eta.confidencePercent);
                m_downloads.SetItemText(row, 7, text);
            }
            text.Format(_T("%u"), signals.rareNeededParts);
            m_downloads.SetItemText(row, 8, text);
        }
        if (pos == NULL)
            break;
    }

    const uint32 activeUploads = theApp.uploadqueue != NULL
        ? static_cast<uint32>(theApp.uploadqueue->GetActiveUploadsCount()) : 0;
    CString summary;
    summary.Format(_T("Downloads: %u   Transferring: %u   Stalled: %u   Rare-part risk: %u   No sources: %u   Down: %s/s   Active uploads: %u"),
        total, transferring, stalled, rare, noSources,
        (LPCTSTR)CastItoXBytes(totalRate, false, false, 1), activeUploads);
    m_summary.SetWindowText(summary);

    m_downloads.SetRedraw(TRUE);
    m_downloads.Invalidate(FALSE);
}

BOOL CEmuleNextDashboardWnd::OnEraseBkgnd(CDC* dc)
{
    if (!CEmuleNextTheme::IsDarkMode())
        return CWnd::OnEraseBkgnd(dc);
    CRect rect;
    GetClientRect(&rect);
    dc->FillSolidRect(rect, CEmuleNextTheme::BackgroundColor());
    return TRUE;
}

HBRUSH CEmuleNextDashboardWnd::OnCtlColor(CDC* dc, CWnd* wnd, UINT ctlColor)
{
    if (!CEmuleNextTheme::IsDarkMode())
        return CWnd::OnCtlColor(dc, wnd, ctlColor);
    dc->SetTextColor(CEmuleNextTheme::TextColor());
    dc->SetBkColor(CEmuleNextTheme::BackgroundColor());
    if (ctlColor == CTLCOLOR_STATIC || ctlColor == CTLCOLOR_DLG)
        return static_cast<HBRUSH>(m_darkBrush.GetSafeHandle());
    return CWnd::OnCtlColor(dc, wnd, ctlColor);
}
