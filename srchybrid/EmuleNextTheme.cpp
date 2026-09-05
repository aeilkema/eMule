//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later

#include "stdafx.h"
#include "EmuleNextTheme.h"
#include "emule.h"

#include <dwmapi.h>
#include <uxtheme.h>

namespace
{
    bool g_darkMode = true;

    enum PreferredAppMode
    {
        AppModeDefault = 0,
        AppModeAllowDark = 1,
        AppModeForceDark = 2,
        AppModeForceLight = 3,
        AppModeMax = 4
    };

    typedef PreferredAppMode (WINAPI *SetPreferredAppModeFn)(PreferredAppMode);
    typedef BOOL (WINAPI *AllowDarkModeForWindowFn)(HWND, BOOL);

    SetPreferredAppModeFn ResolveSetPreferredAppMode()
    {
        HMODULE module = ::GetModuleHandleW(L"uxtheme.dll");
        if (module == NULL)
            module = ::LoadLibraryW(L"uxtheme.dll");
        return module != NULL
            ? reinterpret_cast<SetPreferredAppModeFn>(::GetProcAddress(module, MAKEINTRESOURCEA(135)))
            : NULL;
    }

    AllowDarkModeForWindowFn ResolveAllowDarkModeForWindow()
    {
        HMODULE module = ::GetModuleHandleW(L"uxtheme.dll");
        if (module == NULL)
            module = ::LoadLibraryW(L"uxtheme.dll");
        return module != NULL
            ? reinterpret_cast<AllowDarkModeForWindowFn>(::GetProcAddress(module, MAKEINTRESOURCEA(133)))
            : NULL;
    }

    void ApplyProcessMode()
    {
        SetPreferredAppModeFn setMode = ResolveSetPreferredAppMode();
        if (setMode != NULL)
            setMode(g_darkMode ? AppModeForceDark : AppModeForceLight);
    }

    bool IsClass(HWND window, LPCWSTR expected)
    {
        wchar_t className[80] = {};
        return ::GetClassNameW(window, className, _countof(className)) > 0
            && _wcsicmp(className, expected) == 0;
    }

    void ApplyOne(HWND window)
    {
        if (!::IsWindow(window))
            return;

        AllowDarkModeForWindowFn allowDark = ResolveAllowDarkModeForWindow();
        if (allowDark != NULL)
            allowDark(window, g_darkMode ? TRUE : FALSE);

        const BOOL enabled = g_darkMode ? TRUE : FALSE;
        // Attribute 20 is DWMWA_USE_IMMERSIVE_DARK_MODE on current Win10/11.
        // Attribute 19 is retained as fallback for earlier Win10 builds.
        if (FAILED(::DwmSetWindowAttribute(window, 20, &enabled, sizeof(enabled))))
            ::DwmSetWindowAttribute(window, 19, &enabled, sizeof(enabled));

        ::SetWindowTheme(window, g_darkMode ? L"DarkMode_Explorer" : L"Explorer", NULL);

        if (IsClass(window, WC_LISTVIEWW)) {
            const COLORREF background = g_darkMode ? CEmuleNextTheme::SurfaceColor() : ::GetSysColor(COLOR_WINDOW);
            const COLORREF text = g_darkMode ? CEmuleNextTheme::TextColor() : ::GetSysColor(COLOR_WINDOWTEXT);
            ListView_SetBkColor(window, background);
            ListView_SetTextBkColor(window, background);
            ListView_SetTextColor(window, text);
        }
        else if (IsClass(window, WC_TREEVIEWW)) {
            const COLORREF background = g_darkMode ? CEmuleNextTheme::SurfaceColor() : ::GetSysColor(COLOR_WINDOW);
            const COLORREF text = g_darkMode ? CEmuleNextTheme::TextColor() : ::GetSysColor(COLOR_WINDOWTEXT);
            TreeView_SetBkColor(window, background);
            TreeView_SetTextColor(window, text);
        }

        ::SendMessage(window, WM_THEMECHANGED, 0, 0);
        ::InvalidateRect(window, NULL, TRUE);
    }

    BOOL CALLBACK ApplyChild(HWND child, LPARAM)
    {
        ApplyOne(child);
        return TRUE;
    }
}

void CEmuleNextTheme::Initialize()
{
    g_darkMode = theApp.GetProfileInt(_T("eMule Next"), _T("DarkMode"), 1) != 0;
    ApplyProcessMode();
}

bool CEmuleNextTheme::IsDarkMode()
{
    return g_darkMode;
}

void CEmuleNextTheme::SetDarkMode(bool enabled)
{
    if (g_darkMode == enabled)
        return;
    g_darkMode = enabled;
    theApp.WriteProfileInt(_T("eMule Next"), _T("DarkMode"), enabled ? 1 : 0);
    ApplyProcessMode();
}

void CEmuleNextTheme::ApplyToWindow(HWND root)
{
    if (!::IsWindow(root))
        return;
    ApplyOne(root);
    ::EnumChildWindows(root, ApplyChild, 0);
    ::RedrawWindow(root, NULL, NULL,
        RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN | RDW_FRAME | RDW_UPDATENOW);
}

COLORREF CEmuleNextTheme::BackgroundColor()
{
    return RGB(28, 28, 30);
}

COLORREF CEmuleNextTheme::SurfaceColor()
{
    return RGB(38, 38, 42);
}

COLORREF CEmuleNextTheme::TextColor()
{
    return RGB(232, 232, 235);
}
