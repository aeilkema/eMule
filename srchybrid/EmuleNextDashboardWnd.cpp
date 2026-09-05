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

#include <algorithm>
#include <vector>

namespace
{
    enum
    {
        IDC_EN_DASH_SUMMARY = 0x7E40,
        IDC_EN_DASH_FILTER_ALL,
        IDC_EN_DASH_FILTER_ATTENTION,
        IDC_EN_DASH_FILTER_STALLED,
        IDC_EN_DASH_FILTER_RARE,
        IDC_EN_DASH_FILTER_NOSOURCES,
        IDC_EN_DASH_FILTER_ACTIVE,
        IDC_EN_DASH_DOWNLOADS,
        IDC_EN_DASH_DETAILS
    };

    const UINT_PTR TIMER_EN_DASH_REFRESH = 0x566;
    const UINT WM_EN_DASH_OPEN_FILE = WM_APP + 0x568;
    const uint32 NORMAL_DISCOVERY_BUDGET = 10;

    struct DashboardRow
    {
        CPartFile* file;
        EmuleNextFileSignals signals;
        EmuleNextStallReason stall;
        EmuleNextEta eta;
        uint32 health;
        uint32 discoveryBudget;
        uint32 a4afScore;
        uint32 attention;

        DashboardRow()
            : file(NULL)
            , stall(ENSR_NONE)
            , health(0)
            , discoveryBudget(0)
            , a4afScore(0)
            , attention(0)
        {
        }
    };

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

        // Per-cycle Kad result telemetry is not attached to CPartFile yet. Keep
        // this non-zero so zero-source files report "No sources" rather than
        // claiming a Kad subsystem failure without evidence.
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

    uint32 AttentionScore(const CPartFile* file, const EmuleNextFileSignals& signals,
        EmuleNextStallReason stall, uint32 health)
    {
        if (file == NULL || file->GetStatus() == PS_COMPLETE)
            return 0;

        uint32 score = 1000 - min<uint32>(1000, health);
        switch (stall) {
        case ENSR_NO_SOURCES: score += 900; break;
        case ENSR_NO_NEEDED_PARTS: score += 750; break;
        case ENSR_A4AF_CONFLICT: score += 700; break;
        case ENSR_CONNECTION_FAILURE: score += 650; break;
        case ENSR_RARE_PARTS: score += 600; break;
        case ENSR_ALL_REMOTE_QUEUED: score += 450; break;
        case ENSR_HASHING: score += 100; break;
        case ENSR_KAD_DISCOVERY_FAILURE: score += 800; break;
        case ENSR_DISK_LIMITED: score += 850; break;
        default: break;
        }
        score += min<uint32>(500, signals.rareNeededParts * 60);
        if (file->GetPercentCompleted() >= 90.0f && signals.neededParts > 0)
            score += 180;
        if (file->GetDatarate() > 0)
            score = score > 150 ? score - 150 : 0;
        return min<uint32>(2500, score);
    }

    CString RecommendationText(const DashboardRow& row)
    {
        switch (row.stall) {
        case ENSR_NO_SOURCES:
            return _T("Acquire more sources; discovery budget is intentionally boosted.");
        case ENSR_NO_NEEDED_PARTS:
            return _T("Known peers do not currently expose needed parts; wait for new sources or source exchange.");
        case ENSR_ALL_REMOTE_QUEUED:
            return _T("Sources exist but are queued remotely; avoid needless reconnect churn and keep queue positions.");
        case ENSR_RARE_PARTS:
            return _T("Protect rare-part sources and prioritize completion-critical pieces.");
        case ENSR_CONNECTION_FAILURE:
            return _T("Many source connections are failing; source quality and endpoint freshness need attention.");
        case ENSR_A4AF_CONFLICT:
            return _T("Useful peers are assigned to other files; A4AF reassignment is the main opportunity.");
        case ENSR_HASHING:
            return _T("File is hashing; no source-side intervention is useful right now.");
        case ENSR_DISK_LIMITED:
            return _T("Disk pressure is limiting progress; source changes will not solve this bottleneck.");
        default:
            if (row.signals.rareNeededParts > 0)
                return _T("Download is moving, but rare remaining parts still deserve protection.");
            if (row.health >= 800)
                return _T("Healthy download; no intervention recommended.");
            return _T("Monitor source health; no hard stall is detected.");
        }
    }
}

BEGIN_MESSAGE_MAP(CEmuleNextDashboardWnd, CWnd)
    ON_WM_CREATE()
    ON_WM_DESTROY()
    ON_WM_SIZE()
    ON_WM_TIMER()
    ON_WM_ERASEBKGND()
    ON_WM_CTLCOLOR()
    ON_BN_CLICKED(IDC_EN_DASH_FILTER_ALL, OnFilterAll)
    ON_BN_CLICKED(IDC_EN_DASH_FILTER_ATTENTION, OnFilterAttention)
    ON_BN_CLICKED(IDC_EN_DASH_FILTER_STALLED, OnFilterStalled)
    ON_BN_CLICKED(IDC_EN_DASH_FILTER_RARE, OnFilterRare)
    ON_BN_CLICKED(IDC_EN_DASH_FILTER_NOSOURCES, OnFilterNoSources)
    ON_BN_CLICKED(IDC_EN_DASH_FILTER_ACTIVE, OnFilterActive)
    ON_NOTIFY(LVN_ITEMCHANGED, IDC_EN_DASH_DOWNLOADS, OnDownloadSelectionChanged)
    ON_NOTIFY(NM_DBLCLK, IDC_EN_DASH_DOWNLOADS, OnDownloadDoubleClick)
END_MESSAGE_MAP()

CEmuleNextDashboardWnd::CEmuleNextDashboardWnd()
    : m_refreshTimer(0)
    , m_filter(DASH_ALL)
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
    const DWORD filterStyle = WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTORADIOBUTTON | BS_PUSHLIKE;
    if (!m_summary.Create(_T("eMule Next Dashboard"), WS_CHILD | WS_VISIBLE | SS_LEFT,
            empty, this, IDC_EN_DASH_SUMMARY)
        || !m_filterAll.Create(_T("All"), filterStyle | WS_GROUP, empty, this, IDC_EN_DASH_FILTER_ALL)
        || !m_filterAttention.Create(_T("Attention"), filterStyle, empty, this, IDC_EN_DASH_FILTER_ATTENTION)
        || !m_filterStalled.Create(_T("Stalled"), filterStyle, empty, this, IDC_EN_DASH_FILTER_STALLED)
        || !m_filterRare.Create(_T("Rare parts"), filterStyle, empty, this, IDC_EN_DASH_FILTER_RARE)
        || !m_filterNoSources.Create(_T("No sources"), filterStyle, empty, this, IDC_EN_DASH_FILTER_NOSOURCES)
        || !m_filterActive.Create(_T("Active"), filterStyle, empty, this, IDC_EN_DASH_FILTER_ACTIVE)
        || !m_downloads.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | LVS_REPORT | LVS_SINGLESEL | LVS_SHOWSELALWAYS,
            empty, this, IDC_EN_DASH_DOWNLOADS)
        || !m_details.Create(_T("Select a download for detailed intelligence."),
            WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this, IDC_EN_DASH_DETAILS)) {
        return -1;
    }

    CFont* font = CFont::FromHandle(static_cast<HFONT>(::GetStockObject(DEFAULT_GUI_FONT)));
    m_summary.SetFont(font);
    m_filterAll.SetFont(font);
    m_filterAttention.SetFont(font);
    m_filterStalled.SetFont(font);
    m_filterRare.SetFont(font);
    m_filterNoSources.SetFont(font);
    m_filterActive.SetFont(font);
    m_downloads.SetFont(font);
    m_details.SetFont(font);

    m_downloads.SetExtendedStyle(LVS_EX_FULLROWSELECT | LVS_EX_DOUBLEBUFFER | LVS_EX_GRIDLINES);
    m_downloads.InsertColumn(0, _T("File"), LVCFMT_LEFT, 290);
    m_downloads.InsertColumn(1, _T("Progress"), LVCFMT_RIGHT, 75);
    m_downloads.InsertColumn(2, _T("Speed"), LVCFMT_RIGHT, 90);
    m_downloads.InsertColumn(3, _T("Sources"), LVCFMT_RIGHT, 80);
    m_downloads.InsertColumn(4, _T("Queued"), LVCFMT_RIGHT, 65);
    m_downloads.InsertColumn(5, _T("A4AF"), LVCFMT_RIGHT, 60);
    m_downloads.InsertColumn(6, _T("Health"), LVCFMT_RIGHT, 70);
    m_downloads.InsertColumn(7, _T("Diagnosis"), LVCFMT_LEFT, 145);
    m_downloads.InsertColumn(8, _T("Smart ETA"), LVCFMT_RIGHT, 90);
    m_downloads.InsertColumn(9, _T("Conf."), LVCFMT_RIGHT, 60);
    m_downloads.InsertColumn(10, _T("Rare"), LVCFMT_RIGHT, 50);
    m_downloads.InsertColumn(11, _T("Discovery"), LVCFMT_RIGHT, 70);
    m_downloads.InsertColumn(12, _T("A4AF score"), LVCFMT_RIGHT, 80);
    m_downloads.InsertColumn(13, _T("Attention"), LVCFMT_RIGHT, 75);

    UpdateFilterButtons();
    CEmuleNextTheme::ApplyToWindow(m_hWnd);
    m_refreshTimer = SetTimer(TIMER_EN_DASH_REFRESH, 2000, NULL);
    Refresh();
    return 0;
}

BOOL CEmuleNextDashboardWnd::PreTranslateMessage(MSG* message)
{
    if (message != NULL && message->message == WM_KEYDOWN && message->wParam == VK_RETURN
        && ::GetFocus() == m_downloads.m_hWnd) {
        CPartFile* file = GetSelectedFile();
        if (file != NULL)
            GetParent()->SendMessage(WM_EN_DASH_OPEN_FILE, 0, reinterpret_cast<LPARAM>(file));
        return TRUE;
    }
    return CWnd::PreTranslateMessage(message);
}

void CEmuleNextDashboardWnd::OnDestroy()
{
    if (m_refreshTimer != 0) {
        KillTimer(m_refreshTimer);
        m_refreshTimer = 0;
    }
    CWnd::OnDestroy();
}

void CEmuleNextDashboardWnd::OnSize(UINT type, int cx, int cy)
{
    CWnd::OnSize(type, cx, cy);
    if (!::IsWindow(m_downloads.m_hWnd))
        return;

    const int margin = 8;
    const int summaryHeight = 22;
    const int filterHeight = 25;
    const int detailsHeight = min(126, max(88, cy / 4));
    const int buttonGap = 5;
    const int buttonWidth = max(74, min(105, (cx - margin * 2 - buttonGap * 5) / 6));

    m_summary.MoveWindow(margin, margin, max(0, cx - margin * 2), summaryHeight);
    int x = margin;
    const int filterTop = margin + summaryHeight + 3;
    CButton* buttons[] = {
        &m_filterAll, &m_filterAttention, &m_filterStalled,
        &m_filterRare, &m_filterNoSources, &m_filterActive
    };
    for (int i = 0; i < _countof(buttons); ++i) {
        buttons[i]->MoveWindow(x, filterTop, buttonWidth, filterHeight);
        x += buttonWidth + buttonGap;
    }

    const int listTop = filterTop + filterHeight + 5;
    const int listHeight = max(80, cy - listTop - detailsHeight - margin - 6);
    m_downloads.MoveWindow(margin, listTop, max(0, cx - margin * 2), listHeight);
    m_details.MoveWindow(margin, listTop + listHeight + 6,
        max(0, cx - margin * 2), max(0, cy - (listTop + listHeight + 6) - margin));
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

void CEmuleNextDashboardWnd::UpdateFilterButtons()
{
    m_filterAll.SetCheck(m_filter == DASH_ALL ? BST_CHECKED : BST_UNCHECKED);
    m_filterAttention.SetCheck(m_filter == DASH_ATTENTION ? BST_CHECKED : BST_UNCHECKED);
    m_filterStalled.SetCheck(m_filter == DASH_STALLED ? BST_CHECKED : BST_UNCHECKED);
    m_filterRare.SetCheck(m_filter == DASH_RARE ? BST_CHECKED : BST_UNCHECKED);
    m_filterNoSources.SetCheck(m_filter == DASH_NO_SOURCES ? BST_CHECKED : BST_UNCHECKED);
    m_filterActive.SetCheck(m_filter == DASH_ACTIVE ? BST_CHECKED : BST_UNCHECKED);
}

void CEmuleNextDashboardWnd::Refresh()
{
    if (!::IsWindow(m_downloads.m_hWnd) || theApp.downloadqueue == NULL)
        return;

    CPartFile* selectedBefore = GetSelectedFile();
    std::vector<DashboardRow> rows;
    uint32 total = 0;
    uint32 transferring = 0;
    uint32 stalled = 0;
    uint32 rare = 0;
    uint32 noSources = 0;
    uint32 attentionCount = 0;
    uint64 totalRate = 0;

    for (POSITION pos = NULL; ;) {
        CPartFile* file = theApp.downloadqueue->GetFileNext(pos);
        if (file != NULL) {
            DashboardRow row;
            row.file = file;
            row.signals = BuildSignals(file);
            row.stall = CDownloadIntelligence::DiagnoseStall(row.signals);
            row.health = CDownloadIntelligence::FileAvailabilityHealth(row.signals);
            const uint64 completed = file->GetCompletedSize();
            const uint64 fileSize = file->GetFileSize();
            const uint64 remaining = fileSize > completed ? fileSize - completed : 0;
            row.eta = CDownloadIntelligence::EstimateEta(row.signals, remaining);
            row.discoveryBudget = CDownloadIntelligence::SourceDiscoveryBudget(row.signals, NORMAL_DISCOVERY_BUDGET);
            row.a4afScore = CDownloadIntelligence::A4AFPriority(row.signals, row.health);
            row.attention = AttentionScore(file, row.signals, row.stall, row.health);
            rows.push_back(row);

            ++total;
            totalRate += file->GetDatarate();
            if (file->GetTransferringSrcCount() > 0)
                ++transferring;
            if (row.stall != ENSR_NONE && file->GetStatus() != PS_COMPLETE)
                ++stalled;
            if (row.stall == ENSR_RARE_PARTS || row.signals.rareNeededParts > 0)
                ++rare;
            if (row.stall == ENSR_NO_SOURCES)
                ++noSources;
            if (row.attention >= 700)
                ++attentionCount;
        }
        if (pos == NULL)
            break;
    }

    std::sort(rows.begin(), rows.end(), [](const DashboardRow& left, const DashboardRow& right) {
        if (left.attention != right.attention)
            return left.attention > right.attention;
        if (left.health != right.health)
            return left.health < right.health;
        return left.file->GetFileName().CompareNoCase(right.file->GetFileName()) < 0;
    });

    m_downloads.SetRedraw(FALSE);
    m_downloads.DeleteAllItems();
    int selectedRow = -1;

    for (size_t i = 0; i < rows.size(); ++i) {
        const DashboardRow& rowData = rows[i];
        const CPartFile* file = rowData.file;
        bool visible = false;
        switch (m_filter) {
        case DASH_ALL: visible = true; break;
        case DASH_ATTENTION: visible = rowData.attention >= 700; break;
        case DASH_STALLED: visible = rowData.stall != ENSR_NONE && file->GetStatus() != PS_COMPLETE; break;
        case DASH_RARE: visible = rowData.signals.rareNeededParts > 0; break;
        case DASH_NO_SOURCES: visible = rowData.stall == ENSR_NO_SOURCES; break;
        case DASH_ACTIVE: visible = file->GetTransferringSrcCount() > 0 || file->GetDatarate() > 0; break;
        default: visible = true; break;
        }
        if (!visible)
            continue;

        const int row = m_downloads.InsertItem(m_downloads.GetItemCount(), file->GetFileName());
        m_downloads.SetItemData(row, reinterpret_cast<DWORD_PTR>(rowData.file));
        CString text;
        text.Format(_T("%.1f%%"), file->GetPercentCompleted());
        m_downloads.SetItemText(row, 1, text);
        text.Format(_T("%s/s"), (LPCTSTR)CastItoXBytes(file->GetDatarate(), false, false, 1));
        m_downloads.SetItemText(row, 2, text);
        text.Format(_T("%u/%u"), rowData.signals.usableSources, rowData.signals.totalSources);
        m_downloads.SetItemText(row, 3, text);
        text.Format(_T("%u"), rowData.signals.queuedSources);
        m_downloads.SetItemText(row, 4, text);
        text.Format(_T("%u"), rowData.signals.a4afCandidates);
        m_downloads.SetItemText(row, 5, text);
        text.Format(_T("%u%%"), (rowData.health + 5) / 10);
        m_downloads.SetItemText(row, 6, text);
        m_downloads.SetItemText(row, 7, StallText(rowData.stall));
        m_downloads.SetItemText(row, 8, EtaText(rowData.eta));
        if (rowData.eta.known) {
            text.Format(_T("%u%%"), rowData.eta.confidencePercent);
            m_downloads.SetItemText(row, 9, text);
        }
        text.Format(_T("%u"), rowData.signals.rareNeededParts);
        m_downloads.SetItemText(row, 10, text);
        text.Format(_T("%u"), rowData.discoveryBudget);
        m_downloads.SetItemText(row, 11, text);
        text.Format(_T("%u%%"), (rowData.a4afScore + 5) / 10);
        m_downloads.SetItemText(row, 12, text);
        text.Format(_T("%u"), rowData.attention);
        m_downloads.SetItemText(row, 13, text);

        if (rowData.file == selectedBefore)
            selectedRow = row;
    }

    if (selectedRow >= 0) {
        m_downloads.SetItemState(selectedRow, LVIS_SELECTED | LVIS_FOCUSED, LVIS_SELECTED | LVIS_FOCUSED);
        m_downloads.SetSelectionMark(selectedRow);
        m_downloads.EnsureVisible(selectedRow, FALSE);
    } else if (m_downloads.GetItemCount() > 0) {
        m_downloads.SetItemState(0, LVIS_SELECTED | LVIS_FOCUSED, LVIS_SELECTED | LVIS_FOCUSED);
        m_downloads.SetSelectionMark(0);
    }

    const uint32 activeUploads = theApp.uploadqueue != NULL
        ? static_cast<uint32>(theApp.uploadqueue->GetActiveUploadsCount()) : 0;
    CString summary;
    summary.Format(_T("Downloads: %u   Active: %u   Attention: %u   Stalled: %u   Rare: %u   No sources: %u   Down: %s/s   Uploads: %u   Showing: %u"),
        total, transferring, attentionCount, stalled, rare, noSources,
        (LPCTSTR)CastItoXBytes(totalRate, false, false, 1), activeUploads,
        static_cast<unsigned>(m_downloads.GetItemCount()));
    m_summary.SetWindowText(summary);

    m_downloads.SetRedraw(TRUE);
    m_downloads.Invalidate(FALSE);
    UpdateDetails();
}

CPartFile* CEmuleNextDashboardWnd::GetSelectedFile() const
{
    if (!::IsWindow(m_downloads.m_hWnd))
        return NULL;
    const int row = m_downloads.GetNextItem(-1, LVIS_SELECTED);
    if (row < 0)
        return NULL;
    return reinterpret_cast<CPartFile*>(m_downloads.GetItemData(row));
}

void CEmuleNextDashboardWnd::UpdateDetails()
{
    CPartFile* file = GetSelectedFile();
    if (file == NULL) {
        m_details.SetWindowText(_T("Select a download for detailed intelligence. Double-click or press Enter to open it in Transfers."));
        return;
    }

    DashboardRow row;
    row.file = file;
    row.signals = BuildSignals(file);
    row.stall = CDownloadIntelligence::DiagnoseStall(row.signals);
    row.health = CDownloadIntelligence::FileAvailabilityHealth(row.signals);
    row.discoveryBudget = CDownloadIntelligence::SourceDiscoveryBudget(row.signals, NORMAL_DISCOVERY_BUDGET);
    row.a4afScore = CDownloadIntelligence::A4AFPriority(row.signals, row.health);
    row.attention = AttentionScore(file, row.signals, row.stall, row.health);
    const uint64 completed = file->GetCompletedSize();
    const uint64 fileSize = file->GetFileSize();
    row.eta = CDownloadIntelligence::EstimateEta(row.signals, fileSize > completed ? fileSize - completed : 0);

    CString details;
    details.Format(
        _T("%s\r\nStatus: %s   Progress: %.1f%%   Health: %u%%   Attention: %u\r\n")
        _T("Sources: %u usable / %u total   Remote queued: %u   A4AF candidates: %u   Needed parts: %u   Rare needed: %u\r\n")
        _T("Smart ETA: %s   Confidence: %s   Discovery budget: %u/%u   A4AF score: %u%%\r\n")
        _T("ETA basis: %s\r\nRecommendation: %s\r\nDouble-click or press Enter to jump to this file in Transfers."),
        (LPCTSTR)file->GetFileName(),
        (LPCTSTR)StallText(row.stall),
        file->GetPercentCompleted(),
        (row.health + 5) / 10,
        row.attention,
        row.signals.usableSources,
        row.signals.totalSources,
        row.signals.queuedSources,
        row.signals.a4afCandidates,
        row.signals.neededParts,
        row.signals.rareNeededParts,
        (LPCTSTR)EtaText(row.eta),
        row.eta.known ? (LPCTSTR)CString().Format(_T("%u%%"), row.eta.confidencePercent) : _T("--"),
        row.discoveryBudget,
        NORMAL_DISCOVERY_BUDGET,
        (row.a4afScore + 5) / 10,
        row.eta.reason.IsEmpty() ? _T("not enough stable rate data") : (LPCTSTR)row.eta.reason,
        (LPCTSTR)RecommendationText(row));
    m_details.SetWindowText(details);
}

void CEmuleNextDashboardWnd::OnFilterAll()
{
    m_filter = DASH_ALL;
    UpdateFilterButtons();
    Refresh();
}

void CEmuleNextDashboardWnd::OnFilterAttention()
{
    m_filter = DASH_ATTENTION;
    UpdateFilterButtons();
    Refresh();
}

void CEmuleNextDashboardWnd::OnFilterStalled()
{
    m_filter = DASH_STALLED;
    UpdateFilterButtons();
    Refresh();
}

void CEmuleNextDashboardWnd::OnFilterRare()
{
    m_filter = DASH_RARE;
    UpdateFilterButtons();
    Refresh();
}

void CEmuleNextDashboardWnd::OnFilterNoSources()
{
    m_filter = DASH_NO_SOURCES;
    UpdateFilterButtons();
    Refresh();
}

void CEmuleNextDashboardWnd::OnFilterActive()
{
    m_filter = DASH_ACTIVE;
    UpdateFilterButtons();
    Refresh();
}

void CEmuleNextDashboardWnd::OnDownloadSelectionChanged(NMHDR*, LRESULT* result)
{
    UpdateDetails();
    if (result != NULL)
        *result = 0;
}

void CEmuleNextDashboardWnd::OnDownloadDoubleClick(NMHDR*, LRESULT* result)
{
    CPartFile* file = GetSelectedFile();
    if (file != NULL)
        GetParent()->SendMessage(WM_EN_DASH_OPEN_FILE, 0, reinterpret_cast<LPARAM>(file));
    if (result != NULL)
        *result = 0;
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
