//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

static const uint32 EMULENEXT_SETTINGS_VIEW_ID = 0x7FFFFF04u;

class CEmuleNextSettingsWnd : public CWnd
{
public:
    CEmuleNextSettingsWnd();
    virtual ~CEmuleNextSettingsWnd();
    bool Create(CWnd* parent);
    void Refresh();

protected:
    DECLARE_MESSAGE_MAP()
    afx_msg int OnCreate(LPCREATESTRUCT createStruct);
    afx_msg void OnSize(UINT type, int cx, int cy);
    afx_msg BOOL OnEraseBkgnd(CDC* dc);
    afx_msg HBRUSH OnCtlColor(CDC* dc, CWnd* wnd, UINT ctlColor);
    afx_msg void OnApplyClicked();
    afx_msg void OnSchedulingModeChanged();

private:
    void LayoutControls(int cx, int cy);
    void UpdateSchedulingControls();

    CStatic m_heading;
    CStatic m_themeLabel;
    CComboBox m_themeMode;
    CStatic m_discoveryLabel;
    CButton m_discoveryEnabled;
    CStatic m_concurrencyLabel;
    CComboBox m_maxConcurrent;

    CStatic m_schedulerHeading;
    CStatic m_schedulerModeLabel;
    CComboBox m_schedulerMode;
    CButton m_sourceDiscoveryIntelligence;
    CButton m_a4afIntelligence;
    CButton m_rarePartIntelligence;
    CButton m_etaHealthDisplay;
    CStatic m_schedulerSafety;

    CButton m_apply;
    CStatic m_status;
    CBrush m_darkBrush;
};
