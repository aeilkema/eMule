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
    void FillNumberCombo(CComboBox& combo, const int* values, int count);
    int SelectNumber(CComboBox& combo, const int* values, int count, int value);
    int SelectedNumber(const CComboBox& combo, const int* values, int count, int fallback) const;

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
    CStatic m_schedulerProfileLabel;
    CComboBox m_schedulerProfile;
    CStatic m_schedulerCooldownLabel;
    CComboBox m_schedulerCooldown;
    CStatic m_schedulerBatchLabel;
    CComboBox m_schedulerBatch;
    CStatic m_a4afThresholdLabel;
    CComboBox m_a4afThreshold;
    CButton m_sourceDiscoveryIntelligence;
    CButton m_a4afIntelligence;
    CButton m_rarePartIntelligence;
    CButton m_etaHealthDisplay;
    CButton m_historyCache;
    CButton m_telemetry;
    CStatic m_telemetryCapacityLabel;
    CComboBox m_telemetryCapacity;
    CStatic m_schedulerRuntime;
    CStatic m_schedulerSafety;

    CButton m_apply;
    CStatic m_status;
    CBrush m_darkBrush;
};
