//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#include "stdafx.h"
#include "EmuleNextDiagnosticsWnd.h"
#include "EmuleNextTheme.h"
#include "EmuleNextModernUi.h"
#include "EmuleNextStressDiagnostics.h"
#include "EmuleNextSmartScheduler.h"
#include "EmuleNextVersion.h"
#include "emule.h"

#include <afxdlgs.h>
#include <memory>

namespace
{
    enum
    {
        IDC_EN_DIAG_REFRESH = 0x7ED0,
        IDC_EN_DIAG_CHECK,
        IDC_EN_DIAG_BACKUP,
        IDC_EN_DIAG_RESTORE,
        IDC_EN_DIAG_PRUNE,
        IDC_EN_DIAG_CHECKPOINT,
        IDC_EN_DIAG_OPEN,
        IDC_EN_DIAG_STRESS,
        IDC_EN_DIAG_TESTS,
        IDC_EN_DIAG_TEST_PASS,
        IDC_EN_DIAG_TEST_FAIL,
        IDC_EN_DIAG_TEST_RESET,
        IDC_EN_DIAG_EXPORT
    };

    const UINT WM_EN_DIAG_RESULT = WM_APP + 0x5D8;
    enum MaintenanceAction
    {
        ENMA_REFRESH = 0,
        ENMA_FULL_CHECK,
        ENMA_BACKUP,
        ENMA_RESTORE,
        ENMA_PRUNE,
        ENMA_CHECKPOINT,
        ENMA_STRESS
    };

    struct MaintenanceContext
    {
        HWND target;
        int action;
        CStringW path;
        MaintenanceContext() : target(NULL), action(ENMA_REFRESH) {}
    };

    struct MaintenanceResult
    {
        bool ok;
        int action;
        CStringW message;
        EmuleNextDatabaseDiagnostics snapshot;
        MaintenanceResult() : ok(false), action(ENMA_REFRESH) {}
    };

    struct RuntimeTestDefinition
    {
        LPCTSTR id;
        LPCTSTR title;
        LPCTSTR description;
    };

    const RuntimeTestDefinition kRuntimeTests[] = {
        { _T("ED2K-01"), _T("eD2K server and download"), _T("Connect, discover sources and transfer data through the legacy server path.") },
        { _T("KAD-01"), _T("Kad network and search"), _T("Connect to Kad, search and discover sources without protocol regression.") },
        { _T("UP-01"), _T("Upload to legacy peer"), _T("Complete a real upload slot/session to another eMule-compatible peer.") },
        { _T("SHARE-01"), _T("View Shared Files"), _T("Manual peer browse opens the classic tab; automatic discovery does not create extra tabs.") },
        { _T("PAUSE-01"), _T("Pause / resume / restart"), _T("Incomplete downloads survive pause, resume and application restart.") },
        { _T("SCHED-01"), _T("Scheduler modes"), _T("Analysis, Assist and Automatic behave within their documented safety boundaries.") },
        { _T("A4AF-01"), _T("A4AF intervention"), _T("A4AF remains compatible and intervention telemetry is recorded correctly.") },
        { _T("RARE-01"), _T("Rare-part selection"), _T("Automatic rare-part behavior does not break normal part selection.") },
        { _T("HASH-01"), _T("Hashing and recovery"), _T("Hashing, checking, completion and Library relink preserve exact eD2K identity.") },
        { _T("UI-01"), _T("Preview 2 UI / DPI"), _T("Core Preview 2 workspaces remain usable at 100, 125, 150, 175 and 200 percent DPI.") }
    };

    UINT AFX_CDECL MaintenanceWorker(LPVOID value)
    {
        std::unique_ptr<MaintenanceContext> context(static_cast<MaintenanceContext*>(value));
        std::unique_ptr<MaintenanceResult> result(new MaintenanceResult);
        result->action = context->action;
        switch (context->action) {
        case ENMA_REFRESH:
            result->ok = theEmuleNext.LoadDatabaseDiagnostics(result->snapshot);
            result->message = result->ok ? L"Diagnostics refreshed." : L"Database diagnostics unavailable.";
            break;
        case ENMA_FULL_CHECK:
            result->ok = theEmuleNext.RunDatabaseIntegrityCheck(true, result->message);
            theEmuleNext.LoadDatabaseDiagnostics(result->snapshot);
            break;
        case ENMA_BACKUP:
        {
            CStringW backupPath;
            result->ok = theEmuleNext.CreateDatabaseBackup(L"manual", backupPath, result->message);
            theEmuleNext.LoadDatabaseDiagnostics(result->snapshot);
            break;
        }
        case ENMA_RESTORE:
            result->ok = theEmuleNext.RestoreDatabaseBackup(context->path, result->message);
            theEmuleNext.LoadDatabaseDiagnostics(result->snapshot);
            break;
        case ENMA_PRUNE:
        {
            uint64 removed = 0;
            result->ok = theEmuleNext.PruneDatabaseTelemetry(removed, result->message);
            theEmuleNext.LoadDatabaseDiagnostics(result->snapshot);
            break;
        }
        case ENMA_CHECKPOINT:
            result->ok = theEmuleNext.CheckpointDatabase(result->message);
            theEmuleNext.LoadDatabaseDiagnostics(result->snapshot);
            break;
        case ENMA_STRESS:
        {
            EmuleNextStressDiagnosticsResult stress;
            result->ok = CEmuleNextStressDiagnostics::RunIndexStress(10000, 5000, stress);
            if (result->ok)
                result->ok = CEmuleNextStressDiagnostics::RunWriterQueueStress(10000, stress);
            result->message = stress.details;
            theEmuleNext.LoadDatabaseDiagnostics(result->snapshot);
            break;
        }
        }
        if (::IsWindow(context->target)
            && ::PostMessage(context->target, WM_EN_DIAG_RESULT, 0, reinterpret_cast<LPARAM>(result.get()))) {
            result.release();
        }
        return 0;
    }

    CString SizeText(uint64 bytes)
    {
        CString value;
        if (bytes >= 1024ui64 * 1024ui64)
            value.Format(_T("%.1f MB"), static_cast<double>(bytes) / (1024.0 * 1024.0));
        else if (bytes >= 1024ui64)
            value.Format(_T("%.1f KB"), static_cast<double>(bytes) / 1024.0);
        else
            value.Format(_T("%I64u B"), bytes);
        return value;
    }

    CString TimeText(uint64 timestamp)
    {
        if (timestamp == 0)
            return _T("Never");
        CTime value(static_cast<time_t>(timestamp));
        return value.Format(_T("%Y-%m-%d %H:%M"));
    }
}

BEGIN_MESSAGE_MAP(CEmuleNextDiagnosticsWnd, CWnd)
    ON_WM_CREATE()
    ON_WM_SIZE()
    ON_WM_PAINT()
    ON_WM_ERASEBKGND()
    ON_WM_CTLCOLOR()
    ON_BN_CLICKED(IDC_EN_DIAG_REFRESH, OnRefreshClicked)
    ON_BN_CLICKED(IDC_EN_DIAG_CHECK, OnCheckClicked)
    ON_BN_CLICKED(IDC_EN_DIAG_BACKUP, OnBackupClicked)
    ON_BN_CLICKED(IDC_EN_DIAG_RESTORE, OnRestoreClicked)
    ON_BN_CLICKED(IDC_EN_DIAG_PRUNE, OnPruneClicked)
    ON_BN_CLICKED(IDC_EN_DIAG_CHECKPOINT, OnCheckpointClicked)
    ON_BN_CLICKED(IDC_EN_DIAG_OPEN, OnOpenBackupsClicked)
    ON_BN_CLICKED(IDC_EN_DIAG_STRESS, OnStressClicked)
    ON_NOTIFY(LVN_ITEMCHANGED, IDC_EN_DIAG_TESTS, OnTestSelectionChanged)
    ON_BN_CLICKED(IDC_EN_DIAG_TEST_PASS, OnTestPassClicked)
    ON_BN_CLICKED(IDC_EN_DIAG_TEST_FAIL, OnTestFailClicked)
    ON_BN_CLICKED(IDC_EN_DIAG_TEST_RESET, OnTestResetClicked)
    ON_BN_CLICKED(IDC_EN_DIAG_EXPORT, OnExportClicked)
    ON_MESSAGE(WM_EN_DIAG_RESULT, OnMaintenanceResult)
END_MESSAGE_MAP()

CEmuleNextDiagnosticsWnd::CEmuleNextDiagnosticsWnd()
    : m_busy(false)
{
}

CEmuleNextDiagnosticsWnd::~CEmuleNextDiagnosticsWnd()
{
}

bool CEmuleNextDiagnosticsWnd::Create(CWnd* parent)
{
    if (parent == NULL)
        return false;
    const CString className = AfxRegisterWndClass(CS_DBLCLKS, ::LoadCursor(NULL, IDC_ARROW),
        reinterpret_cast<HBRUSH>(COLOR_WINDOW + 1), NULL);
    CRect empty(0, 0, 0, 0);
    return CWnd::CreateEx(0, className, _T("eMule Next Preview 2 Diagnostics"),
        WS_CHILD | WS_CLIPCHILDREN | WS_CLIPSIBLINGS, empty, parent, 0) != FALSE;
}

int CEmuleNextDiagnosticsWnd::OnCreate(LPCREATESTRUCT createStruct)
{
    if (CWnd::OnCreate(createStruct) == -1)
        return -1;

    m_backgroundBrush.CreateSolidBrush(CEmuleNextModernUi::WindowColor());
    CRect empty(0, 0, 0, 0);
    if (!m_title.Create(_T("Diagnostics"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_subtitle.Create(EMULENEXT_PRODUCT_WITH_CORE_TEXT _T(" - health, recovery and runtime validation"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_databaseCard.Create(_T(""), WS_CHILD | WS_VISIBLE | SS_OWNERDRAW, empty, this)
        || !m_queueCard.Create(_T(""), WS_CHILD | WS_VISIBLE | SS_OWNERDRAW, empty, this)
        || !m_schedulerCard.Create(_T(""), WS_CHILD | WS_VISIBLE | SS_OWNERDRAW, empty, this)
        || !m_performanceCard.Create(_T(""), WS_CHILD | WS_VISIBLE | SS_OWNERDRAW, empty, this)
        || !m_databaseSection.Create(_T("Database maintenance"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_refresh.Create(_T("Refresh"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DIAG_REFRESH)
        || !m_check.Create(_T("Check database"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DIAG_CHECK)
        || !m_backup.Create(_T("Create backup"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DIAG_BACKUP)
        || !m_restore.Create(_T("Restore..."), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DIAG_RESTORE)
        || !m_prune.Create(_T("Prune telemetry"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DIAG_PRUNE)
        || !m_checkpoint.Create(_T("Checkpoint WAL"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DIAG_CHECKPOINT)
        || !m_openBackups.Create(_T("Open backups"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DIAG_OPEN)
        || !m_stress.Create(_T("Run stress self-test"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DIAG_STRESS)
        || !m_runtimeSection.Create(_T("Runtime validation"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_runtimeTests.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | LVS_REPORT | LVS_SINGLESEL | LVS_SHOWSELALWAYS, empty, this, IDC_EN_DIAG_TESTS)
        || !m_testPass.Create(_T("Mark pass"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DIAG_TEST_PASS)
        || !m_testFail.Create(_T("Mark fail"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DIAG_TEST_FAIL)
        || !m_testReset.Create(_T("Reset"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DIAG_TEST_RESET)
        || !m_export.Create(_T("Export report"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DIAG_EXPORT)
        || !m_actionStatus.Create(_T("Maintenance and stress actions run outside the GUI thread."), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)) {
        return -1;
    }

    CEmuleNextModernUi::ApplyFont(this, m_normalFont, m_titleFont, m_sectionFont);
    SetPageFonts();
    CEmuleNextModernUi::ApplyList(m_runtimeTests);
    m_runtimeTests.InsertColumn(0, _T("Test"), LVCFMT_LEFT, CEmuleNextModernUi::Scale(m_hWnd, 150));
    m_runtimeTests.InsertColumn(1, _T("State"), LVCFMT_LEFT, CEmuleNextModernUi::Scale(m_hWnd, 95));
    m_runtimeTests.InsertColumn(2, _T("What to validate"), LVCFMT_LEFT, CEmuleNextModernUi::Scale(m_hWnd, 520));
    PopulateRuntimeTests();

    m_databaseCard.SetContent(_T("Database"), _T("Loading"), _T("Schema, size, backups and integrity"));
    m_queueCard.SetContent(_T("Writer queue"), _T("Loading"), _T("Queued, processed, dropped and errors"));
    m_schedulerCard.SetContent(_T("Smart Scheduler"), _T("Loading"), _T("Runtime mode and tracked intelligence"));
    m_performanceCard.SetContent(_T("Performance self-test"), _T("Not run"), _T("10k clients, 5k downloads and 10k async DB writes"));
    CEmuleNextTheme::ApplyToWindow(m_hWnd);
    Refresh(true);
    return 0;
}

void CEmuleNextDiagnosticsWnd::SetPageFonts()
{
    CWnd* normal[] = { &m_subtitle, &m_refresh, &m_check, &m_backup, &m_restore, &m_prune, &m_checkpoint,
        &m_openBackups, &m_stress, &m_runtimeTests, &m_testPass, &m_testFail, &m_testReset, &m_export, &m_actionStatus };
    for (int i = 0; i < _countof(normal); ++i)
        normal[i]->SetFont(&m_normalFont);
    m_databaseCard.SetFont(&m_normalFont);
    m_queueCard.SetFont(&m_normalFont);
    m_schedulerCard.SetFont(&m_normalFont);
    m_performanceCard.SetFont(&m_normalFont);
    m_title.SetFont(&m_titleFont);
    m_databaseSection.SetFont(&m_sectionFont);
    m_runtimeSection.SetFont(&m_sectionFont);
}

void CEmuleNextDiagnosticsWnd::Refresh(bool force)
{
    if (::IsWindow(m_hWnd) && (!m_busy || force))
        StartAction(ENMA_REFRESH);
}

void CEmuleNextDiagnosticsWnd::StartAction(int action, const CStringW& path)
{
    if (m_busy)
        return;
    std::unique_ptr<MaintenanceContext> context(new MaintenanceContext);
    context->target = m_hWnd;
    context->action = action;
    context->path = path;
    m_busy = true;
    UpdateButtons();
    m_actionStatus.SetWindowText(_T("Working in background..."));
    if (AfxBeginThread(MaintenanceWorker, context.get(), THREAD_PRIORITY_BELOW_NORMAL) == NULL) {
        m_busy = false;
        UpdateButtons();
        m_actionStatus.SetWindowText(_T("Unable to start background worker."));
        return;
    }
    context.release();
}

void CEmuleNextDiagnosticsWnd::ApplySnapshot(const EmuleNextDatabaseDiagnostics& snapshot)
{
    m_snapshot = snapshot;

    CString dbValue;
    dbValue.Format(_T("%s - schema v%d"), static_cast<LPCTSTR>(CString(snapshot.status)), snapshot.schemaVersion);
    CString dbDetail;
    dbDetail.Format(_T("DB %s | WAL %s | %u backups | latest %s"),
        static_cast<LPCTSTR>(SizeText(snapshot.databaseBytes)), static_cast<LPCTSTR>(SizeText(snapshot.walBytes)),
        snapshot.backupCount, static_cast<LPCTSTR>(TimeText(snapshot.lastBackupAt)));
    const COLORREF dbAccent = snapshot.recoveryRequired ? CEmuleNextModernUi::ErrorColor() : CEmuleNextModernUi::SuccessColor();
    m_databaseCard.SetContent(_T("Database"), dbValue, dbDetail, dbAccent);

    CString queueValue;
    queueValue.Format(_T("%I64u queued"), snapshot.queue.queued);
    CString queueDetail;
    queueDetail.Format(_T("Peak %I64u | processed %I64u | dropped %I64u | errors %I64u"),
        snapshot.queue.peakQueued, snapshot.queue.processed, snapshot.queue.dropped, snapshot.queue.errors);
    const COLORREF queueAccent = snapshot.queue.dropped != 0 || snapshot.queue.errors != 0
        ? CEmuleNextModernUi::WarningColor() : CEmuleNextModernUi::SuccessColor();
    m_queueCard.SetContent(_T("Writer queue"), queueValue, queueDetail, queueAccent);

    const CString schedulerText = theEmuleNextScheduler.GetRuntimeStatusText();
    m_schedulerCard.SetContent(_T("Smart Scheduler"), schedulerText, _T("Analysis only remains the safe default; automatic intervention is opt-in."), CEmuleNextModernUi::AccentColor());

    CString perfValue = m_lastStressResult.IsEmpty() ? _T("Not run") : _T("Last run complete");
    CString perfDetail = m_lastStressResult.IsEmpty()
        ? _T("Runs bounded deterministic index and disposable writer-queue stress tests.")
        : m_lastStressResult;
    m_performanceCard.SetContent(_T("Performance self-test"), perfValue, perfDetail,
        m_lastStressResult.Find(_T("PASS")) >= 0 ? CEmuleNextModernUi::SuccessColor() : CLR_INVALID);
}

LRESULT CEmuleNextDiagnosticsWnd::OnMaintenanceResult(WPARAM, LPARAM value)
{
    std::unique_ptr<MaintenanceResult> result(reinterpret_cast<MaintenanceResult*>(value));
    m_busy = false;
    if (result.get() != NULL) {
        if (result->action == ENMA_STRESS)
            m_lastStressResult = CString(result->message);
        ApplySnapshot(result->snapshot);
        CString message(result->message);
        if (!result->ok)
            message = _T("Failed: ") + message;
        m_actionStatus.SetWindowText(message);
    }
    UpdateButtons();
    Invalidate(FALSE);
    return 0;
}

void CEmuleNextDiagnosticsWnd::PopulateRuntimeTests()
{
    m_runtimeTests.DeleteAllItems();
    for (int i = 0; i < _countof(kRuntimeTests); ++i) {
        const int state = static_cast<int>(theApp.GetProfileInt(_T("eMule Next Runtime Tests"), kRuntimeTests[i].id, 0));
        const int row = m_runtimeTests.InsertItem(i, kRuntimeTests[i].id);
        m_runtimeTests.SetItemText(row, 1, RuntimeTestStateText(state));
        m_runtimeTests.SetItemText(row, 2, kRuntimeTests[i].description);
    }
    UpdateButtons();
}

CString CEmuleNextDiagnosticsWnd::RuntimeTestKey(int row) const
{
    if (row < 0 || row >= _countof(kRuntimeTests))
        return CString();
    return CString(kRuntimeTests[row].id);
}

CString CEmuleNextDiagnosticsWnd::RuntimeTestStateText(int state) const
{
    if (state == 1) return _T("PASS");
    if (state == 2) return _T("FAIL");
    if (state == 3) return _T("RETEST");
    return _T("Not tested");
}

void CEmuleNextDiagnosticsWnd::SetRuntimeTestState(int state)
{
    const int row = m_runtimeTests.GetNextItem(-1, LVNI_SELECTED);
    const CString key = RuntimeTestKey(row);
    if (key.IsEmpty())
        return;
    theApp.WriteProfileInt(_T("eMule Next Runtime Tests"), key, state);
    m_runtimeTests.SetItemText(row, 1, RuntimeTestStateText(state));
}

void CEmuleNextDiagnosticsWnd::OnTestSelectionChanged(NMHDR*, LRESULT* result)
{
    UpdateButtons();
    if (result != NULL) *result = 0;
}

void CEmuleNextDiagnosticsWnd::OnTestPassClicked() { SetRuntimeTestState(1); }
void CEmuleNextDiagnosticsWnd::OnTestFailClicked() { SetRuntimeTestState(2); }
void CEmuleNextDiagnosticsWnd::OnTestResetClicked() { SetRuntimeTestState(0); }

void CEmuleNextDiagnosticsWnd::ExportDiagnosticsReport()
{
    CFileDialog dialog(FALSE, _T("txt"), _T("eMule-Next-Preview2-diagnostics.txt"),
        OFN_OVERWRITEPROMPT | OFN_HIDEREADONLY, _T("Text report (*.txt)|*.txt|All files (*.*)|*.*||"), this);
    dialog.m_ofn.lpstrTitle = _T("Export eMule Next diagnostics report");
    if (dialog.DoModal() != IDOK)
        return;

    CStdioFile file;
    if (!file.Open(dialog.GetPathName(), CFile::modeCreate | CFile::modeWrite | CFile::typeText)) {
        m_actionStatus.SetWindowText(_T("Unable to create diagnostics report."));
        return;
    }

    CString line;
    file.WriteString(EMULENEXT_PRODUCT_WITH_CORE_TEXT _T("\n"));
    file.WriteString(_T("Generated: ") + CTime::GetCurrentTime().Format(_T("%Y-%m-%d %H:%M:%S")) + _T("\n\n"));
    line.Format(_T("Database status: %s\nSchema: v%d\nDatabase bytes: %I64u\nWAL bytes: %I64u\nBackups: %u\n"),
        static_cast<LPCTSTR>(CString(m_snapshot.status)), m_snapshot.schemaVersion, m_snapshot.databaseBytes,
        m_snapshot.walBytes, m_snapshot.backupCount);
    file.WriteString(line);
    line.Format(_T("Writer queue: queued=%I64u peak=%I64u processed=%I64u dropped=%I64u errors=%I64u\n"),
        m_snapshot.queue.queued, m_snapshot.queue.peakQueued, m_snapshot.queue.processed,
        m_snapshot.queue.dropped, m_snapshot.queue.errors);
    file.WriteString(line);
    file.WriteString(_T("Scheduler: ") + theEmuleNextScheduler.GetRuntimeStatusText() + _T("\n"));
    file.WriteString(_T("Stress result: ") + (m_lastStressResult.IsEmpty() ? CString(_T("Not run")) : m_lastStressResult) + _T("\n\n"));
    file.WriteString(_T("Runtime validation\n"));
    for (int i = 0; i < _countof(kRuntimeTests); ++i) {
        const int state = static_cast<int>(theApp.GetProfileInt(_T("eMule Next Runtime Tests"), kRuntimeTests[i].id, 0));
        line.Format(_T("%s\t%s\t%s\n"), kRuntimeTests[i].id, static_cast<LPCTSTR>(RuntimeTestStateText(state)), kRuntimeTests[i].description);
        file.WriteString(line);
    }
    file.Close();
    m_actionStatus.SetWindowText(_T("Diagnostics report exported."));
}

void CEmuleNextDiagnosticsWnd::OnExportClicked()
{
    ExportDiagnosticsReport();
}

void CEmuleNextDiagnosticsWnd::UpdateButtons()
{
    const BOOL enabled = m_busy ? FALSE : TRUE;
    m_refresh.EnableWindow(enabled);
    m_check.EnableWindow(enabled);
    m_restore.EnableWindow(enabled);
    m_openBackups.EnableWindow(enabled);
    m_stress.EnableWindow(enabled);
    m_export.EnableWindow(enabled);
    const BOOL running = enabled && theEmuleNext.IsRunning();
    m_backup.EnableWindow(running);
    m_prune.EnableWindow(running);
    m_checkpoint.EnableWindow(running);
    const BOOL selected = enabled && m_runtimeTests.GetNextItem(-1, LVNI_SELECTED) >= 0;
    m_testPass.EnableWindow(selected);
    m_testFail.EnableWindow(selected);
    m_testReset.EnableWindow(selected);
}

void CEmuleNextDiagnosticsWnd::OnRefreshClicked() { StartAction(ENMA_REFRESH); }
void CEmuleNextDiagnosticsWnd::OnCheckClicked() { StartAction(ENMA_FULL_CHECK); }
void CEmuleNextDiagnosticsWnd::OnBackupClicked() { StartAction(ENMA_BACKUP); }
void CEmuleNextDiagnosticsWnd::OnPruneClicked() { StartAction(ENMA_PRUNE); }
void CEmuleNextDiagnosticsWnd::OnCheckpointClicked() { StartAction(ENMA_CHECKPOINT); }
void CEmuleNextDiagnosticsWnd::OnStressClicked() { StartAction(ENMA_STRESS); }

void CEmuleNextDiagnosticsWnd::OnRestoreClicked()
{
    if (m_busy)
        return;
    CFileDialog dialog(TRUE, _T("sqlite3"), NULL, OFN_FILEMUSTEXIST | OFN_HIDEREADONLY,
        _T("eMule Next backups (*.sqlite3)|*.sqlite3|All files (*.*)|*.*||"), this);
    dialog.m_ofn.lpstrTitle = _T("Select a validated eMule Next database backup to restore");
    if (dialog.DoModal() == IDOK)
        StartAction(ENMA_RESTORE, CStringW(dialog.GetPathName()));
}

void CEmuleNextDiagnosticsWnd::OnOpenBackupsClicked()
{
    const CString folder(theEmuleNext.GetDatabaseBackupFolder());
    if (!folder.IsEmpty())
        ::ShellExecute(m_hWnd, _T("open"), folder, NULL, NULL, SW_SHOWNORMAL);
}

BOOL CEmuleNextDiagnosticsWnd::PreTranslateMessage(MSG* message)
{
    if (message != NULL && message->message == WM_KEYDOWN && message->wParam == VK_F5) {
        OnRefreshClicked();
        return TRUE;
    }
    return CWnd::PreTranslateMessage(message);
}

void CEmuleNextDiagnosticsWnd::OnSize(UINT type, int cx, int cy)
{
    CWnd::OnSize(type, cx, cy);
    if (::IsWindow(m_title.m_hWnd))
        LayoutControls(cx, cy);
}

void CEmuleNextDiagnosticsWnd::LayoutControls(int cx, int cy)
{
    const int margin = CEmuleNextModernUi::PageMargin(m_hWnd);
    const int gap = CEmuleNextModernUi::ControlGap(m_hWnd);
    const int sectionGap = CEmuleNextModernUi::SectionGap(m_hWnd);
    const int titleHeight = CEmuleNextModernUi::Scale(m_hWnd, 34);
    const int compact = CEmuleNextModernUi::CompactHeight(m_hWnd);
    const int buttonHeight = CEmuleNextModernUi::ControlHeight(m_hWnd);
    const int cardHeight = CEmuleNextModernUi::Scale(m_hWnd, 104);
    const int width = max(0, cx - margin * 2);

    m_title.MoveWindow(margin, margin, width, titleHeight);
    m_subtitle.MoveWindow(margin, margin + titleHeight, width, compact);

    int y = margin + titleHeight + compact + sectionGap;
    const int cardGap = gap;
    const int cardWidth = max(CEmuleNextModernUi::Scale(m_hWnd, 180), (width - cardGap * 3) / 4);
    CEmuleNextCard* cards[] = { &m_databaseCard, &m_queueCard, &m_schedulerCard, &m_performanceCard };
    for (int i = 0; i < 4; ++i)
        cards[i]->MoveWindow(margin + i * (cardWidth + cardGap), y, cardWidth, cardHeight);
    y += cardHeight + sectionGap;

    m_databaseSection.MoveWindow(margin, y, width, compact);
    y += compact + gap;
    CButton* maintenance[] = { &m_refresh, &m_check, &m_backup, &m_restore, &m_prune, &m_checkpoint, &m_openBackups, &m_stress };
    const int buttonCols = cx < CEmuleNextModernUi::Scale(m_hWnd, 950) ? 4 : 8;
    const int buttonWidth = max(CEmuleNextModernUi::Scale(m_hWnd, 112), (width - gap * (buttonCols - 1)) / buttonCols);
    const int buttonRows = (_countof(maintenance) + buttonCols - 1) / buttonCols;
    for (int i = 0; i < _countof(maintenance); ++i) {
        const int row = i / buttonCols;
        const int col = i % buttonCols;
        maintenance[i]->MoveWindow(margin + col * (buttonWidth + gap), y + row * (buttonHeight + gap), buttonWidth, buttonHeight);
    }
    y += buttonRows * buttonHeight + max(0, buttonRows - 1) * gap + sectionGap;

    m_runtimeSection.MoveWindow(margin, y, width, compact);
    y += compact + gap;
    const int actionWidth = CEmuleNextModernUi::Scale(m_hWnd, 104);
    const int actionArea = actionWidth * 4 + gap * 3;
    const int listHeight = max(CEmuleNextModernUi::Scale(m_hWnd, 190), cy - y - margin - buttonHeight - gap);
    m_runtimeTests.MoveWindow(margin, y, width, listHeight);
    y += listHeight + gap;
    const int actionLeft = margin + width - actionArea;
    m_testPass.MoveWindow(actionLeft, y, actionWidth, buttonHeight);
    m_testFail.MoveWindow(actionLeft + actionWidth + gap, y, actionWidth, buttonHeight);
    m_testReset.MoveWindow(actionLeft + (actionWidth + gap) * 2, y, actionWidth, buttonHeight);
    m_export.MoveWindow(actionLeft + (actionWidth + gap) * 3, y, actionWidth, buttonHeight);
    m_actionStatus.MoveWindow(margin, y, max(0, actionLeft - margin - gap), buttonHeight);
}

void CEmuleNextDiagnosticsWnd::OnPaint()
{
    CPaintDC dc(this);
    CRect client;
    GetClientRect(&client);
    CEmuleNextModernUi::DrawPageBackground(dc, client);
}

BOOL CEmuleNextDiagnosticsWnd::OnEraseBkgnd(CDC*)
{
    return TRUE;
}

HBRUSH CEmuleNextDiagnosticsWnd::OnCtlColor(CDC* dc, CWnd* wnd, UINT ctlColor)
{
    dc->SetBkMode(TRANSPARENT);
    dc->SetTextColor(CEmuleNextModernUi::TextColor());
    if (wnd != NULL && (wnd->m_hWnd == m_subtitle.m_hWnd || wnd->m_hWnd == m_actionStatus.m_hWnd))
        dc->SetTextColor(CEmuleNextModernUi::MutedTextColor());
    if (ctlColor == CTLCOLOR_STATIC || ctlColor == CTLCOLOR_DLG)
        return static_cast<HBRUSH>(m_backgroundBrush.GetSafeHandle());
    return CWnd::OnCtlColor(dc, wnd, ctlColor);
}
