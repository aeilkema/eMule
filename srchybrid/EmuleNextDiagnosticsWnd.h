//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include "EmuleNextRuntime.h"

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
    afx_msg LRESULT OnMaintenanceResult(WPARAM, LPARAM value);

private:
    void LayoutControls(int cx, int cy);
    void StartAction(int action, const CStringW& path = CStringW());
    void ApplySnapshot(const EmuleNextDatabaseDiagnostics& snapshot);
    void UpdateButtons();

    CStatic m_title;
    CStatic m_subtitle;
    CStatic m_health;
    CStatic m_details;
    CButton m_refresh;
    CButton m_check;
    CButton m_backup;
    CButton m_restore;
    CButton m_prune;
    CButton m_checkpoint;
    CButton m_openBackups;
    CButton m_stress;
    CStatic m_actionStatus;
    CBrush m_darkBrush;
    bool m_busy;
    EmuleNextDatabaseDiagnostics m_snapshot;
};
