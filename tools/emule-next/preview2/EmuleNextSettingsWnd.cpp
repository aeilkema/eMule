//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#include "stdafx.h"
#include "EmuleNextSettingsWnd.h"
#include "EmuleNextModernUi.h"
#include "EmuleNextTheme.h"
#include "EmuleNextVersion.h"
#include "EmuleNextSmartScheduler.h"
#include "ClientList.h"
#include "emule.h"

namespace
{
    enum
    {
        IDC_EN_SETTINGS_NAV = 0x7E40,
        IDC_EN_THEME,
        IDC_EN_ETA_HEALTH,
        IDC_EN_DISCOVERY,
        IDC_EN_CONCURRENCY,
        IDC_EN_SCHEDULER_MODE,
        IDC_EN_SCHED_PROFILE,
        IDC_EN_SCHED_DISCOVERY,
        IDC_EN_SCHED_A4AF,
        IDC_EN_SCHED_RARE,
        IDC_EN_CUSTOM_TUNING,
        IDC_EN_SCHED_COOLDOWN,
        IDC_EN_SCHED_BATCH,
        IDC_EN_SCHED_A4AF_THRESHOLD,
        IDC_EN_APPLY
    };

    const int kCooldownValues[] = { 30, 45, 60, 90, 120, 180, 300, 600 };
    const int kBatchValues[] = { 2, 4, 6, 8, 12, 16, 24, 32 };
    const int kA4AFValues[] = { 400, 500, 590, 650, 720, 800, 900 };

    int ClampInt(int value, int low, int high)
    {
        return value < low ? low : (value > high ? high : value);
    }
}

BEGIN_MESSAGE_MAP(CEmuleNextSettingsWnd, CWnd)
    ON_WM_CREATE()
    ON_WM_SIZE()
    ON_WM_PAINT()
    ON_WM_ERASEBKGND()
    ON_WM_CTLCOLOR()
    ON_LBN_SELCHANGE(IDC_EN_SETTINGS_NAV, OnCategoryChanged)
    ON_CBN_SELCHANGE(IDC_EN_SCHEDULER_MODE, OnSchedulingModeChanged)
    ON_BN_CLICKED(IDC_EN_CUSTOM_TUNING, OnCustomTuningChanged)
    ON_BN_CLICKED(IDC_EN_APPLY, OnApplyClicked)
END_MESSAGE_MAP()

CEmuleNextSettingsWnd::CEmuleNextSettingsWnd()
    : m_category(CATEGORY_APPEARANCE)
{
}

CEmuleNextSettingsWnd::~CEmuleNextSettingsWnd()
{
}

bool CEmuleNextSettingsWnd::Create(CWnd* parent)
{
    if (parent == NULL)
        return false;
    const CString className = AfxRegisterWndClass(CS_DBLCLKS, ::LoadCursor(NULL, IDC_ARROW),
        reinterpret_cast<HBRUSH>(COLOR_WINDOW + 1), NULL);
    CRect empty(0, 0, 0, 0);
    return CWnd::CreateEx(0, className, _T("eMule Next Preview 2 Settings"),
        WS_CHILD | WS_CLIPCHILDREN | WS_CLIPSIBLINGS, empty, parent, 0) != FALSE;
}

void CEmuleNextSettingsWnd::FillNumberCombo(CComboBox& combo, const int* values, int count)
{
    for (int i = 0; i < count; ++i) {
        CString value;
        value.Format(_T("%d"), values[i]);
        combo.AddString(value);
    }
}

void CEmuleNextSettingsWnd::SelectNumber(CComboBox& combo, const int* values, int count, int value)
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
}

int CEmuleNextSettingsWnd::SelectedNumber(const CComboBox& combo, const int* values, int count, int fallback) const
{
    const int selection = combo.GetCurSel();
    return selection >= 0 && selection < count ? values[selection] : fallback;
}

int CEmuleNextSettingsWnd::OnCreate(LPCREATESTRUCT createStruct)
{
    if (CWnd::OnCreate(createStruct) == -1)
        return -1;

    m_backgroundBrush.CreateSolidBrush(CEmuleNextModernUi::WindowColor());
    CRect empty(0, 0, 0, 0);

    if (!m_navigation.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | LBS_NOTIFY | LBS_NOINTEGRALHEIGHT,
            empty, this, IDC_EN_SETTINGS_NAV)
        || !m_title.Create(_T("Settings"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_subtitle.Create(EMULENEXT_PRODUCT_WITH_CORE_TEXT, WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_sectionTitle.Create(_T("Appearance"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_sectionDescription.Create(_T("Choose how eMule Next looks and which intelligence indicators are visible."), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_themeLabel.Create(_T("Theme"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_theme.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | CBS_DROPDOWNLIST, empty, this, IDC_EN_THEME)
        || !m_etaHealth.Create(_T("Show Smart ETA and Health indicators"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX, empty, this, IDC_EN_ETA_HEALTH)
        || !m_peerDiscovery.Create(_T("Automatically learn from peers that allow shared-file browsing"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX, empty, this, IDC_EN_DISCOVERY)
        || !m_peerConcurrencyLabel.Create(_T("Concurrent peer requests"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_peerConcurrency.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | CBS_DROPDOWNLIST, empty, this, IDC_EN_CONCURRENCY)
        || !m_peerPrivacyNote.Create(_T("Uses normal eMule shared-file functionality. Denied peers and cooldowns are respected automatically."), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_schedulerModeLabel.Create(_T("Smart Scheduling mode"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_schedulerMode.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | CBS_DROPDOWNLIST, empty, this, IDC_EN_SCHEDULER_MODE)
        || !m_schedulerProfileLabel.Create(_T("Profile"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_schedulerProfile.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | CBS_DROPDOWNLIST, empty, this, IDC_EN_SCHED_PROFILE)
        || !m_sourceDiscovery.Create(_T("Source discovery intelligence"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX, empty, this, IDC_EN_SCHED_DISCOVERY)
        || !m_a4af.Create(_T("A4AF intelligence"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX, empty, this, IDC_EN_SCHED_A4AF)
        || !m_rareParts.Create(_T("Rare-part intelligence"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX, empty, this, IDC_EN_SCHED_RARE)
        || !m_schedulerSafety.Create(_T("Analysis only is the safe default. Automatic intervention is always an explicit opt-in."), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_customTuning.Create(_T("Use custom scheduler tuning"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX, empty, this, IDC_EN_CUSTOM_TUNING)
        || !m_cooldownLabel.Create(_T("Intervention cooldown (seconds)"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_cooldown.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | CBS_DROPDOWNLIST, empty, this, IDC_EN_SCHED_COOLDOWN)
        || !m_batchLabel.Create(_T("Files analysed per pass"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_batch.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | CBS_DROPDOWNLIST, empty, this, IDC_EN_SCHED_BATCH)
        || !m_a4afThresholdLabel.Create(_T("Minimum A4AF intelligence score"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_a4afThreshold.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | CBS_DROPDOWNLIST, empty, this, IDC_EN_SCHED_A4AF_THRESHOLD)
        || !m_advancedNote.Create(_T("History and scheduler telemetry are bounded internal services in Preview 2. Their storage limits are managed automatically."), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_apply.Create(_T("Apply changes"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_DEFPUSHBUTTON, empty, this, IDC_EN_APPLY)
        || !m_status.Create(_T(""), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)) {
        return -1;
    }

    m_navigation.AddString(_T("Appearance"));
    m_navigation.AddString(_T("Peer knowledge"));
    m_navigation.AddString(_T("Intelligence"));
    m_navigation.AddString(_T("Advanced"));
    m_navigation.SetCurSel(0);

    m_theme.AddString(_T("System"));
    m_theme.AddString(_T("Light"));
    m_theme.AddString(_T("Dark"));
    m_peerConcurrency.AddString(_T("Automatic (recommended)"));
    m_peerConcurrency.AddString(_T("1"));
    m_peerConcurrency.AddString(_T("2"));
    m_peerConcurrency.AddString(_T("4"));
    m_peerConcurrency.AddString(_T("8"));

    m_schedulerMode.AddString(_T("Analysis only - observe and recommend"));
    m_schedulerMode.AddString(_T("Assist - recommendations and selected actions"));
    m_schedulerMode.AddString(_T("Automatic - allow interventions"));
    m_schedulerProfile.AddString(_T("Conservative"));
    m_schedulerProfile.AddString(_T("Balanced"));
    m_schedulerProfile.AddString(_T("Responsive"));
    FillNumberCombo(m_cooldown, kCooldownValues, _countof(kCooldownValues));
    FillNumberCombo(m_batch, kBatchValues, _countof(kBatchValues));
    FillNumberCombo(m_a4afThreshold, kA4AFValues, _countof(kA4AFValues));

    CEmuleNextModernUi::ApplyFont(this, m_normalFont, m_titleFont, m_sectionFont);
    SetPageFonts();
    CEmuleNextModernUi::ApplyCombo(m_theme);
    CEmuleNextModernUi::ApplyCombo(m_peerConcurrency);
    CEmuleNextModernUi::ApplyCombo(m_schedulerMode);
    CEmuleNextModernUi::ApplyCombo(m_schedulerProfile);
    CEmuleNextModernUi::ApplyCombo(m_cooldown);
    CEmuleNextModernUi::ApplyCombo(m_batch);
    CEmuleNextModernUi::ApplyCombo(m_a4afThreshold);
    CEmuleNextModernUi::SetExplorerTheme(m_navigation.m_hWnd);

    Refresh();
    CEmuleNextTheme::ApplyToWindow(m_hWnd);
    return 0;
}

void CEmuleNextSettingsWnd::SetPageFonts()
{
    CWnd* normalControls[] = {
        &m_navigation, &m_subtitle, &m_sectionDescription, &m_themeLabel, &m_theme, &m_etaHealth,
        &m_peerDiscovery, &m_peerConcurrencyLabel, &m_peerConcurrency, &m_peerPrivacyNote,
        &m_schedulerModeLabel, &m_schedulerMode, &m_schedulerProfileLabel, &m_schedulerProfile,
        &m_sourceDiscovery, &m_a4af, &m_rareParts, &m_schedulerSafety, &m_customTuning,
        &m_cooldownLabel, &m_cooldown, &m_batchLabel, &m_batch, &m_a4afThresholdLabel,
        &m_a4afThreshold, &m_advancedNote, &m_apply, &m_status
    };
    for (int i = 0; i < _countof(normalControls); ++i)
        normalControls[i]->SetFont(&m_normalFont);
    m_title.SetFont(&m_titleFont);
    m_sectionTitle.SetFont(&m_sectionFont);
}

void CEmuleNextSettingsWnd::Refresh()
{
    if (!::IsWindow(m_hWnd))
        return;

    m_theme.SetCurSel(static_cast<int>(CEmuleNextTheme::GetMode()));
    m_etaHealth.SetCheck(theApp.GetProfileInt(_T("eMule Next"), _T("SmartEtaHealthDisplay"), 1) ? BST_CHECKED : BST_UNCHECKED);
    m_peerDiscovery.SetCheck(theApp.GetProfileInt(_T("eMule Next"), _T("PeerShareDiscovery"), 1) ? BST_CHECKED : BST_UNCHECKED);

    const int concurrency = ClampInt(static_cast<int>(theApp.GetProfileInt(_T("eMule Next"), _T("PeerShareMaxConcurrent"), 2)), 1, 8);
    int concurrencySelection = 0;
    if (concurrency == 1) concurrencySelection = 1;
    else if (concurrency == 2) concurrencySelection = 2;
    else if (concurrency <= 4) concurrencySelection = 3;
    else concurrencySelection = 4;
    m_peerConcurrency.SetCurSel(concurrencySelection);

    const int mode = ClampInt(static_cast<int>(theApp.GetProfileInt(_T("eMule Next"), _T("SmartSchedulingMode"), ENSM_ANALYSIS_ONLY)), ENSM_ANALYSIS_ONLY, ENSM_AUTOMATIC);
    m_schedulerMode.SetCurSel(mode);
    m_schedulerProfile.SetCurSel(ClampInt(static_cast<int>(theApp.GetProfileInt(_T("eMule Next"), _T("SmartSchedulerProfile"), 1)), 0, 2));
    m_sourceDiscovery.SetCheck(theApp.GetProfileInt(_T("eMule Next"), _T("SmartSourceDiscovery"), 1) ? BST_CHECKED : BST_UNCHECKED);
    m_a4af.SetCheck(theApp.GetProfileInt(_T("eMule Next"), _T("SmartA4AF"), 1) ? BST_CHECKED : BST_UNCHECKED);
    m_rareParts.SetCheck(theApp.GetProfileInt(_T("eMule Next"), _T("SmartRareParts"), 1) ? BST_CHECKED : BST_UNCHECKED);

    const bool custom = theApp.GetProfileInt(_T("eMule Next"), _T("SmartCustomTuning"), 0) != 0;
    m_customTuning.SetCheck(custom ? BST_CHECKED : BST_UNCHECKED);
    SelectNumber(m_cooldown, kCooldownValues, _countof(kCooldownValues), static_cast<int>(theApp.GetProfileInt(_T("eMule Next"), _T("SmartSchedulerCooldown"), 90)));
    SelectNumber(m_batch, kBatchValues, _countof(kBatchValues), static_cast<int>(theApp.GetProfileInt(_T("eMule Next"), _T("SmartSchedulerMaxFilesPerRound"), 8)));
    SelectNumber(m_a4afThreshold, kA4AFValues, _countof(kA4AFValues), static_cast<int>(theApp.GetProfileInt(_T("eMule Next"), _T("SmartA4AFMinimumScore"), 650)));

    ShowCategory(m_category);
    UpdateEnabledState();
}

void CEmuleNextSettingsWnd::OnCategoryChanged()
{
    const int selection = m_navigation.GetCurSel();
    if (selection >= 0 && selection < CATEGORY_COUNT) {
        m_category = static_cast<Category>(selection);
        ShowCategory(m_category);
        Invalidate(FALSE);
    }
}

void CEmuleNextSettingsWnd::ShowCategory(Category category)
{
    CWnd* appearance[] = { &m_themeLabel, &m_theme, &m_etaHealth };
    CWnd* peers[] = { &m_peerDiscovery, &m_peerConcurrencyLabel, &m_peerConcurrency, &m_peerPrivacyNote };
    CWnd* intelligence[] = { &m_schedulerModeLabel, &m_schedulerMode, &m_schedulerProfileLabel, &m_schedulerProfile,
        &m_sourceDiscovery, &m_a4af, &m_rareParts, &m_schedulerSafety };
    CWnd* advanced[] = { &m_customTuning, &m_cooldownLabel, &m_cooldown, &m_batchLabel, &m_batch,
        &m_a4afThresholdLabel, &m_a4afThreshold, &m_advancedNote };

    for (int i = 0; i < _countof(appearance); ++i) appearance[i]->ShowWindow(category == CATEGORY_APPEARANCE ? SW_SHOW : SW_HIDE);
    for (int i = 0; i < _countof(peers); ++i) peers[i]->ShowWindow(category == CATEGORY_PEERS ? SW_SHOW : SW_HIDE);
    for (int i = 0; i < _countof(intelligence); ++i) intelligence[i]->ShowWindow(category == CATEGORY_INTELLIGENCE ? SW_SHOW : SW_HIDE);
    for (int i = 0; i < _countof(advanced); ++i) advanced[i]->ShowWindow(category == CATEGORY_ADVANCED ? SW_SHOW : SW_HIDE);

    CString title;
    CString description;
    switch (category) {
    case CATEGORY_APPEARANCE:
        title = _T("Appearance");
        description = _T("Theme and presentation options. System mode follows the Windows appearance setting.");
        break;
    case CATEGORY_PEERS:
        title = _T("Peer knowledge");
        description = _T("Control passive knowledge collection through the existing eMule shared-file capability.");
        break;
    case CATEGORY_INTELLIGENCE:
        title = _T("Intelligence");
        description = _T("Choose how far Smart Scheduling may go. Analysis only remains the recommended default.");
        break;
    default:
        title = _T("Advanced");
        description = _T("Optional expert overrides. Leave custom tuning off to use bounded profile defaults.");
        break;
    }
    m_sectionTitle.SetWindowText(title);
    m_sectionDescription.SetWindowText(description);
    CRect rect;
    GetClientRect(&rect);
    LayoutControls(rect.Width(), rect.Height());
}

void CEmuleNextSettingsWnd::UpdateEnabledState()
{
    const bool schedulingEnabled = m_schedulerMode.GetCurSel() >= ENSM_ANALYSIS_ONLY;
    m_schedulerProfile.EnableWindow(schedulingEnabled ? TRUE : FALSE);
    m_sourceDiscovery.EnableWindow(schedulingEnabled ? TRUE : FALSE);
    m_a4af.EnableWindow(schedulingEnabled ? TRUE : FALSE);
    m_rareParts.EnableWindow(schedulingEnabled ? TRUE : FALSE);

    const BOOL custom = m_customTuning.GetCheck() == BST_CHECKED ? TRUE : FALSE;
    m_cooldown.EnableWindow(custom);
    m_batch.EnableWindow(custom);
    m_a4afThreshold.EnableWindow(custom);
}

void CEmuleNextSettingsWnd::OnSchedulingModeChanged()
{
    UpdateEnabledState();
}

void CEmuleNextSettingsWnd::OnCustomTuningChanged()
{
    UpdateEnabledState();
}

void CEmuleNextSettingsWnd::OnApplyClicked()
{
    int theme = m_theme.GetCurSel();
    if (theme < ENTM_SYSTEM || theme > ENTM_DARK)
        theme = ENTM_SYSTEM;
    CEmuleNextTheme::SetMode(static_cast<EmuleNextThemeMode>(theme));

    theApp.WriteProfileInt(_T("eMule Next"), _T("SmartEtaHealthDisplay"), m_etaHealth.GetCheck() == BST_CHECKED ? 1 : 0);
    const bool discovery = m_peerDiscovery.GetCheck() == BST_CHECKED;
    theApp.WriteProfileInt(_T("eMule Next"), _T("PeerShareDiscovery"), discovery ? 1 : 0);
    int concurrency = 2;
    switch (m_peerConcurrency.GetCurSel()) {
    case 1: concurrency = 1; break;
    case 2: concurrency = 2; break;
    case 3: concurrency = 4; break;
    case 4: concurrency = 8; break;
    default: concurrency = 2; break;
    }
    theApp.WriteProfileInt(_T("eMule Next"), _T("PeerShareMaxConcurrent"), concurrency);
    if (theApp.clientlist != NULL) {
        theApp.clientlist->SetPeerShareDiscoveryEnabled(discovery);
        theApp.clientlist->SetPeerShareMaxConcurrent(static_cast<uint32>(concurrency));
    }

    int mode = m_schedulerMode.GetCurSel();
    if (mode < ENSM_ANALYSIS_ONLY || mode > ENSM_AUTOMATIC)
        mode = ENSM_ANALYSIS_ONLY;
    theApp.WriteProfileInt(_T("eMule Next"), _T("SmartSchedulingMode"), mode);
    int profile = m_schedulerProfile.GetCurSel();
    if (profile < 0 || profile > 2) profile = 1;
    theApp.WriteProfileInt(_T("eMule Next"), _T("SmartSchedulerProfile"), profile);
    theApp.WriteProfileInt(_T("eMule Next"), _T("SmartSourceDiscovery"), m_sourceDiscovery.GetCheck() == BST_CHECKED ? 1 : 0);
    theApp.WriteProfileInt(_T("eMule Next"), _T("SmartA4AF"), m_a4af.GetCheck() == BST_CHECKED ? 1 : 0);
    theApp.WriteProfileInt(_T("eMule Next"), _T("SmartRareParts"), m_rareParts.GetCheck() == BST_CHECKED ? 1 : 0);

    const bool custom = m_customTuning.GetCheck() == BST_CHECKED;
    theApp.WriteProfileInt(_T("eMule Next"), _T("SmartCustomTuning"), custom ? 1 : 0);
    if (custom) {
        theApp.WriteProfileInt(_T("eMule Next"), _T("SmartSchedulerCooldown"), SelectedNumber(m_cooldown, kCooldownValues, _countof(kCooldownValues), 90));
        theApp.WriteProfileInt(_T("eMule Next"), _T("SmartSchedulerMaxFilesPerRound"), SelectedNumber(m_batch, kBatchValues, _countof(kBatchValues), 8));
        theApp.WriteProfileInt(_T("eMule Next"), _T("SmartA4AFMinimumScore"), SelectedNumber(m_a4afThreshold, kA4AFValues, _countof(kA4AFValues), 650));
    }
    else {
        // Zero means: use the selected profile's bounded defaults. The batch size
        // has no profile-specific fallback in the legacy scheduler, so keep 8.
        theApp.WriteProfileInt(_T("eMule Next"), _T("SmartSchedulerCooldown"), 0);
        theApp.WriteProfileInt(_T("eMule Next"), _T("SmartSchedulerMaxFilesPerRound"), 8);
        theApp.WriteProfileInt(_T("eMule Next"), _T("SmartA4AFMinimumScore"), 0);
    }

    // Preview 2 treats history and scheduler telemetry as bounded product
    // services rather than end-user tuning knobs.
    theApp.WriteProfileInt(_T("eMule Next"), _T("SmartHistoryCache"), 1);
    theApp.WriteProfileInt(_T("eMule Next"), _T("SmartHistoryCacheCapacity"), 4096);
    theApp.WriteProfileInt(_T("eMule Next"), _T("SmartTelemetry"), 1);
    theApp.WriteProfileInt(_T("eMule Next"), _T("SmartTelemetryCapacity"), 256);

    CEmuleNextTheme::ApplyToWindow(GetParent() != NULL ? GetParent()->m_hWnd : m_hWnd);
    m_status.SetWindowText(_T("Settings saved. Changes that affect active peers are applied immediately."));
    Invalidate(FALSE);
}

BOOL CEmuleNextSettingsWnd::PreTranslateMessage(MSG* message)
{
    if (message != NULL && message->message == WM_KEYDOWN && message->wParam == VK_RETURN
        && (::GetKeyState(VK_CONTROL) & 0x8000) != 0) {
        OnApplyClicked();
        return TRUE;
    }
    return CWnd::PreTranslateMessage(message);
}

void CEmuleNextSettingsWnd::OnSize(UINT type, int cx, int cy)
{
    CWnd::OnSize(type, cx, cy);
    if (::IsWindow(m_navigation.m_hWnd))
        LayoutControls(cx, cy);
}

void CEmuleNextSettingsWnd::LayoutControls(int cx, int cy)
{
    const int margin = CEmuleNextModernUi::PageMargin(m_hWnd);
    const int navWidth = CEmuleNextModernUi::NavigationWidth(m_hWnd);
    const int gap = CEmuleNextModernUi::ControlGap(m_hWnd);
    const int sectionGap = CEmuleNextModernUi::SectionGap(m_hWnd);
    const int controlHeight = CEmuleNextModernUi::ControlHeight(m_hWnd);
    const int compactHeight = CEmuleNextModernUi::CompactHeight(m_hWnd);
    const int titleHeight = CEmuleNextModernUi::Scale(m_hWnd, 34);
    const int descriptionHeight = CEmuleNextModernUi::Scale(m_hWnd, 42);
    const int contentLeft = margin + navWidth + sectionGap;
    const int contentWidth = max(CEmuleNextModernUi::Scale(m_hWnd, 360), cx - contentLeft - margin);
    const int fieldWidth = min(CEmuleNextModernUi::Scale(m_hWnd, 360), contentWidth - CEmuleNextModernUi::Scale(m_hWnd, 24));

    m_navigation.MoveWindow(margin, margin + titleHeight + gap, navWidth, max(CEmuleNextModernUi::Scale(m_hWnd, 220), cy - margin * 2 - titleHeight - gap));
    m_title.MoveWindow(contentLeft, margin, contentWidth, titleHeight);
    m_subtitle.MoveWindow(contentLeft, margin + titleHeight, contentWidth, compactHeight);

    int y = margin + titleHeight + compactHeight + sectionGap;
    m_sectionTitle.MoveWindow(contentLeft + gap, y, contentWidth - gap * 2, compactHeight);
    y += compactHeight;
    m_sectionDescription.MoveWindow(contentLeft + gap, y, contentWidth - gap * 2, descriptionHeight);
    y += descriptionHeight + sectionGap;

    const int x = contentLeft + CEmuleNextModernUi::Scale(m_hWnd, 18);
    const int width = contentWidth - CEmuleNextModernUi::Scale(m_hWnd, 36);

    if (m_category == CATEGORY_APPEARANCE) {
        m_themeLabel.MoveWindow(x, y, width, compactHeight); y += compactHeight;
        m_theme.MoveWindow(x, y, fieldWidth, CEmuleNextModernUi::Scale(m_hWnd, 220)); y += controlHeight + sectionGap;
        m_etaHealth.MoveWindow(x, y, width, controlHeight);
    }
    else if (m_category == CATEGORY_PEERS) {
        m_peerDiscovery.MoveWindow(x, y, width, controlHeight); y += controlHeight + gap;
        m_peerConcurrencyLabel.MoveWindow(x, y, width, compactHeight); y += compactHeight;
        m_peerConcurrency.MoveWindow(x, y, fieldWidth, CEmuleNextModernUi::Scale(m_hWnd, 220)); y += controlHeight + sectionGap;
        m_peerPrivacyNote.MoveWindow(x, y, width, descriptionHeight);
    }
    else if (m_category == CATEGORY_INTELLIGENCE) {
        m_schedulerModeLabel.MoveWindow(x, y, width, compactHeight); y += compactHeight;
        m_schedulerMode.MoveWindow(x, y, fieldWidth, CEmuleNextModernUi::Scale(m_hWnd, 220)); y += controlHeight + gap;
        m_schedulerProfileLabel.MoveWindow(x, y, width, compactHeight); y += compactHeight;
        m_schedulerProfile.MoveWindow(x, y, fieldWidth, CEmuleNextModernUi::Scale(m_hWnd, 220)); y += controlHeight + sectionGap;
        m_sourceDiscovery.MoveWindow(x, y, width, controlHeight); y += controlHeight;
        m_a4af.MoveWindow(x, y, width, controlHeight); y += controlHeight;
        m_rareParts.MoveWindow(x, y, width, controlHeight); y += controlHeight + sectionGap;
        m_schedulerSafety.MoveWindow(x, y, width, descriptionHeight);
    }
    else {
        m_customTuning.MoveWindow(x, y, width, controlHeight); y += controlHeight + gap;
        m_cooldownLabel.MoveWindow(x, y, width, compactHeight); y += compactHeight;
        m_cooldown.MoveWindow(x, y, fieldWidth, CEmuleNextModernUi::Scale(m_hWnd, 220)); y += controlHeight + gap;
        m_batchLabel.MoveWindow(x, y, width, compactHeight); y += compactHeight;
        m_batch.MoveWindow(x, y, fieldWidth, CEmuleNextModernUi::Scale(m_hWnd, 220)); y += controlHeight + gap;
        m_a4afThresholdLabel.MoveWindow(x, y, width, compactHeight); y += compactHeight;
        m_a4afThreshold.MoveWindow(x, y, fieldWidth, CEmuleNextModernUi::Scale(m_hWnd, 220)); y += controlHeight + sectionGap;
        m_advancedNote.MoveWindow(x, y, width, descriptionHeight);
    }

    const int actionWidth = CEmuleNextModernUi::Scale(m_hWnd, 150);
    const int actionY = max(y + sectionGap, cy - margin - controlHeight);
    m_apply.MoveWindow(contentLeft + contentWidth - actionWidth, actionY, actionWidth, controlHeight);
    m_status.MoveWindow(contentLeft + gap, actionY, max(0, contentWidth - actionWidth - gap * 3), controlHeight);
}

void CEmuleNextSettingsWnd::OnPaint()
{
    CPaintDC dc(this);
    CRect client;
    GetClientRect(&client);
    CEmuleNextModernUi::DrawPageBackground(dc, client);

    const int margin = CEmuleNextModernUi::PageMargin(m_hWnd);
    const int navWidth = CEmuleNextModernUi::NavigationWidth(m_hWnd);
    const int sectionGap = CEmuleNextModernUi::SectionGap(m_hWnd);
    CRect navRect(margin - CEmuleNextModernUi::Scale(m_hWnd, 6), margin,
        margin + navWidth + CEmuleNextModernUi::Scale(m_hWnd, 6), client.bottom - margin);
    CEmuleNextModernUi::DrawRoundedCard(dc, navRect, CEmuleNextModernUi::NavigationColor(), CEmuleNextModernUi::BorderColor(), CEmuleNextModernUi::CardRadius(m_hWnd));

    const int contentLeft = margin + navWidth + sectionGap;
    CRect card(contentLeft, margin + CEmuleNextModernUi::Scale(m_hWnd, 72), client.right - margin,
        client.bottom - margin - CEmuleNextModernUi::Scale(m_hWnd, 48));
    CEmuleNextModernUi::DrawRoundedCard(dc, card, CEmuleNextModernUi::CardColor(), CEmuleNextModernUi::BorderColor(), CEmuleNextModernUi::CardRadius(m_hWnd));
}

BOOL CEmuleNextSettingsWnd::OnEraseBkgnd(CDC*)
{
    return TRUE;
}

HBRUSH CEmuleNextSettingsWnd::OnCtlColor(CDC* dc, CWnd* wnd, UINT ctlColor)
{
    dc->SetTextColor(CEmuleNextModernUi::TextColor());
    dc->SetBkMode(TRANSPARENT);
    if (wnd != NULL && wnd->m_hWnd == m_subtitle.m_hWnd)
        dc->SetTextColor(CEmuleNextModernUi::MutedTextColor());
    if (wnd != NULL && (wnd->m_hWnd == m_sectionDescription.m_hWnd || wnd->m_hWnd == m_peerPrivacyNote.m_hWnd
        || wnd->m_hWnd == m_schedulerSafety.m_hWnd || wnd->m_hWnd == m_advancedNote.m_hWnd || wnd->m_hWnd == m_status.m_hWnd))
        dc->SetTextColor(CEmuleNextModernUi::MutedTextColor());
    if (ctlColor == CTLCOLOR_STATIC || ctlColor == CTLCOLOR_DLG)
        return static_cast<HBRUSH>(m_backgroundBrush.GetSafeHandle());
    return CWnd::OnCtlColor(dc, wnd, ctlColor);
}
