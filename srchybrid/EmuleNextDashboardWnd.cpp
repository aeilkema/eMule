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
#include "EmuleNextUiMetrics.h"
#include "EmuleNextSmartScheduler.h"
#include "EmuleNextTransferInsights.h"
#include "EmuleNextRuntime.h"
#include "EmuleNextSchedulerTelemetryReader.h"
#include "OtherFunctions.h"

#include <algorithm>
#include <memory>
#include <vector>

#ifdef min
#undef min
#endif
#ifdef max
#undef max
#endif

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
        IDC_EN_DASH_FILTER_LOWHEALTH,
        IDC_EN_DASH_FILTER_INTERVENTION,
        IDC_EN_DASH_FILTER_A4AF,
        IDC_EN_DASH_DOWNLOADS,
        IDC_EN_DASH_OPEN_TRANSFERS,
        IDC_EN_DASH_OPEN_SOURCES,
        IDC_EN_DASH_PAUSE_RESUME,
        IDC_EN_DASH_PRIORITY_HIGH,
        IDC_EN_DASH_PRIORITY_NORMAL,
        IDC_EN_DASH_FORCE_ANALYSIS,
        IDC_EN_DASH_RESET_INTELLIGENCE,
        IDC_EN_DASH_REFRESH_NOW,
        IDC_EN_DASH_DETAILS
    };

    const UINT_PTR TIMER_EN_DASH_REFRESH = 0x566;
    const UINT WM_EN_DASH_OPEN_FILE = WM_APP + 0x568;
    const UINT WM_EN_DASH_PERSISTED_LOADED = WM_APP + 0x569;
    const uint32 NORMAL_DISCOVERY_BUDGET = 10;
    const size_t DASHBOARD_MAX_FILES = 1000;

    struct DashboardRow
    {
        CPartFile* file;
        EmuleNextFileSignals signals;
        EmuleNextEta eta;
        EmuleNextStallReason stall;
        uint32 health;
        uint32 attention;
        uint32 discoveryBudget;
        uint32 a4afScore;
        uint32 bestSourceQuality;
        uint32 averageSourceQuality;
        uint32 sampledSources;
        uint32 strongSources;
        uint32 normalSources;
        uint32 weakSources;
        uint32 failedSources;
        uint32 transferringSources;
        double historicalBytesPerSecond;
        bool hasScheduler;
        bool schedulerApplied;
        EmuleNextSchedulingAction schedulerAction;
        uint64 lastInterventionAt;
        uint64 lastUsefulSourceAt;

        DashboardRow()
            : file(NULL)
            , stall(ENSR_NONE)
            , health(0)
            , attention(0)
            , discoveryBudget(0)
            , a4afScore(0)
            , bestSourceQuality(0)
            , averageSourceQuality(0)
            , sampledSources(0)
            , strongSources(0)
            , normalSources(0)
            , weakSources(0)
            , failedSources(0)
            , transferringSources(0)
            , historicalBytesPerSecond(0.0)
            , hasScheduler(false)
            , schedulerApplied(false)
            , schedulerAction(ENSA_NONE)
            , lastInterventionAt(0)
            , lastUsefulSourceAt(0)
        {
        }
    };

    struct PersistedContext
    {
        HWND target;
        CStringW databasePath;
        std::array<unsigned char, 16> fileHash;
    };

    struct PersistedResult
    {
        bool ok;
        std::array<unsigned char, 16> fileHash;
        EmuleNextPersistedSchedulerBundle bundle;
        PersistedResult() : ok(false) { fileHash.fill(0); }
    };

    UINT AFX_CDECL PersistedWorker(LPVOID value)
    {
        std::unique_ptr<PersistedContext> context(static_cast<PersistedContext*>(value));
        std::unique_ptr<PersistedResult> result(new PersistedResult);
        result->fileHash = context->fileHash;
        CEmuleNextSchedulerTelemetryReader reader(context->databasePath);
        result->ok = reader.LoadRecentForFile(context->fileHash.data(), result->bundle, 16, 24);
        if (::IsWindow(context->target)
            && ::PostMessage(context->target, WM_EN_DASH_PERSISTED_LOADED, 0, reinterpret_cast<LPARAM>(result.get()))) {
            result.release();
        }
        return 0;
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

    CString TimeText(uint64 timestamp)
    {
        if (timestamp == 0)
            return _T("--");
        CTime value(static_cast<time_t>(timestamp));
        return value.Format(_T("%Y-%m-%d %H:%M"));
    }

    CString RateText(double bytesPerSecond)
    {
        if (bytesPerSecond <= 0.0)
            return _T("--");
        return CastItoXBytes(static_cast<uint64>(bytesPerSecond), false, false, 1) + _T("/s");
    }

    CString RecommendationText(const DashboardRow& row)
    {
        switch (row.stall) {
        case ENSR_NO_SOURCES: return _T("Acquire more sources; discovery is the primary opportunity.");
        case ENSR_NO_NEEDED_PARTS: return _T("Known peers do not expose needed parts; wait for new sources/source exchange.");
        case ENSR_ALL_REMOTE_QUEUED: return _T("Keep useful remote queue positions; reconnect churn is unlikely to help.");
        case ENSR_RARE_PARTS: return _T("Protect rare-part sources and completion-critical pieces.");
        case ENSR_CONNECTION_FAILURE: return _T("Source endpoints are failing; prefer fresher/stronger sources.");
        case ENSR_A4AF_CONFLICT: return _T("A4AF reassignment is the strongest current opportunity.");
        case ENSR_HASHING: return _T("Hashing is active; source-side intervention is suppressed.");
        case ENSR_DISK_LIMITED: return _T("Disk pressure is the bottleneck; network intervention is suppressed.");
        default:
            if (row.signals.rareNeededParts > 0)
                return _T("Transfer is moving, but rare remaining parts still need protection.");
            if (row.health >= 800)
                return _T("Healthy transfer; hold current scheduler state.");
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
    ON_BN_CLICKED(IDC_EN_DASH_FILTER_LOWHEALTH, OnFilterLowHealth)
    ON_BN_CLICKED(IDC_EN_DASH_FILTER_INTERVENTION, OnFilterIntervention)
    ON_BN_CLICKED(IDC_EN_DASH_FILTER_A4AF, OnFilterA4AF)
    ON_BN_CLICKED(IDC_EN_DASH_OPEN_TRANSFERS, OnOpenTransfers)
    ON_BN_CLICKED(IDC_EN_DASH_OPEN_SOURCES, OnOpenSources)
    ON_BN_CLICKED(IDC_EN_DASH_PAUSE_RESUME, OnPauseResume)
    ON_BN_CLICKED(IDC_EN_DASH_PRIORITY_HIGH, OnPriorityHigh)
    ON_BN_CLICKED(IDC_EN_DASH_PRIORITY_NORMAL, OnPriorityNormal)
    ON_BN_CLICKED(IDC_EN_DASH_FORCE_ANALYSIS, OnForceAnalysis)
    ON_BN_CLICKED(IDC_EN_DASH_RESET_INTELLIGENCE, OnResetIntelligence)
    ON_BN_CLICKED(IDC_EN_DASH_REFRESH_NOW, OnRefreshNow)
    ON_NOTIFY(LVN_ITEMCHANGED, IDC_EN_DASH_DOWNLOADS, OnDownloadSelectionChanged)
    ON_NOTIFY(NM_DBLCLK, IDC_EN_DASH_DOWNLOADS, OnDownloadDoubleClick)
    ON_NOTIFY(LVN_COLUMNCLICK, IDC_EN_DASH_DOWNLOADS, OnDownloadColumnClick)
    ON_MESSAGE(WM_EN_DASH_PERSISTED_LOADED, OnPersistentDetailsLoaded)
END_MESSAGE_MAP()

CEmuleNextDashboardWnd::CEmuleNextDashboardWnd()
    : m_refreshTimer(0)
    , m_filter(DASH_ALL)
    , m_sortColumn(10)
    , m_sortAscending(false)
    , m_lastAutoRefreshTick(0)
    , m_lastRefreshDurationMs(0)
    , m_persistedLoading(false)
    , m_persistedHashValid(false)
{
    m_persistedHash.fill(0);
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
        WS_CHILD | WS_CLIPCHILDREN | WS_CLIPSIBLINGS, empty, parent, 0) != FALSE;
}

int CEmuleNextDashboardWnd::OnCreate(LPCREATESTRUCT createStruct)
{
    if (CWnd::OnCreate(createStruct) == -1)
        return -1;

    m_darkBrush.CreateSolidBrush(CEmuleNextTheme::BackgroundColor());
    CRect empty(0, 0, 0, 0);
    const DWORD filterStyle = WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTORADIOBUTTON | BS_PUSHLIKE;
    if (!m_summary.Create(_T("eMule Next Dashboard"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this, IDC_EN_DASH_SUMMARY)
        || !m_filterAll.Create(_T("All"), filterStyle | WS_GROUP, empty, this, IDC_EN_DASH_FILTER_ALL)
        || !m_filterAttention.Create(_T("Attention"), filterStyle, empty, this, IDC_EN_DASH_FILTER_ATTENTION)
        || !m_filterStalled.Create(_T("Stalled"), filterStyle, empty, this, IDC_EN_DASH_FILTER_STALLED)
        || !m_filterRare.Create(_T("Rare"), filterStyle, empty, this, IDC_EN_DASH_FILTER_RARE)
        || !m_filterNoSources.Create(_T("No sources"), filterStyle, empty, this, IDC_EN_DASH_FILTER_NOSOURCES)
        || !m_filterActive.Create(_T("Active"), filterStyle, empty, this, IDC_EN_DASH_FILTER_ACTIVE)
        || !m_filterLowHealth.Create(_T("Low health"), filterStyle, empty, this, IDC_EN_DASH_FILTER_LOWHEALTH)
        || !m_filterIntervention.Create(_T("Intervention"), filterStyle, empty, this, IDC_EN_DASH_FILTER_INTERVENTION)
        || !m_filterA4AF.Create(_T("A4AF"), filterStyle, empty, this, IDC_EN_DASH_FILTER_A4AF)
        || !m_downloads.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | LVS_REPORT | LVS_SINGLESEL | LVS_SHOWSELALWAYS,
            empty, this, IDC_EN_DASH_DOWNLOADS)
        || !m_openTransfers.Create(_T("Open in Transfers"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DASH_OPEN_TRANSFERS)
        || !m_openSources.Create(_T("Open + sources"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DASH_OPEN_SOURCES)
        || !m_pauseResume.Create(_T("Pause / Resume"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DASH_PAUSE_RESUME)
        || !m_priorityHigh.Create(_T("Priority high"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DASH_PRIORITY_HIGH)
        || !m_priorityNormal.Create(_T("Priority normal"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DASH_PRIORITY_NORMAL)
        || !m_forceAnalysis.Create(_T("Force analysis"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DASH_FORCE_ANALYSIS)
        || !m_resetIntelligence.Create(_T("Reset intelligence"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DASH_RESET_INTELLIGENCE)
        || !m_refreshNow.Create(_T("Refresh"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DASH_REFRESH_NOW)
        || !m_details.Create(_T("Select a download for detailed intelligence."), WS_CHILD | WS_VISIBLE | SS_LEFT,
            empty, this, IDC_EN_DASH_DETAILS)) {
        return -1;
    }

    CFont* font = CFont::FromHandle(static_cast<HFONT>(::GetStockObject(DEFAULT_GUI_FONT)));
    CWnd* controls[] = {
        &m_summary, &m_filterAll, &m_filterAttention, &m_filterStalled, &m_filterRare,
        &m_filterNoSources, &m_filterActive, &m_filterLowHealth, &m_filterIntervention, &m_filterA4AF,
        &m_downloads, &m_openTransfers, &m_openSources, &m_pauseResume, &m_priorityHigh,
        &m_priorityNormal, &m_forceAnalysis, &m_resetIntelligence, &m_refreshNow, &m_details
    };
    for (int i = 0; i < _countof(controls); ++i)
        controls[i]->SetFont(font);

    m_downloads.SetExtendedStyle(LVS_EX_FULLROWSELECT | LVS_EX_DOUBLEBUFFER | LVS_EX_GRIDLINES);
    const int widths[] = { 280, 72, 88, 88, 82, 92, 68, 132, 88, 72, 72, 118, 58, 132, 132, 118 };
    const LPCTSTR names[] = {
        _T("File"), _T("Progress"), _T("Live speed"), _T("Hist. speed"), _T("Sources"), _T("Quality"),
        _T("Health"), _T("Diagnosis"), _T("Smart ETA"), _T("A4AF"), _T("Attention"), _T("Scheduler"),
        _T("Applied"), _T("Last intervention"), _T("Last useful source"), _T("Source profile")
    };
    for (int i = 0; i < _countof(names); ++i)
        m_downloads.InsertColumn(i, names[i], i == 0 || i == 7 || i == 11 || i >= 13 ? LVCFMT_LEFT : LVCFMT_RIGHT,
            CEmuleNextUiMetrics::Scale(m_hWnd, widths[i]));

    LoadViewState();
    UpdateFilterButtons();
    UpdateActionButtons();
    CEmuleNextTheme::ApplyToWindow(m_hWnd);
    m_refreshTimer = SetTimer(TIMER_EN_DASH_REFRESH, 3000, NULL);
    Refresh();
    return 0;
}

BOOL CEmuleNextDashboardWnd::PreTranslateMessage(MSG* message)
{
    if (message != NULL && message->message == WM_KEYDOWN && message->wParam == VK_RETURN
        && ::GetFocus() == m_downloads.m_hWnd) {
        JumpToTransfers(false);
        return TRUE;
    }
    return CWnd::PreTranslateMessage(message);
}

void CEmuleNextDashboardWnd::OnDestroy()
{
    SaveViewState();
    if (m_refreshTimer != 0) {
        KillTimer(m_refreshTimer);
        m_refreshTimer = 0;
    }
    CWnd::OnDestroy();
}

void CEmuleNextDashboardWnd::LoadViewState()
{
    int filter = static_cast<int>(theApp.GetProfileInt(_T("eMule Next"), _T("DashboardFilter"), DASH_ALL));
    if (filter < DASH_ALL || filter >= DASH_FILTER_COUNT)
        filter = DASH_ALL;
    m_filter = static_cast<DashboardFilter>(filter);
    m_sortColumn = static_cast<int>(theApp.GetProfileInt(_T("eMule Next"), _T("DashboardSortColumn"), 10));
    if (m_sortColumn < 0 || m_sortColumn >= 16)
        m_sortColumn = 10;
    m_sortAscending = theApp.GetProfileInt(_T("eMule Next"), _T("DashboardSortAscending"), 0) != 0;
    for (int i = 0; i < 16; ++i) {
        CString key;
        key.Format(_T("DashboardColumnWidth%d"), i);
        const int width = static_cast<int>(theApp.GetProfileInt(_T("eMule Next"), key, 0));
        if (width >= 30 && width <= 1200)
            m_downloads.SetColumnWidth(i, width);
    }
}

void CEmuleNextDashboardWnd::SaveViewState()
{
    if (!::IsWindow(m_downloads.m_hWnd))
        return;
    theApp.WriteProfileInt(_T("eMule Next"), _T("DashboardFilter"), static_cast<int>(m_filter));
    theApp.WriteProfileInt(_T("eMule Next"), _T("DashboardSortColumn"), m_sortColumn);
    theApp.WriteProfileInt(_T("eMule Next"), _T("DashboardSortAscending"), m_sortAscending ? 1 : 0);
    for (int i = 0; i < 16; ++i) {
        CString key;
        key.Format(_T("DashboardColumnWidth%d"), i);
        theApp.WriteProfileInt(_T("eMule Next"), key, m_downloads.GetColumnWidth(i));
    }
}

void CEmuleNextDashboardWnd::OnSize(UINT type, int cx, int cy)
{
    CWnd::OnSize(type, cx, cy);
    if (!::IsWindow(m_downloads.m_hWnd))
        return;

    const int margin = CEmuleNextUiMetrics::Scale(m_hWnd, 8);
    const int summaryHeight = CEmuleNextUiMetrics::Scale(m_hWnd, 22);
    const int filterHeight = CEmuleNextUiMetrics::Scale(m_hWnd, 25);
    const int gap = CEmuleNextUiMetrics::Scale(m_hWnd, 5);
    const int filterRows = cx < CEmuleNextUiMetrics::Scale(m_hWnd, 900) ? 2 : 1;
    const int buttonsPerRow = filterRows == 1 ? 9 : 5;
    const int clientWidth = std::max(0, cx - margin * 2);
    const int buttonWidth = std::max(CEmuleNextUiMetrics::Scale(m_hWnd, 70),
        (clientWidth - gap * (buttonsPerRow - 1)) / buttonsPerRow);

    m_summary.MoveWindow(margin, margin, clientWidth, summaryHeight);
    const int filterTop = margin + summaryHeight + gap;
    CButton* filters[] = {
        &m_filterAll, &m_filterAttention, &m_filterStalled, &m_filterRare, &m_filterNoSources,
        &m_filterActive, &m_filterLowHealth, &m_filterIntervention, &m_filterA4AF
    };
    for (int i = 0; i < _countof(filters); ++i) {
        const int row = i / buttonsPerRow;
        const int col = i % buttonsPerRow;
        filters[i]->MoveWindow(margin + col * (buttonWidth + gap), filterTop + row * (filterHeight + gap),
            buttonWidth, filterHeight);
    }

    const int actionHeight = CEmuleNextUiMetrics::Scale(m_hWnd, 27);
    const int filterAreaHeight = filterRows * filterHeight + (filterRows - 1) * gap;
    const int listTop = filterTop + filterAreaHeight + gap;
    const int detailsHeight = std::max(CEmuleNextUiMetrics::Scale(m_hWnd, 150), std::min(CEmuleNextUiMetrics::Scale(m_hWnd, 270), cy / 4));
    const int listHeight = std::max(CEmuleNextUiMetrics::Scale(m_hWnd, 80),
        cy - listTop - detailsHeight - actionHeight - margin - gap * 3);
    m_downloads.MoveWindow(margin, listTop, clientWidth, listHeight);

    CButton* actions[] = {
        &m_openTransfers, &m_openSources, &m_pauseResume, &m_priorityHigh,
        &m_priorityNormal, &m_forceAnalysis, &m_resetIntelligence, &m_refreshNow
    };
    const int actionTop = listTop + listHeight + gap;
    const int actionWidth = std::max(CEmuleNextUiMetrics::Scale(m_hWnd, 86),
        (clientWidth - gap * 7) / 8);
    for (int i = 0; i < _countof(actions); ++i)
        actions[i]->MoveWindow(margin + i * (actionWidth + gap), actionTop, actionWidth, actionHeight);

    const int detailsTop = actionTop + actionHeight + gap;
    m_details.MoveWindow(margin, detailsTop, clientWidth, std::max(0, cy - detailsTop - margin));
}

void CEmuleNextDashboardWnd::OnTimer(UINT_PTR timerId)
{
    if (timerId == TIMER_EN_DASH_REFRESH) {
        if (IsWindowVisible()) {
            const DWORD now = ::GetTickCount();
            const DWORD minimumGap = m_lastRefreshDurationMs > 250 ? 6000 : 3000;
            if (m_lastAutoRefreshTick == 0 || now - m_lastAutoRefreshTick >= minimumGap) {
                m_lastAutoRefreshTick = now;
                Refresh();
            }
        }
        return;
    }
    CWnd::OnTimer(timerId);
}

void CEmuleNextDashboardWnd::SetFilter(DashboardFilter filter)
{
    m_filter = filter;
    theApp.WriteProfileInt(_T("eMule Next"), _T("DashboardFilter"), static_cast<int>(m_filter));
    UpdateFilterButtons();
    Refresh();
}

void CEmuleNextDashboardWnd::UpdateFilterButtons()
{
    m_filterAll.SetCheck(m_filter == DASH_ALL ? BST_CHECKED : BST_UNCHECKED);
    m_filterAttention.SetCheck(m_filter == DASH_ATTENTION ? BST_CHECKED : BST_UNCHECKED);
    m_filterStalled.SetCheck(m_filter == DASH_STALLED ? BST_CHECKED : BST_UNCHECKED);
    m_filterRare.SetCheck(m_filter == DASH_RARE ? BST_CHECKED : BST_UNCHECKED);
    m_filterNoSources.SetCheck(m_filter == DASH_NO_SOURCES ? BST_CHECKED : BST_UNCHECKED);
    m_filterActive.SetCheck(m_filter == DASH_ACTIVE ? BST_CHECKED : BST_UNCHECKED);
    m_filterLowHealth.SetCheck(m_filter == DASH_LOW_HEALTH ? BST_CHECKED : BST_UNCHECKED);
    m_filterIntervention.SetCheck(m_filter == DASH_INTERVENTION ? BST_CHECKED : BST_UNCHECKED);
    m_filterA4AF.SetCheck(m_filter == DASH_A4AF_OPPORTUNITY ? BST_CHECKED : BST_UNCHECKED);
}

void CEmuleNextDashboardWnd::Refresh()
{
    if (!::IsWindow(m_downloads.m_hWnd) || theApp.downloadqueue == NULL)
        return;
    const DWORD started = ::GetTickCount();
    CPartFile* selectedBefore = GetSelectedFile();
    std::vector<DashboardRow> rows;
    rows.reserve(std::min<size_t>(DASHBOARD_MAX_FILES, static_cast<size_t>(theApp.downloadqueue->GetFileCount())));

    uint32 total = 0, transferring = 0, stalled = 0, rare = 0, noSources = 0, attentionCount = 0;
    uint64 totalRate = 0;
    bool truncated = false;
    for (POSITION pos = NULL; ;) {
        CPartFile* file = theApp.downloadqueue->GetFileNext(pos);
        if (file != NULL) {
            ++total;
            if (rows.size() >= DASHBOARD_MAX_FILES) {
                truncated = true;
            } else {
                DashboardRow row;
                row.file = file;
                EmuleNextFileHistory history;
                if (theEmuleNextScheduler.History().GetHistory(file->GetFileHash(), history))
                    row.historicalBytesPerSecond = history.ewmaBytesPerSecond;
                const EmuleNextTransferInsight insight = CEmuleNextTransferInsights::Build(file, row.historicalBytesPerSecond);
                row.signals = insight.file;
                row.eta = insight.eta;
                row.stall = insight.stall;
                row.health = insight.health;
                row.attention = insight.attention;
                row.bestSourceQuality = insight.bestSourceQuality;
                row.averageSourceQuality = insight.averageSourceQuality;
                row.sampledSources = insight.sampledSources;
                row.strongSources = insight.strongSources;
                row.normalSources = insight.normalSources;
                row.weakSources = insight.weakSources;
                row.failedSources = insight.failedSources;
                row.transferringSources = insight.transferringSources;
                row.discoveryBudget = CDownloadIntelligence::SourceDiscoveryBudget(row.signals, NORMAL_DISCOVERY_BUDGET);
                row.a4afScore = CDownloadIntelligence::A4AFPriority(row.signals, row.bestSourceQuality);
                EmuleNextSchedulerSnapshot snapshot;
                if (theEmuleNextScheduler.GetSnapshot(file->GetFileHash(), snapshot)) {
                    row.hasScheduler = true;
                    row.schedulerApplied = snapshot.applied;
                    row.schedulerAction = snapshot.decision.primaryAction;
                    row.lastInterventionAt = snapshot.lastInterventionAt;
                    row.lastUsefulSourceAt = snapshot.lastUsefulSourceAt;
                }
                rows.push_back(row);
            }
            totalRate += file->GetDatarate();
            if (file->GetTransferringSrcCount() > 0) ++transferring;
        }
        if (pos == NULL)
            break;
    }

    for (size_t i = 0; i < rows.size(); ++i) {
        if (rows[i].stall != ENSR_NONE && rows[i].file->GetStatus() != PS_COMPLETE) ++stalled;
        if (rows[i].signals.rareNeededParts > 0) ++rare;
        if (rows[i].stall == ENSR_NO_SOURCES) ++noSources;
        if (rows[i].attention >= 700) ++attentionCount;
    }

    std::sort(rows.begin(), rows.end(), [this](const DashboardRow& a, const DashboardRow& b) {
        int compare = 0;
        switch (m_sortColumn) {
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
        }
        if (compare == 0)
            compare = a.file->GetFileName().CompareNoCase(b.file->GetFileName());
        return m_sortAscending ? compare < 0 : compare > 0;
    });

    m_downloads.SetRedraw(FALSE);
    m_downloads.DeleteAllItems();
    int selectedRow = -1;
    for (size_t i = 0; i < rows.size(); ++i) {
        const DashboardRow& r = rows[i];
        bool visible = false;
        switch (m_filter) {
        case DASH_ALL: visible = true; break;
        case DASH_ATTENTION: visible = r.attention >= 700; break;
        case DASH_STALLED: visible = r.stall != ENSR_NONE && r.file->GetStatus() != PS_COMPLETE; break;
        case DASH_RARE: visible = r.signals.rareNeededParts > 0; break;
        case DASH_NO_SOURCES: visible = r.stall == ENSR_NO_SOURCES; break;
        case DASH_ACTIVE: visible = r.file->GetTransferringSrcCount() > 0 || r.file->GetDatarate() > 0; break;
        case DASH_LOW_HEALTH: visible = r.health < 500; break;
        case DASH_INTERVENTION: visible = r.schedulerApplied || r.lastInterventionAt > 0; break;
        case DASH_A4AF_OPPORTUNITY: visible = r.signals.a4afCandidates > 0 && r.a4afScore >= 650; break;
        default: visible = true; break;
        }
        if (!visible)
            continue;

        const int row = m_downloads.InsertItem(m_downloads.GetItemCount(), r.file->GetFileName());
        m_downloads.SetItemData(row, reinterpret_cast<DWORD_PTR>(r.file));
        CString text;
        text.Format(_T("%.1f%%"), r.file->GetPercentCompleted()); m_downloads.SetItemText(row, 1, text);
        m_downloads.SetItemText(row, 2, RateText(r.signals.currentBytesPerSecond));
        m_downloads.SetItemText(row, 3, RateText(r.historicalBytesPerSecond));
        text.Format(_T("%u/%u"), r.signals.usableSources, r.signals.totalSources); m_downloads.SetItemText(row, 4, text);
        text.Format(_T("%u/%u%%"), (r.averageSourceQuality + 5) / 10, (r.bestSourceQuality + 5) / 10); m_downloads.SetItemText(row, 5, text);
        text.Format(_T("%u%%"), (r.health + 5) / 10); m_downloads.SetItemText(row, 6, text);
        m_downloads.SetItemText(row, 7, StallText(r.stall));
        m_downloads.SetItemText(row, 8, EtaText(r.eta));
        text.Format(_T("%u%%"), (r.a4afScore + 5) / 10); m_downloads.SetItemText(row, 9, text);
        text.Format(_T("%u"), r.attention); m_downloads.SetItemText(row, 10, text);
        m_downloads.SetItemText(row, 11, r.hasScheduler ? CDownloadIntelligence::SchedulingActionText(r.schedulerAction) : _T("pending"));
        m_downloads.SetItemText(row, 12, r.schedulerApplied ? _T("yes") : _T("no"));
        m_downloads.SetItemText(row, 13, TimeText(r.lastInterventionAt));
        m_downloads.SetItemText(row, 14, TimeText(r.lastUsefulSourceAt));
        text.Format(_T("S%u N%u W%u F%u"), r.strongSources, r.normalSources, r.weakSources, r.failedSources); m_downloads.SetItemText(row, 15, text);
        if (r.file == selectedBefore)
            selectedRow = row;
    }

    if (selectedRow >= 0) {
        m_downloads.SetItemState(selectedRow, LVIS_SELECTED | LVIS_FOCUSED, LVIS_SELECTED | LVIS_FOCUSED);
        m_downloads.SetSelectionMark(selectedRow);
    } else if (m_downloads.GetItemCount() > 0) {
        m_downloads.SetItemState(0, LVIS_SELECTED | LVIS_FOCUSED, LVIS_SELECTED | LVIS_FOCUSED);
        m_downloads.SetSelectionMark(0);
    }

    const uint32 activeUploads = theApp.uploadqueue != NULL ? static_cast<uint32>(theApp.uploadqueue->GetActiveUploadsCount()) : 0;
    m_lastRefreshDurationMs = ::GetTickCount() - started;
    CString summary;
    summary.Format(_T("Downloads: %u   Active: %u   Attention: %u   Stalled: %u   Rare: %u   No sources: %u   Down: %s/s   Uploads: %u   Showing: %u%s   Refresh: %ums   |   Scheduler: %s"),
        total, transferring, attentionCount, stalled, rare, noSources,
        (LPCTSTR)CastItoXBytes(totalRate, false, false, 1), activeUploads,
        static_cast<unsigned>(m_downloads.GetItemCount()), truncated ? _T(" (capped at 1000)") : _T(""),
        static_cast<unsigned>(m_lastRefreshDurationMs), (LPCTSTR)theEmuleNextScheduler.GetRuntimeStatusText());
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
    return row >= 0 ? reinterpret_cast<CPartFile*>(m_downloads.GetItemData(row)) : NULL;
}

void CEmuleNextDashboardWnd::RequestPersistentDetails()
{
    CPartFile* file = GetSelectedFile();
    if (file == NULL || !theEmuleNext.IsRunning())
        return;
    std::array<unsigned char, 16> hash;
    memcpy(hash.data(), file->GetFileHash(), 16);
    if (m_persistedHashValid && hash == m_persistedHash && (m_persistedLoading || !m_persistedSummary.IsEmpty()))
        return;
    if (m_persistedLoading)
        return;

    std::unique_ptr<PersistedContext> context(new PersistedContext);
    context->target = m_hWnd;
    context->databasePath = theEmuleNext.Database().GetDatabasePath();
    context->fileHash = hash;
    if (context->databasePath.IsEmpty())
        return;
    m_persistedHash = hash;
    m_persistedHashValid = true;
    m_persistedSummary = _T("Persistent diagnose: loading...");
    m_persistedLoading = true;
    if (AfxBeginThread(PersistedWorker, context.get(), THREAD_PRIORITY_BELOW_NORMAL) == NULL) {
        m_persistedLoading = false;
        m_persistedSummary = _T("Persistent diagnose: worker unavailable.");
        return;
    }
    context.release();
}

LRESULT CEmuleNextDashboardWnd::OnPersistentDetailsLoaded(WPARAM, LPARAM value)
{
    std::unique_ptr<PersistedResult> result(reinterpret_cast<PersistedResult*>(value));
    m_persistedLoading = false;
    CPartFile* file = GetSelectedFile();
    if (result.get() == NULL || file == NULL) {
        m_persistedSummary.Empty();
        return 0;
    }
    std::array<unsigned char, 16> currentHash;
    memcpy(currentHash.data(), file->GetFileHash(), 16);
    if (currentHash != result->fileHash) {
        m_persistedSummary.Empty();
        m_persistedHashValid = false;
        RequestPersistentDetails();
        return 0;
    }

    if (!result->ok) {
        m_persistedSummary = _T("Persistent diagnose: no readable scheduler history.");
    } else {
        CString decisionText = _T("none");
        if (!result->bundle.decisions.empty()) {
            const EmuleNextSchedulerEvent& event = result->bundle.decisions.front();
            decisionText.Format(_T("%s at %s, applied %s"),
                (LPCTSTR)CDownloadIntelligence::SchedulingActionText(event.action),
                (LPCTSTR)TimeText(event.timestamp), event.applied ? _T("yes") : _T("no"));
        }
        CString baseline = _T("--"), after30 = _T("--"), after120 = _T("--");
        for (size_t i = 0; i < result->bundle.outcomes.size(); ++i) {
            const EmuleNextSchedulerOutcomeRecord& o = result->bundle.outcomes[i];
            CString valueText;
            valueText.Format(_T("%s, %u sources"), (LPCTSTR)RateText(o.bytesPerSecond), o.usableSources);
            if (o.windowSeconds == 0 && baseline == _T("--")) baseline = valueText;
            else if (o.windowSeconds == 30 && after30 == _T("--")) after30 = valueText;
            else if (o.windowSeconds == 120 && after120 == _T("--")) after120 = valueText;
        }
        m_persistedSummary.Format(_T("Persistent diagnose: last decision %s | baseline %s | +30s %s | +120s %s"),
            (LPCTSTR)decisionText, (LPCTSTR)baseline, (LPCTSTR)after30, (LPCTSTR)after120);
    }
    UpdateDetails();
    return 0;
}

void CEmuleNextDashboardWnd::UpdateDetails()
{
    CPartFile* file = GetSelectedFile();
    if (file == NULL) {
        m_details.SetWindowText(_T("Select a download for detailed intelligence."));
        UpdateActionButtons();
        return;
    }

    EmuleNextFileHistory history;
    const double historical = theEmuleNextScheduler.History().GetHistory(file->GetFileHash(), history)
        ? history.ewmaBytesPerSecond : 0.0;
    const EmuleNextTransferInsight insight = CEmuleNextTransferInsights::Build(file, historical);
    const uint32 discoveryBudget = CDownloadIntelligence::SourceDiscoveryBudget(insight.file, NORMAL_DISCOVERY_BUDGET);
    const uint32 a4afScore = CDownloadIntelligence::A4AFPriority(insight.file, insight.bestSourceQuality);

    EmuleNextSchedulerSnapshot snapshot;
    const bool hasSnapshot = theEmuleNextScheduler.GetSnapshot(file->GetFileHash(), snapshot);
    EmuleNextInterventionOutcome outcome;
    const bool hasOutcome = theEmuleNextScheduler.GetOutcome(file->GetFileHash(), outcome);

    CString outcomeText = _T("No intervention outcome is active.");
    if (hasOutcome) {
        outcomeText.Format(_T("Outcome %s: baseline %s/%u sources; +30s %s/%u%s; +120s %s/%u%s."),
            (LPCTSTR)CDownloadIntelligence::SchedulingActionText(outcome.action),
            (LPCTSTR)RateText(outcome.baselineBytesPerSecond), outcome.baselineUsableSources,
            (LPCTSTR)RateText(outcome.bytesPerSecond30), outcome.usableSources30, outcome.measured30 ? _T("") : _T(" pending"),
            (LPCTSTR)RateText(outcome.bytesPerSecond120), outcome.usableSources120, outcome.measured120 ? _T("") : _T(" pending"));
    }

    CString schedulerText;
    if (hasSnapshot) {
        schedulerText.Format(_T("Scheduler: %s | applied %s | last intervention %s | discovery %s | A4AF %s | rare %s | last useful source %s"),
            (LPCTSTR)CDownloadIntelligence::SchedulingActionText(snapshot.decision.primaryAction),
            snapshot.applied ? _T("yes") : _T("no"),
            (LPCTSTR)TimeText(snapshot.lastInterventionAt), (LPCTSTR)TimeText(snapshot.lastDiscoveryAt),
            (LPCTSTR)TimeText(snapshot.lastA4AFAt), (LPCTSTR)TimeText(snapshot.lastRarePartAt),
            (LPCTSTR)TimeText(snapshot.lastUsefulSourceAt));
    } else {
        schedulerText = _T("Scheduler: pending first analysis");
    }

    CString details;
    details.Format(
        _T("%s\r\nStatus: %s   Progress: %.1f%%   Health: %u%%   Attention: %u\r\n")
        _T("Rates: live %s   historical %s   Smart ETA %s (%u%% confidence)\r\n")
        _T("Sources: %u usable/%u total   sampled %u   quality avg/best %u%%/%u%%   profile strong %u / normal %u / weak %u / failed %u / transferring %u\r\n")
        _T("Needed parts: %u   rare: %u   remote queued: %u   A4AF candidates: %u   A4AF score: %u%%   discovery budget: %u/%u\r\n")
        _T("%s\r\n%s\r\nRecommendation: %s\r\n%s"),
        (LPCTSTR)file->GetFileName(), (LPCTSTR)StallText(insight.stall), file->GetPercentCompleted(),
        (insight.health + 5) / 10, insight.attention,
        (LPCTSTR)RateText(insight.file.currentBytesPerSecond), (LPCTSTR)RateText(historical),
        (LPCTSTR)EtaText(insight.eta), insight.eta.known ? insight.eta.confidencePercent : 0,
        insight.file.usableSources, insight.file.totalSources, insight.sampledSources,
        (insight.averageSourceQuality + 5) / 10, (insight.bestSourceQuality + 5) / 10,
        insight.strongSources, insight.normalSources, insight.weakSources, insight.failedSources, insight.transferringSources,
        insight.file.neededParts, insight.file.rareNeededParts, insight.file.queuedSources, insight.file.a4afCandidates,
        (a4afScore + 5) / 10, discoveryBudget, NORMAL_DISCOVERY_BUDGET,
        (LPCTSTR)schedulerText, (LPCTSTR)outcomeText, (LPCTSTR)RecommendationText(DashboardRow()),
        m_persistedSummary.IsEmpty() ? _T("Persistent diagnose: not loaded yet.") : (LPCTSTR)m_persistedSummary);

    // Use a real row for recommendation rather than the placeholder used in the format above.
    DashboardRow recommendationRow;
    recommendationRow.file = file;
    recommendationRow.signals = insight.file;
    recommendationRow.stall = insight.stall;
    recommendationRow.health = insight.health;
    CString recommendation = RecommendationText(recommendationRow);
    const int marker = details.Find(_T("Recommendation: "));
    if (marker >= 0) {
        const int end = details.Find(_T("\r\n"), marker);
        if (end >= 0)
            details = details.Left(marker) + _T("Recommendation: ") + recommendation + details.Mid(end);
    }

    m_details.SetWindowText(details);
    UpdateActionButtons();
    RequestPersistentDetails();
}

void CEmuleNextDashboardWnd::UpdateActionButtons()
{
    CPartFile* file = GetSelectedFile();
    const BOOL hasFile = file != NULL ? TRUE : FALSE;
    m_openTransfers.EnableWindow(hasFile);
    m_openSources.EnableWindow(hasFile);
    m_priorityHigh.EnableWindow(hasFile);
    m_priorityNormal.EnableWindow(hasFile);
    m_forceAnalysis.EnableWindow(hasFile);
    m_resetIntelligence.EnableWindow(hasFile);
    if (file == NULL) {
        m_pauseResume.EnableWindow(FALSE);
        m_pauseResume.SetWindowText(_T("Pause / Resume"));
        return;
    }
    if (file->CanResumeFile()) {
        m_pauseResume.EnableWindow(TRUE);
        m_pauseResume.SetWindowText(_T("Resume"));
    } else if (file->CanPauseFile()) {
        m_pauseResume.EnableWindow(TRUE);
        m_pauseResume.SetWindowText(_T("Pause"));
    } else {
        m_pauseResume.EnableWindow(FALSE);
        m_pauseResume.SetWindowText(_T("Pause / Resume"));
    }
}

void CEmuleNextDashboardWnd::JumpToTransfers(bool expandSources)
{
    CPartFile* file = GetSelectedFile();
    if (file != NULL && GetParent() != NULL)
        GetParent()->SendMessage(WM_EN_DASH_OPEN_FILE, expandSources ? 1 : 0, reinterpret_cast<LPARAM>(file));
}

void CEmuleNextDashboardWnd::OnFilterAll() { SetFilter(DASH_ALL); }
void CEmuleNextDashboardWnd::OnFilterAttention() { SetFilter(DASH_ATTENTION); }
void CEmuleNextDashboardWnd::OnFilterStalled() { SetFilter(DASH_STALLED); }
void CEmuleNextDashboardWnd::OnFilterRare() { SetFilter(DASH_RARE); }
void CEmuleNextDashboardWnd::OnFilterNoSources() { SetFilter(DASH_NO_SOURCES); }
void CEmuleNextDashboardWnd::OnFilterActive() { SetFilter(DASH_ACTIVE); }
void CEmuleNextDashboardWnd::OnFilterLowHealth() { SetFilter(DASH_LOW_HEALTH); }
void CEmuleNextDashboardWnd::OnFilterIntervention() { SetFilter(DASH_INTERVENTION); }
void CEmuleNextDashboardWnd::OnFilterA4AF() { SetFilter(DASH_A4AF_OPPORTUNITY); }

void CEmuleNextDashboardWnd::OnOpenTransfers() { JumpToTransfers(false); }
void CEmuleNextDashboardWnd::OnOpenSources() { JumpToTransfers(true); }

void CEmuleNextDashboardWnd::OnPauseResume()
{
    CPartFile* file = GetSelectedFile();
    if (file == NULL) return;
    if (file->CanResumeFile()) file->ResumeFile();
    else if (file->CanPauseFile()) file->PauseFile();
    Refresh();
}

void CEmuleNextDashboardWnd::OnPriorityHigh()
{
    CPartFile* file = GetSelectedFile();
    if (file == NULL) return;
    file->SetAutoDownPriority(false);
    file->SetDownPriority(PR_HIGH);
    Refresh();
}

void CEmuleNextDashboardWnd::OnPriorityNormal()
{
    CPartFile* file = GetSelectedFile();
    if (file == NULL) return;
    file->SetAutoDownPriority(false);
    file->SetDownPriority(PR_NORMAL);
    Refresh();
}

void CEmuleNextDashboardWnd::OnForceAnalysis()
{
    CPartFile* file = GetSelectedFile();
    if (file != NULL && theApp.downloadqueue != NULL) {
        theEmuleNextScheduler.ForceAnalyze(theApp.downloadqueue, file);
        m_persistedSummary.Empty();
        m_persistedHashValid = false;
        Refresh();
    }
}

void CEmuleNextDashboardWnd::OnResetIntelligence()
{
    CPartFile* file = GetSelectedFile();
    if (file == NULL) return;
    theEmuleNextScheduler.ResetFileIntelligence(file->GetFileHash(), true);
    m_persistedSummary.Empty();
    m_persistedHashValid = false;
    Refresh();
}

void CEmuleNextDashboardWnd::OnRefreshNow() { Refresh(); }

void CEmuleNextDashboardWnd::OnDownloadSelectionChanged(NMHDR*, LRESULT* result)
{
    m_persistedSummary.Empty();
    m_persistedHashValid = false;
    UpdateDetails();
    if (result != NULL) *result = 0;
}

void CEmuleNextDashboardWnd::OnDownloadDoubleClick(NMHDR*, LRESULT* result)
{
    JumpToTransfers(true);
    if (result != NULL) *result = 0;
}

void CEmuleNextDashboardWnd::OnDownloadColumnClick(NMHDR* header, LRESULT* result)
{
    const NM_LISTVIEW* view = reinterpret_cast<const NM_LISTVIEW*>(header);
    if (view != NULL && view->iSubItem >= 0 && view->iSubItem < 16) {
        if (m_sortColumn == view->iSubItem)
            m_sortAscending = !m_sortAscending;
        else {
            m_sortColumn = view->iSubItem;
            m_sortAscending = true;
        }
        theApp.WriteProfileInt(_T("eMule Next"), _T("DashboardSortColumn"), m_sortColumn);
        theApp.WriteProfileInt(_T("eMule Next"), _T("DashboardSortAscending"), m_sortAscending ? 1 : 0);
        Refresh();
    }
    if (result != NULL) *result = 0;
}

BOOL CEmuleNextDashboardWnd::OnEraseBkgnd(CDC* dc)
{
    if (!CEmuleNextTheme::IsDarkMode())
        return CWnd::OnEraseBkgnd(dc);
    CRect rect; GetClientRect(&rect);
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
