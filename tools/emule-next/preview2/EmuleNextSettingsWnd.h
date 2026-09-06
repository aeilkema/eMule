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
    virtual BOOL PreTranslateMessage(MSG* message);

protected:
    DECLARE_MESSAGE_MAP()
    afx_msg int OnCreate(LPCREATESTRUCT createStruct);
    afx_msg void OnSize(UINT type, int cx, int cy);
    afx_msg void OnPaint();
    afx_msg BOOL OnEraseBkgnd(CDC* dc);
    afx_msg HBRUSH OnCtlColor(CDC* dc, CWnd* wnd, UINT ctlColor);
    afx_msg void OnCategoryChanged();
    afx_msg void OnSchedulingModeChanged();
    afx_msg void OnCustomTuningChanged();
    afx_msg void OnApplyClicked();

private:
    enum Category
    {
        CATEGORY_APPEARANCE = 0,
        CATEGORY_PEERS,
        CATEGORY_INTELLIGENCE,
        CATEGORY_ADVANCED,
        CATEGORY_COUNT
    };

    void LayoutControls(int cx, int cy);
    void ShowCategory(Category category);
    void UpdateEnabledState();
    void FillNumberCombo(CComboBox& combo, const int* values, int count);
    void SelectNumber(CComboBox& combo, const int* values, int count, int value);
    int SelectedNumber(const CComboBox& combo, const int* values, int count, int fallback) const;
    void SetPageFonts();

    CListBox m_navigation;
    CStatic m_title;
    CStatic m_subtitle;
    CStatic m_sectionTitle;
    CStatic m_sectionDescription;

    CStatic m_themeLabel;
    CComboBox m_theme;
    CButton m_etaHealth;

    CButton m_peerDiscovery;
    CStatic m_peerConcurrencyLabel;
    CComboBox m_peerConcurrency;
    CStatic m_peerPrivacyNote;

    CStatic m_schedulerModeLabel;
    CComboBox m_schedulerMode;
    CStatic m_schedulerProfileLabel;
    CComboBox m_schedulerProfile;
    CButton m_sourceDiscovery;
    CButton m_a4af;
    CButton m_rareParts;
    CStatic m_schedulerSafety;

    CButton m_customTuning;
    CStatic m_cooldownLabel;
    CComboBox m_cooldown;
    CStatic m_batchLabel;
    CComboBox m_batch;
    CStatic m_a4afThresholdLabel;
    CComboBox m_a4afThreshold;
    CStatic m_advancedNote;

    CButton m_apply;
    CStatic m_status;
    CBrush m_backgroundBrush;
    CFont m_normalFont;
    CFont m_titleFont;
    CFont m_sectionFont;
    Category m_category;
};
