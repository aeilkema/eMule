//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#include "stdafx.h"
#include "EmuleNextModernUi.h"
#include "EmuleNextTheme.h"
#include "EmuleNextUiMetrics.h"

#include <commctrl.h>
#include <uxtheme.h>

int CEmuleNextModernUi::Scale(HWND window, int value)
{
    return CEmuleNextUiMetrics::Scale(window, value);
}

COLORREF CEmuleNextModernUi::WindowColor()
{
    return CEmuleNextTheme::BackgroundColor();
}

COLORREF CEmuleNextModernUi::NavigationColor()
{
    if (CEmuleNextTheme::IsDarkMode())
        return RGB(24, 26, 30);
    return RGB(245, 247, 250);
}

COLORREF CEmuleNextModernUi::CardColor()
{
    return CEmuleNextTheme::SurfaceColor();
}

COLORREF CEmuleNextModernUi::CardHoverColor()
{
    if (CEmuleNextTheme::IsDarkMode())
        return RGB(49, 53, 60);
    return RGB(248, 250, 252);
}

COLORREF CEmuleNextModernUi::BorderColor()
{
    return CEmuleNextTheme::BorderColor();
}

COLORREF CEmuleNextModernUi::TextColor()
{
    return CEmuleNextTheme::TextColor();
}

COLORREF CEmuleNextModernUi::MutedTextColor()
{
    return CEmuleNextTheme::MutedTextColor();
}

COLORREF CEmuleNextModernUi::AccentColor()
{
    return CEmuleNextTheme::AccentColor();
}

COLORREF CEmuleNextModernUi::SuccessColor()
{
    return CEmuleNextTheme::IsDarkMode() ? RGB(94, 210, 142) : RGB(24, 142, 82);
}

COLORREF CEmuleNextModernUi::WarningColor()
{
    return CEmuleNextTheme::IsDarkMode() ? RGB(244, 194, 92) : RGB(181, 116, 0);
}

COLORREF CEmuleNextModernUi::ErrorColor()
{
    return CEmuleNextTheme::IsDarkMode() ? RGB(244, 119, 119) : RGB(193, 52, 52);
}

void CEmuleNextModernUi::ApplyFont(CWnd* root, CFont& normal, CFont& title, CFont& section)
{
    if (root == NULL || !::IsWindow(root->m_hWnd))
        return;

    const int dpi = static_cast<int>(CEmuleNextUiMetrics::DpiForWindow(root->m_hWnd));
    const int normalHeight = -MulDiv(9, dpi, 72);
    const int titleHeight = -MulDiv(18, dpi, 72);
    const int sectionHeight = -MulDiv(11, dpi, 72);

    normal.DeleteObject();
    title.DeleteObject();
    section.DeleteObject();

    LOGFONT lf = {};
    lf.lfHeight = normalHeight;
    lf.lfWeight = FW_NORMAL;
    _tcscpy_s(lf.lfFaceName, _T("Segoe UI Variable Text"));
    if (!normal.CreateFontIndirect(&lf)) {
        _tcscpy_s(lf.lfFaceName, _T("Segoe UI"));
        normal.CreateFontIndirect(&lf);
    }

    lf.lfHeight = titleHeight;
    lf.lfWeight = FW_SEMIBOLD;
    _tcscpy_s(lf.lfFaceName, _T("Segoe UI Variable Display"));
    if (!title.CreateFontIndirect(&lf)) {
        _tcscpy_s(lf.lfFaceName, _T("Segoe UI"));
        title.CreateFontIndirect(&lf);
    }

    lf.lfHeight = sectionHeight;
    lf.lfWeight = FW_SEMIBOLD;
    _tcscpy_s(lf.lfFaceName, _T("Segoe UI Variable Text"));
    if (!section.CreateFontIndirect(&lf)) {
        _tcscpy_s(lf.lfFaceName, _T("Segoe UI"));
        section.CreateFontIndirect(&lf);
    }
}

void CEmuleNextModernUi::SetExplorerTheme(HWND window)
{
    if (window == NULL)
        return;
    ::SetWindowTheme(window, CEmuleNextTheme::IsDarkMode() ? L"DarkMode_Explorer" : L"Explorer", NULL);
}

void CEmuleNextModernUi::ApplyList(CListCtrl& list)
{
    if (!::IsWindow(list.m_hWnd))
        return;
    list.SetExtendedStyle(list.GetExtendedStyle() | LVS_EX_FULLROWSELECT | LVS_EX_DOUBLEBUFFER | LVS_EX_LABELTIP);
    list.SetBkColor(CardColor());
    list.SetTextBkColor(CardColor());
    list.SetTextColor(TextColor());
    SetExplorerTheme(list.m_hWnd);
    if (list.GetHeaderCtrl() != NULL)
        SetExplorerTheme(list.GetHeaderCtrl()->m_hWnd);
}

void CEmuleNextModernUi::ApplyCombo(CComboBox& combo)
{
    if (::IsWindow(combo.m_hWnd))
        SetExplorerTheme(combo.m_hWnd);
}

void CEmuleNextModernUi::DrawRoundedCard(CDC& dc, const CRect& rect, COLORREF fill, COLORREF border, int radius)
{
    CPen pen(PS_SOLID, 1, border);
    CBrush brush(fill);
    CPen* oldPen = dc.SelectObject(&pen);
    CBrush* oldBrush = dc.SelectObject(&brush);
    dc.RoundRect(rect, CPoint(radius, radius));
    dc.SelectObject(oldBrush);
    dc.SelectObject(oldPen);
}

void CEmuleNextModernUi::DrawPageBackground(CDC& dc, const CRect& rect)
{
    dc.FillSolidRect(rect, WindowColor());
}

CEmuleNextCard::CEmuleNextCard()
    : m_accent(CLR_INVALID)
{
}

void CEmuleNextCard::SetContent(const CString& title, const CString& value, const CString& detail, COLORREF accent)
{
    m_title = title;
    m_value = value;
    m_detail = detail;
    m_accent = accent;
    if (::IsWindow(m_hWnd))
        Invalidate(FALSE);
}

void CEmuleNextCard::DrawItem(LPDRAWITEMSTRUCT drawItemStruct)
{
    if (drawItemStruct == NULL)
        return;
    CDC dc;
    dc.Attach(drawItemStruct->hDC);
    CRect rect(drawItemStruct->rcItem);
    rect.DeflateRect(1, 1);
    CEmuleNextModernUi::DrawRoundedCard(dc, rect, CEmuleNextModernUi::CardColor(), CEmuleNextModernUi::BorderColor(), CEmuleNextModernUi::CardRadius(m_hWnd));

    const int pad = CEmuleNextModernUi::Scale(m_hWnd, 14);
    CRect textRect = rect;
    textRect.DeflateRect(pad, CEmuleNextModernUi::Scale(m_hWnd, 10));
    dc.SetBkMode(TRANSPARENT);
    dc.SetTextColor(CEmuleNextModernUi::MutedTextColor());

    CFont* base = GetFont();
    CFont section;
    LOGFONT lf = {};
    if (base != NULL && base->GetLogFont(&lf)) {
        lf.lfWeight = FW_SEMIBOLD;
        section.CreateFontIndirect(&lf);
    }

    CRect titleRect = textRect;
    titleRect.bottom = titleRect.top + CEmuleNextModernUi::Scale(m_hWnd, 20);
    dc.DrawText(m_title, titleRect, DT_LEFT | DT_SINGLELINE | DT_END_ELLIPSIS | DT_VCENTER);

    if (section.m_hObject != NULL)
        dc.SelectObject(&section);
    dc.SetTextColor(m_accent == CLR_INVALID ? CEmuleNextModernUi::TextColor() : m_accent);
    CRect valueRect = textRect;
    valueRect.top += CEmuleNextModernUi::Scale(m_hWnd, 24);
    valueRect.bottom = valueRect.top + CEmuleNextModernUi::Scale(m_hWnd, 26);
    dc.DrawText(m_value, valueRect, DT_LEFT | DT_SINGLELINE | DT_END_ELLIPSIS | DT_VCENTER);

    if (base != NULL)
        dc.SelectObject(base);
    dc.SetTextColor(CEmuleNextModernUi::MutedTextColor());
    CRect detailRect = textRect;
    detailRect.top += CEmuleNextModernUi::Scale(m_hWnd, 52);
    dc.DrawText(m_detail, detailRect, DT_LEFT | DT_WORDBREAK | DT_END_ELLIPSIS);
    dc.Detach();
}

BEGIN_MESSAGE_MAP(CEmuleNextNavList, CListBox)
    ON_WM_ERASEBKGND()
END_MESSAGE_MAP()

CEmuleNextNavList::CEmuleNextNavList()
{
}

void CEmuleNextNavList::RefreshPalette()
{
    if (!::IsWindow(m_hWnd))
        return;
    CEmuleNextModernUi::SetExplorerTheme(m_hWnd);
    Invalidate(FALSE);
}

BOOL CEmuleNextNavList::OnEraseBkgnd(CDC* dc)
{
    if (dc == NULL)
        return TRUE;
    CRect rect;
    GetClientRect(&rect);
    dc->FillSolidRect(rect, CEmuleNextModernUi::NavigationColor());
    return TRUE;
}

void CEmuleNextNavList::MeasureItem(LPMEASUREITEMSTRUCT measureItemStruct)
{
    if (measureItemStruct != NULL)
        measureItemStruct->itemHeight = CEmuleNextModernUi::Scale(m_hWnd, 42);
}

void CEmuleNextNavList::DrawItem(LPDRAWITEMSTRUCT drawItemStruct)
{
    if (drawItemStruct == NULL || drawItemStruct->itemID == static_cast<UINT>(-1))
        return;

    CDC dc;
    dc.Attach(drawItemStruct->hDC);
    CRect rect(drawItemStruct->rcItem);
    dc.FillSolidRect(rect, CEmuleNextModernUi::NavigationColor());

    const bool selected = (drawItemStruct->itemState & ODS_SELECTED) != 0;
    const bool focused = (drawItemStruct->itemState & ODS_FOCUS) != 0;
    CRect itemRect = rect;
    itemRect.DeflateRect(CEmuleNextModernUi::Scale(m_hWnd, 6), CEmuleNextModernUi::Scale(m_hWnd, 3));

    if (selected) {
        CEmuleNextModernUi::DrawRoundedCard(dc, itemRect,
            CEmuleNextModernUi::CardHoverColor(), CEmuleNextModernUi::AccentColor(),
            CEmuleNextModernUi::Scale(m_hWnd, 8));
        CRect accent = itemRect;
        accent.right = accent.left + CEmuleNextModernUi::Scale(m_hWnd, 4);
        dc.FillSolidRect(accent, CEmuleNextModernUi::AccentColor());
    }

    CString text;
    GetText(static_cast<int>(drawItemStruct->itemID), text);
    CRect textRect = itemRect;
    textRect.left += CEmuleNextModernUi::Scale(m_hWnd, 16);
    textRect.right -= CEmuleNextModernUi::Scale(m_hWnd, 10);
    dc.SetBkMode(TRANSPARENT);
    dc.SetTextColor(selected ? CEmuleNextModernUi::TextColor() : CEmuleNextModernUi::MutedTextColor());
    CFont* font = GetFont();
    CFont* oldFont = font != NULL ? dc.SelectObject(font) : NULL;
    dc.DrawText(text, textRect, DT_LEFT | DT_SINGLELINE | DT_VCENTER | DT_END_ELLIPSIS | DT_NOPREFIX);
    if (oldFont != NULL)
        dc.SelectObject(oldFont);

    if (focused && !selected)
        dc.DrawFocusRect(itemRect);
    dc.Detach();
}