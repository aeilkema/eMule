//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later

#include "stdafx.h"
#include "EmuleNextSettingsWnd.h"
#include "EmuleNextTheme.h"
#include "EmuleNextVersion.h"
#include "EmuleNextSmartScheduler.h"
#include "DownloadIntelligence.h"
#include "ClientList.h"
#include "emule.h"
#include "emuledlg.h"

namespace
{
    enum
    {
        IDC_EN_THEME = 0x7E40,
        IDC_EN_DISCOVERY,
        IDC_EN_CONCURRENCY,
        IDC_EN_SCHEDULER_MODE,
        IDC_EN_SCHED_PROFILE,
        IDC_EN_SCHED_COOLDOWN,
        IDC_EN_SCHED_BATCH,
        IDC_EN_SCHED_A4AF_THRESHOLD,
        IDC_EN_SCHED_DISCOVERY,
        IDC_EN_SCHED_A4AF,
        IDC_EN_SCHED_RARE,
        IDC_EN_SCHED_ETA_HEALTH,
        IDC_EN_SCHED_HISTORY,
        IDC_EN_SCHED_TELEMETRY,
        IDC_EN_SCHED_TELEMETRY_CAPACITY,
        IDC_EN_APPLY
    };

    const int kCooldownValues[] = { 30, 45, 60, 90, 120, 180, 300, 600 };
    const int kBatchValues[] = { 2, 4, 6, 8, 12, 16, 24, 32 };
    const int kA4AFValues[] = { 400, 500, 590, 650, 720, 800, 900 };
    const int kTelemetryValues[] = { 64, 128, 256, 512, 1024, 2048, 4096 };

    int ClampInt(int value, int low, int high)
    {
        return value < low ? low : (value > high ? high : value);
    }
}

BEGIN_MESSAGE_MAP(CEmuleNextSettingsWnd, CWnd)
    ON_WM_CREATE()
    ON_WM_SIZE()
    ON_WM_ERASEBKGND()
    ON_WM_CTLCOLOR()
    ON_CBN_SELCHANGE(IDC_EN_SCHEDULER_MODE, OnSchedulingModeChanged)
    ON_BN_CLICKED(IDC_EN_APPLY, OnApplyClicked)
END_MESSAGE_MAP()

CEmuleNextSettingsWnd::CEmuleNextSettingsWnd() {}
CEmuleNextSettingsWnd::~CEmuleNextSettingsWnd() {}

bool CEmuleNextSettingsWnd::Create(CWnd* parent)
{
    if (parent == NULL) return false;
    const CString className = AfxRegisterWndClass(CS_DBLCLKS, ::LoadCursor(NULL, IDC_ARROW),
        reinterpret_cast<HBRUSH>(COLOR_WINDOW + 1), NULL);
    CRect empty(0, 0, 0, 0);
    return CWnd::CreateEx(0, className, _T("eMule Next Settings"),
        WS_CHILD | WS_CLIPCHILDREN | WS_CLIPSIBLINGS, empty, parent, 0) != FALSE;
}

void CEmuleNextSettingsWnd::FillNumberCombo(CComboBox& combo, const int* values, int count)
{
    for (int i = 0; i < count; ++i) {
        CString text;
        text.Format(_T("%d"), values[i]);
        combo.AddString(text);
    }
}

int CEmuleNextSettingsWnd::SelectNumber(CComboBox& combo, const int* values, int count, int value)
{
    int best = 0;
    int bestDistance = 0x7FFFFFFF;
    for (int i = 0; i < count; ++i) {
        const int distance = abs(values[i] - value);
        if (distance < bestDistance) {
            bestDistance = distance;
            best = i;
        }
    }
    combo.SetCurSel(best);
    return best;
}

int CEmuleNextSettingsWnd::SelectedNumber(const CComboBox& combo, const int* values, int count, int fallback) const
{
    const int selection = combo.GetCurSel();
    return selection >= 0 && selection < count ? values[selection] : fallback;
}

int CEmuleNextSettingsWnd::OnCreate(LPCREATESTRUCT createStruct)
{
    if (CWnd::OnCreate(createStruct) == -1) return -1;
    m_darkBrush.CreateSolidBrush(CEmuleNextTheme::BackgroundColor());
    CRect empty(0, 0, 0, 0);
    if (!m_heading.Create(EMULENEXT_PRODUCT_WITH_CORE_TEXT, WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_themeLabel.Create(_T("Appearance"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_themeMode.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | CBS_DROPDOWNLIST, empty, this, IDC_EN_THEME)
        || !m_discoveryLabel.Create(_T("Peer knowledge"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_discoveryEnabled.Create(_T("Automatically inspect shared files exposed by connected peers"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX, empty, this, IDC_EN_DISCOVERY)
        || !m_concurrencyLabel.Create(_T("Maximum concurrent shared-file requests"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_maxConcurrent.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | CBS_DROPDOWNLIST, empty, this, IDC_EN_CONCURRENCY)
        || !m_schedulerHeading.Create(_T("Smart Scheduling"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_schedulerModeLabel.Create(_T("Scheduler mode"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_schedulerMode.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | CBS_DROPDOWNLIST, empty, this, IDC_EN_SCHEDULER_MODE)
        || !m_schedulerProfileLabel.Create(_T("Scheduler profile"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_schedulerProfile.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | CBS_DROPDOWNLIST, empty, this, IDC_EN_SCHED_PROFILE)
        || !m_schedulerCooldownLabel.Create(_T("Intervention cooldown (seconds)"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_schedulerCooldown.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | CBS_DROPDOWNLIST, empty, this, IDC_EN_SCHED_COOLDOWN)
        || !m_schedulerBatchLabel.Create(_T("Files analysed per 2-second pass"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_schedulerBatch.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | CBS_DROPDOWNLIST, empty, this, IDC_EN_SCHED_BATCH)
        || !m_a4afThresholdLabel.Create(_T("Minimum A4AF intelligence score"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_a4afThreshold.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | CBS_DROPDOWNLIST, empty, this, IDC_EN_SCHED_A4AF_THRESHOLD)
        || !m_sourceDiscoveryIntelligence.Create(_T("Source Discovery Intelligence"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX, empty, this, IDC_EN_SCHED_DISCOVERY)
        || !m_a4afIntelligence.Create(_T("A4AF Intelligence"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX, empty, this, IDC_EN_SCHED_A4AF)
        || !m_rarePartIntelligence.Create(_T("Rare Part Intelligence"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX, empty, this, IDC_EN_SCHED_RARE)
        || !m_etaHealthDisplay.Create(_T("Show Smart ETA and Health intelligence"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX, empty, this, IDC_EN_SCHED_ETA_HEALTH)
        || !m_historyCache.Create(_T("Use bounded in-memory transfer history cache"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX, empty, this, IDC_EN_SCHED_HISTORY)
        || !m_telemetry.Create(_T("Keep scheduler decision telemetry in memory"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX, empty, this, IDC_EN_SCHED_TELEMETRY)
        || !m_telemetryCapacityLabel.Create(_T("Telemetry retention (events)"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_telemetryCapacity.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | CBS_DROPDOWNLIST, empty, this, IDC_EN_SCHED_TELEMETRY_CAPACITY)
        || !m_schedulerRuntime.Create(_T("Scheduler runtime: waiting for first pass"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_schedulerSafety.Create(_T("Analysis only never changes scheduler/network behavior. Automatic mode is explicitly opt-in."), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_apply.Create(_T("Apply"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_APPLY)
        || !m_status.Create(_T("Changes are stored in the eMule profile."), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)) return -1;

    CFont* font = CFont::FromHandle(static_cast<HFONT>(::GetStockObject(DEFAULT_GUI_FONT)));
    CWnd* controls[] = { &m_heading, &m_themeLabel, &m_themeMode, &m_discoveryLabel, &m_discoveryEnabled,
        &m_concurrencyLabel, &m_maxConcurrent, &m_schedulerHeading, &m_schedulerModeLabel, &m_schedulerMode,
        &m_schedulerProfileLabel, &m_schedulerProfile, &m_schedulerCooldownLabel, &m_schedulerCooldown,
        &m_schedulerBatchLabel, &m_schedulerBatch, &m_a4afThresholdLabel, &m_a4afThreshold,
        &m_sourceDiscoveryIntelligence, &m_a4afIntelligence, &m_rarePartIntelligence, &m_etaHealthDisplay,
        &m_historyCache, &m_telemetry, &m_telemetryCapacityLabel, &m_telemetryCapacity,
        &m_schedulerRuntime, &m_schedulerSafety, &m_apply, &m_status };
    for (int i = 0; i < _countof(controls); ++i) controls[i]->SetFont(font);

    m_themeMode.AddString(_T("System")); m_themeMode.AddString(_T("Light")); m_themeMode.AddString(_T("Dark"));
    for (int i = 1; i <= 8; ++i) { CString value; value.Format(_T("%d"), i); m_maxConcurrent.AddString(value); }
    m_schedulerMode.AddString(_T("Analysis only (recommended)"));
    m_schedulerMode.AddString(_T("Assist / recommendations"));
    m_schedulerMode.AddString(_T("Automatic intervention"));
    m_schedulerProfile.AddString(_T("Conservative"));
    m_schedulerProfile.AddString(_T("Balanced"));
    m_schedulerProfile.AddString(_T("Responsive"));
    FillNumberCombo(m_schedulerCooldown, kCooldownValues, _countof(kCooldownValues));
    FillNumberCombo(m_schedulerBatch, kBatchValues, _countof(kBatchValues));
    FillNumberCombo(m_a4afThreshold, kA4AFValues, _countof(kA4AFValues));
    FillNumberCombo(m_telemetryCapacity, kTelemetryValues, _countof(kTelemetryValues));

    Refresh();
    CEmuleNextTheme::ApplyToWindow(m_hWnd);
    return 0;
}

void CEmuleNextSettingsWnd::Refresh()
{
    if (!::IsWindow(m_hWnd)) return;
    m_themeMode.SetCurSel(static_cast<int>(CEmuleNextTheme::GetMode()));
    const bool discovery = theApp.GetProfileInt(_T("eMule Next"), _T("PeerShareDiscovery"), 1) != 0;
    int concurrent = ClampInt(static_cast<int>(theApp.GetProfileInt(_T("eMule Next"), _T("PeerShareMaxConcurrent"), 2)), 1, 8);
    m_discoveryEnabled.SetCheck(discovery ? BST_CHECKED : BST_UNCHECKED);
    m_maxConcurrent.SetCurSel(concurrent - 1);

    int mode = ClampInt(static_cast<int>(theApp.GetProfileInt(_T("eMule Next"), _T("SmartSchedulingMode"), ENSM_ANALYSIS_ONLY)), ENSM_ANALYSIS_ONLY, ENSM_AUTOMATIC);
    m_schedulerMode.SetCurSel(mode);
    m_schedulerProfile.SetCurSel(ClampInt(static_cast<int>(theApp.GetProfileInt(_T("eMule Next"), _T("SmartSchedulerProfile"), 1)), 0, 2));
    SelectNumber(m_schedulerCooldown, kCooldownValues, _countof(kCooldownValues), static_cast<int>(theApp.GetProfileInt(_T("eMule Next"), _T("SmartSchedulerCooldown"), 90)));
    SelectNumber(m_schedulerBatch, kBatchValues, _countof(kBatchValues), static_cast<int>(theApp.GetProfileInt(_T("eMule Next"), _T("SmartSchedulerMaxFilesPerRound"), 8)));
    SelectNumber(m_a4afThreshold, kA4AFValues, _countof(kA4AFValues), static_cast<int>(theApp.GetProfileInt(_T("eMule Next"), _T("SmartA4AFMinimumScore"), 650)));
    SelectNumber(m_telemetryCapacity, kTelemetryValues, _countof(kTelemetryValues), static_cast<int>(theApp.GetProfileInt(_T("eMule Next"), _T("SmartTelemetryCapacity"), 256)));
    m_sourceDiscoveryIntelligence.SetCheck(theApp.GetProfileInt(_T("eMule Next"), _T("SmartSourceDiscovery"), 1) ? BST_CHECKED : BST_UNCHECKED);
    m_a4afIntelligence.SetCheck(theApp.GetProfileInt(_T("eMule Next"), _T("SmartA4AF"), 1) ? BST_CHECKED : BST_UNCHECKED);
    m_rarePartIntelligence.SetCheck(theApp.GetProfileInt(_T("eMule Next"), _T("SmartRareParts"), 1) ? BST_CHECKED : BST_UNCHECKED);
    m_etaHealthDisplay.SetCheck(theApp.GetProfileInt(_T("eMule Next"), _T("SmartEtaHealthDisplay"), 1) ? BST_CHECKED : BST_UNCHECKED);
    m_historyCache.SetCheck(theApp.GetProfileInt(_T("eMule Next"), _T("SmartHistoryCache"), 1) ? BST_CHECKED : BST_UNCHECKED);
    m_telemetry.SetCheck(theApp.GetProfileInt(_T("eMule Next"), _T("SmartTelemetry"), 1) ? BST_CHECKED : BST_UNCHECKED);
    m_schedulerRuntime.SetWindowText(_T("Scheduler runtime: ") + theEmuleNextScheduler.GetRuntimeStatusText());
    UpdateSchedulingControls();
}

void CEmuleNextSettingsWnd::OnSize(UINT type, int cx, int cy)
{
    CWnd::OnSize(type, cx, cy);
    if (::IsWindow(m_heading.m_hWnd)) LayoutControls(cx, cy);
}

void CEmuleNextSettingsWnd::LayoutControls(int cx, int /*cy*/)
{
    const int margin = 18, labelWidth = 250, fieldLeft = margin + labelWidth + 16;
    const int fieldWidth = cx - fieldLeft - margin > 290 ? 290 : (cx - fieldLeft - margin < 150 ? 150 : cx - fieldLeft - margin);
    const int checkWidth = cx - fieldLeft - margin > 280 ? cx - fieldLeft - margin : 280;
    int y = 14;
    m_heading.MoveWindow(margin, y, cx - margin * 2 > 200 ? cx - margin * 2 : 200, 22); y += 32;
    m_themeLabel.MoveWindow(margin, y + 4, labelWidth, 20); m_themeMode.MoveWindow(fieldLeft, y, fieldWidth, 220); y += 31;
    m_discoveryLabel.MoveWindow(margin, y + 3, labelWidth, 20); m_discoveryEnabled.MoveWindow(fieldLeft, y, checkWidth, 22); y += 29;
    m_concurrencyLabel.MoveWindow(margin, y + 4, labelWidth, 20); m_maxConcurrent.MoveWindow(fieldLeft, y, 90, 220); y += 38;

    m_schedulerHeading.MoveWindow(margin, y, cx - margin * 2 > 200 ? cx - margin * 2 : 200, 22); y += 27;
    m_schedulerModeLabel.MoveWindow(margin, y + 4, labelWidth, 20); m_schedulerMode.MoveWindow(fieldLeft, y, fieldWidth, 220); y += 29;
    m_schedulerProfileLabel.MoveWindow(margin, y + 4, labelWidth, 20); m_schedulerProfile.MoveWindow(fieldLeft, y, fieldWidth, 220); y += 29;
    m_schedulerCooldownLabel.MoveWindow(margin, y + 4, labelWidth, 20); m_schedulerCooldown.MoveWindow(fieldLeft, y, 120, 220); y += 29;
    m_schedulerBatchLabel.MoveWindow(margin, y + 4, labelWidth, 20); m_schedulerBatch.MoveWindow(fieldLeft, y, 120, 220); y += 29;
    m_a4afThresholdLabel.MoveWindow(margin, y + 4, labelWidth, 20); m_a4afThreshold.MoveWindow(fieldLeft, y, 120, 220); y += 31;
    m_sourceDiscoveryIntelligence.MoveWindow(fieldLeft, y, checkWidth, 21); y += 24;
    m_a4afIntelligence.MoveWindow(fieldLeft, y, checkWidth, 21); y += 24;
    m_rarePartIntelligence.MoveWindow(fieldLeft, y, checkWidth, 21); y += 24;
    m_etaHealthDisplay.MoveWindow(fieldLeft, y, checkWidth, 21); y += 24;
    m_historyCache.MoveWindow(fieldLeft, y, checkWidth, 21); y += 24;
    m_telemetry.MoveWindow(fieldLeft, y, checkWidth, 21); y += 27;
    m_telemetryCapacityLabel.MoveWindow(margin, y + 4, labelWidth, 20); m_telemetryCapacity.MoveWindow(fieldLeft, y, 120, 220); y += 34;
    m_schedulerRuntime.MoveWindow(margin, y, cx - margin * 2 > 200 ? cx - margin * 2 : 200, 32); y += 35;
    m_schedulerSafety.MoveWindow(margin, y, cx - margin * 2 > 200 ? cx - margin * 2 : 200, 34); y += 39;
    m_apply.MoveWindow(fieldLeft, y, 100, 28);
    m_status.MoveWindow(fieldLeft + 115, y + 5, cx - fieldLeft - 115 - margin > 100 ? cx - fieldLeft - 115 - margin : 100, 20);
}

void CEmuleNextSettingsWnd::UpdateSchedulingControls()
{
    const int mode = m_schedulerMode.GetCurSel();
    const BOOL enabled = mode >= ENSM_ANALYSIS_ONLY ? TRUE : FALSE;
    m_schedulerProfile.EnableWindow(enabled);
    m_schedulerCooldown.EnableWindow(enabled);
    m_schedulerBatch.EnableWindow(enabled);
    m_a4afThreshold.EnableWindow(enabled && m_a4afIntelligence.GetCheck() == BST_CHECKED);
    m_sourceDiscoveryIntelligence.EnableWindow(enabled);
    m_a4afIntelligence.EnableWindow(enabled);
    m_rarePartIntelligence.EnableWindow(enabled);
    m_etaHealthDisplay.EnableWindow(TRUE);
    m_historyCache.EnableWindow(TRUE);
    m_telemetry.EnableWindow(TRUE);
    m_telemetryCapacity.EnableWindow(m_telemetry.GetCheck() == BST_CHECKED);
    if (mode == ENSM_AUTOMATIC)
        m_schedulerSafety.SetWindowText(_T("Automatic mode may alter scheduler choices. Legacy protocol restrictions stay authoritative; interventions are bounded, cooled down and feature-gated."));
    else if (mode == ENSM_ASSIST)
        m_schedulerSafety.SetWindowText(_T("Assist mode calculates and displays recommendations, scores and preferred actions but executes no source-discovery intervention."));
    else
        m_schedulerSafety.SetWindowText(_T("Analysis only never changes scheduler/network behavior. This remains the safe default."));
}

void CEmuleNextSettingsWnd::OnSchedulingModeChanged()
{
    UpdateSchedulingControls();
}

BOOL CEmuleNextSettingsWnd::OnEraseBkgnd(CDC* dc)
{
    if (!CEmuleNextTheme::IsDarkMode()) return CWnd::OnEraseBkgnd(dc);
    CRect rect; GetClientRect(&rect); dc->FillSolidRect(rect, CEmuleNextTheme::BackgroundColor()); return TRUE;
}

HBRUSH CEmuleNextSettingsWnd::OnCtlColor(CDC* dc, CWnd* wnd, UINT ctlColor)
{
    if (!CEmuleNextTheme::IsDarkMode()) return CWnd::OnCtlColor(dc, wnd, ctlColor);
    dc->SetTextColor(CEmuleNextTheme::TextColor()); dc->SetBkColor(CEmuleNextTheme::BackgroundColor());
    if (ctlColor == CTLCOLOR_STATIC || ctlColor == CTLCOLOR_DLG) return static_cast<HBRUSH>(m_darkBrush.GetSafeHandle());
    return CWnd::OnCtlColor(dc, wnd, ctlColor);
}

void CEmuleNextSettingsWnd::OnApplyClicked()
{
    int theme = m_themeMode.GetCurSel();
    if (theme < ENTM_SYSTEM || theme > ENTM_DARK) theme = ENTM_SYSTEM;
    CEmuleNextTheme::SetMode(static_cast<EmuleNextThemeMode>(theme));

    const bool discovery = m_discoveryEnabled.GetCheck() == BST_CHECKED;
    const int concurrent = ClampInt(m_maxConcurrent.GetCurSel() + 1, 1, 8);
    theApp.WriteProfileInt(_T("eMule Next"), _T("PeerShareDiscovery"), discovery ? 1 : 0);
    theApp.WriteProfileInt(_T("eMule Next"), _T("PeerShareMaxConcurrent"), concurrent);
    if (theApp.clientlist != NULL) {
        theApp.clientlist->SetPeerShareDiscoveryEnabled(discovery);
        theApp.clientlist->SetPeerShareMaxConcurrent(static_cast<uint32>(concurrent));
    }

    int schedulerMode = ClampInt(m_schedulerMode.GetCurSel(), ENSM_ANALYSIS_ONLY, ENSM_AUTOMATIC);
    const int schedulerProfile = ClampInt(m_schedulerProfile.GetCurSel(), 0, 2);
    const int cooldown = SelectedNumber(m_schedulerCooldown, kCooldownValues, _countof(kCooldownValues), 90);
    const int batch = SelectedNumber(m_schedulerBatch, kBatchValues, _countof(kBatchValues), 8);
    const int a4afThreshold = SelectedNumber(m_a4afThreshold, kA4AFValues, _countof(kA4AFValues), 650);
    const int telemetryCapacity = SelectedNumber(m_telemetryCapacity, kTelemetryValues, _countof(kTelemetryValues), 256);

    theApp.WriteProfileInt(_T("eMule Next"), _T("SmartSchedulingMode"), schedulerMode);
    theApp.WriteProfileInt(_T("eMule Next"), _T("SmartSchedulerProfile"), schedulerProfile);
    theApp.WriteProfileInt(_T("eMule Next"), _T("SmartSchedulerCooldown"), cooldown);
    theApp.WriteProfileInt(_T("eMule Next"), _T("SmartSchedulerMaxFilesPerRound"), batch);
    theApp.WriteProfileInt(_T("eMule Next"), _T("SmartA4AFMinimumScore"), a4afThreshold);
    theApp.WriteProfileInt(_T("eMule Next"), _T("SmartSourceDiscovery"), m_sourceDiscoveryIntelligence.GetCheck() == BST_CHECKED ? 1 : 0);
    theApp.WriteProfileInt(_T("eMule Next"), _T("SmartA4AF"), m_a4afIntelligence.GetCheck() == BST_CHECKED ? 1 : 0);
    theApp.WriteProfileInt(_T("eMule Next"), _T("SmartRareParts"), m_rarePartIntelligence.GetCheck() == BST_CHECKED ? 1 : 0);
    theApp.WriteProfileInt(_T("eMule Next"), _T("SmartEtaHealthDisplay"), m_etaHealthDisplay.GetCheck() == BST_CHECKED ? 1 : 0);
    theApp.WriteProfileInt(_T("eMule Next"), _T("SmartHistoryCache"), m_historyCache.GetCheck() == BST_CHECKED ? 1 : 0);
    theApp.WriteProfileInt(_T("eMule Next"), _T("SmartTelemetry"), m_telemetry.GetCheck() == BST_CHECKED ? 1 : 0);
    theApp.WriteProfileInt(_T("eMule Next"), _T("SmartTelemetryCapacity"), telemetryCapacity);
    theEmuleNextScheduler.Telemetry().SetCapacity(static_cast<size_t>(telemetryCapacity));

    if (theApp.emuledlg != NULL) CEmuleNextTheme::ApplyToWindow(theApp.emuledlg->GetSafeHwnd());
    else CEmuleNextTheme::ApplyToWindow(m_hWnd);
    CString status;
    status.Format(_T("Applied: %s / %s, %d files per pass, %ds cooldown."),
        (LPCTSTR)CDownloadIntelligence::SchedulingModeText(static_cast<EmuleNextSchedulingMode>(schedulerMode)),
        (LPCTSTR)CEmuleNextSmartScheduler::ProfileText(schedulerProfile), batch, cooldown);
    m_status.SetWindowText(status);
    m_schedulerRuntime.SetWindowText(_T("Scheduler runtime: ") + theEmuleNextScheduler.GetRuntimeStatusText());
    UpdateSchedulingControls();
    Invalidate(TRUE);
}
