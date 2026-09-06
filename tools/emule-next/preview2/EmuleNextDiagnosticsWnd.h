//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include "EmuleNextRuntime.h"
#include "EmuleNextModernUi.h"

static const uint32 EMULENEXT_DIAGNOSTICS_VIEW_ID = 0x7FFFFF05u;

class CEmuleNextDiagnosticsWnd : public CWnd
{
public:
    CEmuleNextDiagnosticsWnd();
    virtual ~CEmuleNextDiagnosticsWnd();
    bool Create(CWnd* parent);
    void Refresh(bool force = false);
    virtual BOOL PreTranslateMessage(MSG* message);

protected:
    DECLARE_MESSAGE_MAP()
    afx_msg int OnCreate(LPCREATESTRUCT createStruct);
    afx_msg void OnSize(UINT type, int cx, int cy);
    afx_msg void OnPaint();
    afx_msg BOOL OnEraseBkgnd(CDC* dc);
    afx_msg HBRUSH OnCtlColor(CDC* dc, CWnd* wnd, UINT ctlColor);
    afx_msg void OnRefreshClicked();
    afx_msg void OnCheckClicked();
    afx_msg void OnBackupClicked();
    afx_msg void OnRestoreClicked();
    afx_msg void OnPruneClicked();
    afx_msg void OnCheckpointClicked();
    afx_msg void OnOpenBackupsClicked();
    afx_msg void OnStressClicked();
    afx_msg void OnTestSelectionChanged(NMHDR* header, LRESULT* result);
    afx_msg void OnTestPassClicked();
    afx_msg void OnTestFailClicked();
    afx_msg void OnTestResetClicked();
    afx_msg void OnExportClicked();
    afx_msg LRESULT OnMaintenanceResult(WPARAM, LPARAM value);

private:
    void LayoutControls(int cx, int cy);
    void StartAction(int action, const CStringW& path = CStringW());
    void ApplySnapshot(const EmuleNextDatabaseDiagnostics& snapshot);
    void UpdateButtons();
    void PopulateRuntimeTests();
    void SetRuntimeTestState(int state);
    CString RuntimeTestKey(int row) const;
    CString RuntimeTestStateText(int state) const;
    void ExportDiagnosticsReport();
    void SetPageFonts();

    CStatic m_title;
    CStatic m_subtitle;
    CEmuleNextCard m_databaseCard;
    CEmuleNextCard m_queueCard;
    CEmuleNextCard m_schedulerCard;
    CEmuleNextCard m_performanceCard;
    CStatic m_databaseSection;
    CButton m_refresh;
    CButton m_check;
    CButton m_backup;
    CButton m_restore;
    CButton m_prune;
    CButton m_checkpoint;
    CButton m_openBackups;
    CButton m_stress;
    CStatic m_runtimeSection;
    CListCtrl m_runtimeTests;
    CButton m_testPass;
    CButton m_testFail;
    CButton m_testReset;
    CButton m_export;
    CStatic m_actionStatus;
    CBrush m_backgroundBrush;
    CFont m_normalFont;
    CFont m_titleFont;
    CFont m_sectionFont;
    bool m_busy;
    CString m_lastStressResult;
    EmuleNextDatabaseDiagnostics m_snapshot;
};
