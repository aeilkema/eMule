//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#include "stdafx.h"
#include "EmuleNextDashboardWnd.h"

#include "emule.h"
#include "DownloadQueue.h"
#include "UploadQueue.h"
#include "PartFile.h"
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

    CString DurationText(uint64 seconds)
    {
        if (seconds < 60) {
            CString text;
            text.Format(_T("%llus"), seconds);
            return text;
        }
        if (seconds < 3600) {
            CString text;
            text.Format(_T("%llum"), seconds / 60);
            return text;
        }
        if (seconds < 86400) {
            CString text;
            text.Format(_T("%lluh %02llum"), seconds / 3600, (seconds % 3600) / 60);
            return text;
        }
        CString text;
        text.Format(_T("%llud %lluh"), seconds / 86400, (seconds % 86400) / 3600);
        return text;
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
        ::LoadCursor(NULL, IDC_ARROW), reinterpret_cast<HBRUSH>(COLOR_WINDOW + 1), NULL);
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
    m_downloads.InsertColumn(0, _T("File"), LVCFMT_LEFT, 280);
    m_downloads.InsertColumn(1, _T("Progress"), LVCFMT_RIGHT, 75);
    m_downloads.InsertColumn(2, _T("Speed"), LVCFMT_RIGHT, 95);
    m_downloads.InsertColumn(3, _T("Sources"), LVCFMT_RIGHT, 70);
    m_downloads.InsertColumn(4, _T("Health"), LVCFMT_RIGHT, 75);
    m_downloads.InsertColumn(5, _T("Diagnosis"), LVCFMT_LEFT, 135);
    m_downloads.InsertColumn(6, _T("Smart ETA"), LVCFMT_RIGHT, 105);
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
    if (::IsWindow(m_downloads.m_hWnd))
        LayoutControls(cx, cy);
}

void CEmuleNextDashboardWnd::LayoutControls(int cx, int cy)
{
    const int margin = 8;
    m_summary.MoveWindow(margin, margin + 3, max(0, cx - margin * 2), 22);
    m_downloads.MoveWindow(margin, margin + 30,
        max(0, cx - margin * 2), max(0, cy - margin * 2 - 30));
}

void CEmuleNextDashboardWnd::Refresh()
{
    if (!IsWindowVisible())
        return;
    PopulateDownloads();
}

void CEmuleNextDashboardWnd::PopulateDownloads()
{
    m_downloads.SetRedraw(FALSE);
    m_downloads.DeleteAllItems();

    uint32 files = 0;
    uint32 transferring = 0;
    uint32 stalled = 0;
    uint32 rare = 0;
    uint32 noSources = 0;
    uint64 aggregateSpeed = 0;

    POSITION pos = NULL;
    for (;;) {
        CPartFile* file = theApp.downloadqueue->GetFileNext(pos);
        if (file != NULL) {
            ++files;
            EmuleNextFileSignals signals = BuildSignals(file);
            const uint32 health = CDownloadIntelligence::FileAvailabilityHealth(signals);
            const EmuleNextStallReason stallReason = CDownloadIntelligence::DiagnoseStall(signals);
            const uint64 remaining = file->GetFileSize() > file->GetCompletedSize()
                ? file->GetFileSize() - file->GetCompletedSize() : 0;
            const EmuleNextEta eta = CDownloadIntelligence::EstimateEta(signals, remaining);

            if (file->GetTransferringSrcCount() > 0)
                ++transferring;
            if (stallReason != ENSR_NONE && stallReason != ENSR_HASHING)
                ++stalled;
            if (signals.rareNeededParts > 0)
                ++rare;
            if (signals.totalSources == 0)
                ++noSources;
            aggregateSpeed += file->GetDatarate();

            const int row = m_downloads.InsertItem(m_downloads.GetItemCount(), file->GetFileName());
            CString text;
            text.Format(_T("%.1f%%"), file->GetPercentCompleted());
            m_downloads.SetItemText(row, 1, text);
            text.Format(_T("%s/s"), (LPCTSTR)CastItoXBytes(file->GetDatarate(), false, false, 1));
            m_downloads.SetItemText(row, 2, text);
            text.Format(_T("%u/%u"), signals.usableSources, signals.totalSources);
            m_downloads.SetItemText(row, 3, text);
            text.Format(_T("%u%%"), (health + 5) / 10);
            m_downloads.SetItemText(row, 4, text);
            m_downloads.SetItemText(row, 5, StallText(stallReason));
            m_downloads.SetItemText(row, 6, eta.known ? DurationText(eta.seconds) : _T("--"));
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

    CString summary;
    summary.Format(_T("Files: %u   Transferring: %u   Stalled: %u   Rare-part risk: %u   No sources: %u   Download: %s/s   Active uploads: %u"),
        files, transferring, stalled, rare, noSources,
        (LPCTSTR)CastItoXBytes(aggregateSpeed, false, false, 1),
        static_cast<unsigned>(theApp.uploadqueue->GetActiveUploadsCount()));
    m_summary.SetWindowText(summary);

    m_downloads.SetRedraw(TRUE);
    m_downloads.Invalidate(FALSE);
}

void CEmuleNextDashboardWnd::OnTimer(UINT_PTR timerId)
{
    if (timerId == TIMER_EN_DASH_REFRESH) {
        Refresh();
        return;
    }
    CWnd::OnTimer(timerId);
}

BOOL CEmuleNextDashboardWnd::PreTranslateMessage(MSG* message)
{
    return CWnd::PreTranslateMessage(message);
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
