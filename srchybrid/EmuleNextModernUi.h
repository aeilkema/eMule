//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include <afxcmn.h>

class CEmuleNextModernUi
{
public:
    static int Scale(HWND window, int value);
    static int PageMargin(HWND window) { return Scale(window, 20); }
    static int SectionGap(HWND window) { return Scale(window, 16); }
    static int ControlGap(HWND window) { return Scale(window, 8); }
    static int ControlHeight(HWND window) { return Scale(window, 34); }
    static int CompactHeight(HWND window) { return Scale(window, 30); }
    static int NavigationWidth(HWND window) { return Scale(window, 196); }
    static int HeaderHeight(HWND window) { return Scale(window, 64); }
    static int CardRadius(HWND window) { return Scale(window, 10); }

    static COLORREF WindowColor();
    static COLORREF NavigationColor();
    static COLORREF CardColor();
    static COLORREF CardHoverColor();
    static COLORREF BorderColor();
    static COLORREF TextColor();
    static COLORREF MutedTextColor();
    static COLORREF AccentColor();
    static COLORREF SuccessColor();
    static COLORREF WarningColor();
    static COLORREF ErrorColor();

    static void ApplyFont(CWnd* root, CFont& normal, CFont& title, CFont& section);
    static void ApplyList(CListCtrl& list);
    static void ApplyCombo(CComboBox& combo);
    static void SetExplorerTheme(HWND window);
    static void DrawRoundedCard(CDC& dc, const CRect& rect, COLORREF fill, COLORREF border, int radius);
    static void DrawPageBackground(CDC& dc, const CRect& rect);
};

class CEmuleNextCard : public CStatic
{
public:
    CEmuleNextCard();
    void SetContent(const CString& title, const CString& value, const CString& detail, COLORREF accent = CLR_INVALID);

protected:
    virtual void DrawItem(LPDRAWITEMSTRUCT drawItemStruct);

private:
    CString m_title;
    CString m_value;
    CString m_detail;
    COLORREF m_accent;
};

class CEmuleNextNavList : public CListBox
{
public:
    CEmuleNextNavList();
    void RefreshPalette();

protected:
    virtual void DrawItem(LPDRAWITEMSTRUCT drawItemStruct);
    virtual void MeasureItem(LPMEASUREITEMSTRUCT measureItemStruct);
    afx_msg BOOL OnEraseBkgnd(CDC* dc);

    DECLARE_MESSAGE_MAP()
};