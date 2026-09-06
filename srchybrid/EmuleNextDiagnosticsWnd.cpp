//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#include "stdafx.h"
#include "EmuleNextDiagnosticsWnd.h"
#include "EmuleNextTheme.h"
#include "EmuleNextUiMetrics.h"
#include "EmuleNextStressDiagnostics.h"

#include <afxdlgs.h>
#include <memory>

namespace
{
    enum { IDC_EN_DIAG_REFRESH = 0x7ED0, IDC_EN_DIAG_CHECK, IDC_EN_DIAG_BACKUP, IDC_EN_DIAG_RESTORE,
        IDC_EN_DIAG_PRUNE, IDC_EN_DIAG_CHECKPOINT, IDC_EN_DIAG_OPEN, IDC_EN_DIAG_STRESS };
    const UINT WM_EN_DIAG_RESULT = WM_APP + 0x5D8;
    enum MaintenanceAction { ENMA_REFRESH = 0, ENMA_FULL_CHECK, ENMA_BACKUP, ENMA_RESTORE, ENMA_PRUNE, ENMA_CHECKPOINT, ENMA_STRESS };

    struct MaintenanceContext { HWND target; int action; CStringW path; MaintenanceContext() : target(NULL), action(ENMA_REFRESH) {} };
    struct MaintenanceResult { bool ok; int action; CStringW message; EmuleNextDatabaseDiagnostics snapshot; MaintenanceResult() : ok(false), action(ENMA_REFRESH) {} };

    UINT AFX_CDECL MaintenanceWorker(LPVOID value)
    {
        std::unique_ptr<MaintenanceContext> context(static_cast<MaintenanceContext*>(value));
        std::unique_ptr<MaintenanceResult> result(new MaintenanceResult); result->action = context->action;
        switch (context->action) {
        case ENMA_REFRESH: result->ok = theEmuleNext.LoadDatabaseDiagnostics(result->snapshot); result->message = result->ok ? L"Diagnostics refreshed." : L"Database diagnostics unavailable."; break;
        case ENMA_FULL_CHECK: result->ok = theEmuleNext.RunDatabaseIntegrityCheck(true, result->message); theEmuleNext.LoadDatabaseDiagnostics(result->snapshot); break;
        case ENMA_BACKUP: { CStringW backupPath; result->ok = theEmuleNext.CreateDatabaseBackup(L"manual", backupPath, result->message); theEmuleNext.LoadDatabaseDiagnostics(result->snapshot); break; }
        case ENMA_RESTORE: result->ok = theEmuleNext.RestoreDatabaseBackup(context->path, result->message); theEmuleNext.LoadDatabaseDiagnostics(result->snapshot); break;
        case ENMA_PRUNE: { uint64 removed = 0; result->ok = theEmuleNext.PruneDatabaseTelemetry(removed, result->message); theEmuleNext.LoadDatabaseDiagnostics(result->snapshot); break; }
        case ENMA_CHECKPOINT: result->ok = theEmuleNext.CheckpointDatabase(result->message); theEmuleNext.LoadDatabaseDiagnostics(result->snapshot); break;
        case ENMA_STRESS: {
            EmuleNextStressDiagnosticsResult stress;
            result->ok = CEmuleNextStressDiagnostics::RunIndexStress(10000, 5000, stress);
            result->message = stress.details;
            theEmuleNext.LoadDatabaseDiagnostics(result->snapshot);
            break;
        }
        }
        if (::IsWindow(context->target) && ::PostMessage(context->target, WM_EN_DIAG_RESULT, 0, reinterpret_cast<LPARAM>(result.get()))) result.release();
        return 0;
    }

    CString SizeText(uint64 bytes) { CString value; if (bytes >= 1024ui64 * 1024ui64) value.Format(_T("%.1f MB"), static_cast<double>(bytes) / (1024.0 * 1024.0)); else if (bytes >= 1024ui64) value.Format(_T("%.1f KB"), static_cast<double>(bytes) / 1024.0); else value.Format(_T("%I64u B"), bytes); return value; }
    CString TimeText(uint64 timestamp) { if (timestamp == 0) return _T("--"); CTime value(static_cast<time_t>(timestamp)); return value.Format(_T("%Y-%m-%d %H:%M")); }
}

BEGIN_MESSAGE_MAP(CEmuleNextDiagnosticsWnd, CWnd)
    ON_WM_CREATE() ON_WM_SIZE() ON_WM_ERASEBKGND() ON_WM_CTLCOLOR()
    ON_BN_CLICKED(IDC_EN_DIAG_REFRESH, OnRefreshClicked) ON_BN_CLICKED(IDC_EN_DIAG_CHECK, OnCheckClicked)
    ON_BN_CLICKED(IDC_EN_DIAG_BACKUP, OnBackupClicked) ON_BN_CLICKED(IDC_EN_DIAG_RESTORE, OnRestoreClicked)
    ON_BN_CLICKED(IDC_EN_DIAG_PRUNE, OnPruneClicked) ON_BN_CLICKED(IDC_EN_DIAG_CHECKPOINT, OnCheckpointClicked)
    ON_BN_CLICKED(IDC_EN_DIAG_OPEN, OnOpenBackupsClicked) ON_BN_CLICKED(IDC_EN_DIAG_STRESS, OnStressClicked)
    ON_MESSAGE(WM_EN_DIAG_RESULT, OnMaintenanceResult)
END_MESSAGE_MAP()

CEmuleNextDiagnosticsWnd::CEmuleNextDiagnosticsWnd() : m_busy(false) {}
CEmuleNextDiagnosticsWnd::~CEmuleNextDiagnosticsWnd() {}

bool CEmuleNextDiagnosticsWnd::Create(CWnd* parent)
{
    if (parent == NULL) return false;
    const CString className = AfxRegisterWndClass(CS_DBLCLKS, ::LoadCursor(NULL, IDC_ARROW), reinterpret_cast<HBRUSH>(COLOR_WINDOW + 1), NULL);
    CRect empty(0, 0, 0, 0);
    return CWnd::CreateEx(0, className, _T("eMule Next Diagnostics"), WS_CHILD | WS_CLIPCHILDREN | WS_CLIPSIBLINGS, empty, parent, 0) != FALSE;
}

int CEmuleNextDiagnosticsWnd::OnCreate(LPCREATESTRUCT createStruct)
{
    if (CWnd::OnCreate(createStruct) == -1) return -1;
    m_darkBrush.CreateSolidBrush(CEmuleNextTheme::BackgroundColor()); CRect empty(0, 0, 0, 0);
    if (!m_title.Create(_T("Database, Performance & Recovery"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_subtitle.Create(_T("Integrity, backups, writer queues and deterministic in-memory index stress diagnostics."), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_health.Create(_T("Status: loading..."), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_details.Create(_T(""), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_refresh.Create(_T("Refresh"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DIAG_REFRESH)
        || !m_check.Create(_T("Full integrity check"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DIAG_CHECK)
        || !m_backup.Create(_T("Create backup"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DIAG_BACKUP)
        || !m_restore.Create(_T("Restore backup..."), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DIAG_RESTORE)
        || !m_prune.Create(_T("Prune old telemetry"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DIAG_PRUNE)
        || !m_checkpoint.Create(_T("Checkpoint WAL"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DIAG_CHECKPOINT)
        || !m_openBackups.Create(_T("Open backup folder"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DIAG_OPEN)
        || !m_stress.Create(_T("Run index stress test"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DIAG_STRESS)
        || !m_actionStatus.Create(_T("Maintenance and stress actions run outside the GUI thread."), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)) return -1;
    CFont* font = CFont::FromHandle(static_cast<HFONT>(::GetStockObject(DEFAULT_GUI_FONT)));
    CWnd* controls[] = { &m_title, &m_subtitle, &m_health, &m_details, &m_refresh, &m_check, &m_backup, &m_restore, &m_prune, &m_checkpoint, &m_openBackups, &m_stress, &m_actionStatus };
    for (int i = 0; i < _countof(controls); ++i) controls[i]->SetFont(font);
    CEmuleNextTheme::ApplyToWindow(m_hWnd); Refresh(true); return 0;
}

void CEmuleNextDiagnosticsWnd::Refresh(bool force) { if (::IsWindow(m_hWnd) && (!m_busy || force)) StartAction(ENMA_REFRESH); }
void CEmuleNextDiagnosticsWnd::StartAction(int action, const CStringW& path)
{
    if (m_busy) return;
    std::unique_ptr<MaintenanceContext> context(new MaintenanceContext); context->target = m_hWnd; context->action = action; context->path = path;
    m_busy = true; UpdateButtons(); m_actionStatus.SetWindowText(_T("Working in background..."));
    if (AfxBeginThread(MaintenanceWorker, context.get(), THREAD_PRIORITY_BELOW_NORMAL) == NULL) { m_busy = false; UpdateButtons(); m_actionStatus.SetWindowText(_T("Unable to start maintenance worker.")); return; }
    context.release();
}

void CEmuleNextDiagnosticsWnd::ApplySnapshot(const EmuleNextDatabaseDiagnostics& s)
{
    m_snapshot = s; CString health; health.Format(_T("Status: %s%s"), static_cast<LPCTSTR>(CString(s.status)), s.recoveryRequired ? _T(" - manual recovery required") : _T("")); m_health.SetWindowText(health);
    CString details;
    details.Format(_T("Database: %s\r\nSchema: v%d   DB: %s   WAL: %s\r\nBackups: %u   latest: %s\r\nRows - peers %I64u, files %I64u, library %I64u, transfers %I64u, scheduler decisions %I64u, outcomes %I64u\r\nWriter queue - queued %I64u, peak %I64u, processed %I64u, dropped %I64u, errors %I64u\r\nLast integrity check: %s   result: %s\r\nBackup folder: %s\r\nPerformance self-test: use 'Run index stress test' for 10,000 ClientIndex + 5,000 DownloadIndex entries."),
        static_cast<LPCTSTR>(CString(s.databasePath)), s.schemaVersion, static_cast<LPCTSTR>(SizeText(s.databaseBytes)), static_cast<LPCTSTR>(SizeText(s.walBytes)), s.backupCount, static_cast<LPCTSTR>(TimeText(s.lastBackupAt)),
        s.peerCount, s.fileCount, s.libraryCount, s.transferCount, s.schedulerDecisionCount, s.schedulerOutcomeCount,
        s.queue.queued, s.queue.peakQueued, s.queue.processed, s.queue.dropped, s.queue.errors,
        static_cast<LPCTSTR>(TimeText(s.lastIntegrityAt)), static_cast<LPCTSTR>(CString(s.lastIntegrityResult)), static_cast<LPCTSTR>(CString(s.backupFolder)));
    m_details.SetWindowText(details);
}

LRESULT CEmuleNextDiagnosticsWnd::OnMaintenanceResult(WPARAM, LPARAM value)
{
    std::unique_ptr<MaintenanceResult> result(reinterpret_cast<MaintenanceResult*>(value)); m_busy = false;
    if (result.get() != NULL) { ApplySnapshot(result->snapshot); CString message(result->message); if (!result->ok) message = _T("Failed: ") + message; m_actionStatus.SetWindowText(message); }
    UpdateButtons(); return 0;
}

void CEmuleNextDiagnosticsWnd::UpdateButtons()
{
    const BOOL e = m_busy ? FALSE : TRUE; m_refresh.EnableWindow(e); m_check.EnableWindow(e); m_restore.EnableWindow(e); m_openBackups.EnableWindow(e); m_stress.EnableWindow(e);
    const BOOL running = e && theEmuleNext.IsRunning(); m_backup.EnableWindow(running); m_prune.EnableWindow(running); m_checkpoint.EnableWindow(running);
}
void CEmuleNextDiagnosticsWnd::OnRefreshClicked() { StartAction(ENMA_REFRESH); }
void CEmuleNextDiagnosticsWnd::OnCheckClicked() { StartAction(ENMA_FULL_CHECK); }
void CEmuleNextDiagnosticsWnd::OnBackupClicked() { StartAction(ENMA_BACKUP); }
void CEmuleNextDiagnosticsWnd::OnPruneClicked() { StartAction(ENMA_PRUNE); }
void CEmuleNextDiagnosticsWnd::OnCheckpointClicked() { StartAction(ENMA_CHECKPOINT); }
void CEmuleNextDiagnosticsWnd::OnStressClicked() { StartAction(ENMA_STRESS); }
void CEmuleNextDiagnosticsWnd::OnRestoreClicked()
{
    if (m_busy) return;
    CFileDialog dialog(TRUE, _T("sqlite3"), NULL, OFN_FILEMUSTEXIST | OFN_HIDEREADONLY, _T("eMule Next backups (*.sqlite3)|*.sqlite3|All files (*.*)|*.*||"), this);
    dialog.m_ofn.lpstrTitle = _T("Select a validated eMule Next database backup to restore");
    if (dialog.DoModal() == IDOK) StartAction(ENMA_RESTORE, CStringW(dialog.GetPathName()));
}
void CEmuleNextDiagnosticsWnd::OnOpenBackupsClicked() { const CString folder(theEmuleNext.GetDatabaseBackupFolder()); if (!folder.IsEmpty()) ::ShellExecute(m_hWnd, _T("open"), folder, NULL, NULL, SW_SHOWNORMAL); }
BOOL CEmuleNextDiagnosticsWnd::PreTranslateMessage(MSG* message) { if (message != NULL && message->message == WM_KEYDOWN && message->wParam == VK_F5) { OnRefreshClicked(); return TRUE; } return CWnd::PreTranslateMessage(message); }
void CEmuleNextDiagnosticsWnd::OnSize(UINT type, int cx, int cy) { CWnd::OnSize(type, cx, cy); if (::IsWindow(m_title.m_hWnd)) LayoutControls(cx, cy); }
void CEmuleNextDiagnosticsWnd::LayoutControls(int cx, int cy)
{
    const int margin = CEmuleNextUiMetrics::Scale(m_hWnd, 12), gap = CEmuleNextUiMetrics::Scale(m_hWnd, 7), titleHeight = CEmuleNextUiMetrics::Scale(m_hWnd, 24), line = CEmuleNextUiMetrics::Scale(m_hWnd, 20), actionHeight = CEmuleNextUiMetrics::Scale(m_hWnd, 30), clientWidth = max(0, cx - margin * 2); int y = margin;
    m_title.MoveWindow(margin, y, clientWidth, titleHeight); y += titleHeight + gap / 2; m_subtitle.MoveWindow(margin, y, clientWidth, line); y += line + gap; m_health.MoveWindow(margin, y, clientWidth, line); y += line + gap;
    const int perRow = cx < CEmuleNextUiMetrics::Scale(m_hWnd, 900) ? 3 : 4; CButton* buttons[] = { &m_refresh, &m_check, &m_backup, &m_restore, &m_prune, &m_checkpoint, &m_openBackups, &m_stress };
    const int buttonWidth = max(CEmuleNextUiMetrics::Scale(m_hWnd, 125), (clientWidth - gap * (perRow - 1)) / perRow), rows = (_countof(buttons) + perRow - 1) / perRow;
    for (int i = 0; i < _countof(buttons); ++i) { const int row = i / perRow, col = i % perRow; buttons[i]->MoveWindow(margin + col * (buttonWidth + gap), y + row * (actionHeight + gap), buttonWidth, actionHeight); }
    y += rows * actionHeight + (rows - 1) * gap + gap; m_actionStatus.MoveWindow(margin, y, clientWidth, line); y += line + gap; m_details.MoveWindow(margin, y, clientWidth, max(CEmuleNextUiMetrics::Scale(m_hWnd, 160), cy - y - margin));
}
BOOL CEmuleNextDiagnosticsWnd::OnEraseBkgnd(CDC* dc) { if (!CEmuleNextTheme::IsDarkMode()) return CWnd::OnEraseBkgnd(dc); CRect rect; GetClientRect(&rect); dc->FillSolidRect(rect, CEmuleNextTheme::BackgroundColor()); return TRUE; }
HBRUSH CEmuleNextDiagnosticsWnd::OnCtlColor(CDC* dc, CWnd* wnd, UINT ctlColor) { if (!CEmuleNextTheme::IsDarkMode()) return CWnd::OnCtlColor(dc, wnd, ctlColor); dc->SetTextColor(CEmuleNextTheme::TextColor()); dc->SetBkColor(CEmuleNextTheme::BackgroundColor()); if (ctlColor == CTLCOLOR_STATIC || ctlColor == CTLCOLOR_DLG) return static_cast<HBRUSH>(m_darkBrush.GetSafeHandle()); return CWnd::OnCtlColor(dc, wnd, ctlColor); }
