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
    EmuleNextThemeMode g_themeMode = ENTM_DARK;
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

    bool SystemWantsDarkMode()
    {
        DWORD appsUseLightTheme = 1;
        DWORD bytes = sizeof(appsUseLightTheme);
        const LSTATUS status = ::RegGetValueW(HKEY_CURRENT_USER,
            L"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize",
            L"AppsUseLightTheme", RRF_RT_REG_DWORD, NULL, &appsUseLightTheme, &bytes);
        return status == ERROR_SUCCESS && appsUseLightTheme == 0;
    }

    void ResolveEffectiveMode()
    {
        if (g_themeMode == ENTM_SYSTEM)
            g_darkMode = SystemWantsDarkMode();
        else
            g_darkMode = g_themeMode == ENTM_DARK;
    }

    void ApplyProcessMode()
    {
        ResolveEffectiveMode();
        SetPreferredAppModeFn setMode = ResolveSetPreferredAppMode();
        if (setMode != NULL) {
            if (g_themeMode == ENTM_SYSTEM)
                setMode(AppModeAllowDark);
            else
                setMode(g_darkMode ? AppModeForceDark : AppModeForceLight);
        }
    }

    CStringW WindowClass(HWND window)
    {
        wchar_t className[96] = {};
        if (::GetClassNameW(window, className, _countof(className)) <= 0)
            return CStringW();
        return CStringW(className);
    }

    bool SameClass(const CStringW& actual, LPCWSTR expected)
    {
        return actual.CompareNoCase(expected) == 0;
    }

    void ApplyOne(HWND window)
    {
        if (!::IsWindow(window))
            return;

        AllowDarkModeForWindowFn allowDark = ResolveAllowDarkModeForWindow();
        if (allowDark != NULL)
            allowDark(window, g_darkMode ? TRUE : FALSE);

        const BOOL enabled = g_darkMode ? TRUE : FALSE;
        if (FAILED(::DwmSetWindowAttribute(window, 20, &enabled, sizeof(enabled))))
            ::DwmSetWindowAttribute(window, 19, &enabled, sizeof(enabled));

        const CStringW className = WindowClass(window);
        LPCWSTR theme = g_darkMode ? L"DarkMode_Explorer" : L"Explorer";
        if (SameClass(className, L"Edit") || SameClass(className, L"RichEdit20W")
            || SameClass(className, L"RICHEDIT50W") || SameClass(className, L"ComboBox")) {
            theme = g_darkMode ? L"DarkMode_CFD" : L"Explorer";
        }
        ::SetWindowTheme(window, theme, NULL);

        const COLORREF background = g_darkMode ? CEmuleNextTheme::SurfaceColor() : ::GetSysColor(COLOR_WINDOW);
        const COLORREF text = g_darkMode ? CEmuleNextTheme::TextColor() : ::GetSysColor(COLOR_WINDOWTEXT);

        if (SameClass(className, WC_LISTVIEWW)) {
            ListView_SetBkColor(window, background);
            ListView_SetTextBkColor(window, background);
            ListView_SetTextColor(window, text);
        }
        else if (SameClass(className, WC_TREEVIEWW)) {
            TreeView_SetBkColor(window, background);
            TreeView_SetTextColor(window, text);
        }
        else if (SameClass(className, L"RichEdit20W") || SameClass(className, L"RICHEDIT50W")) {
            ::SendMessage(window, EM_SETBKGNDCOLOR, 0, background);
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
    int storedMode = theApp.GetProfileInt(_T("eMule Next"), _T("ThemeMode"), -1);
    if (storedMode < ENTM_SYSTEM || storedMode > ENTM_DARK) {
        // Migration from the first eMule Next builds.
        const bool oldDark = theApp.GetProfileInt(_T("eMule Next"), _T("DarkMode"), 1) != 0;
        storedMode = oldDark ? ENTM_DARK : ENTM_LIGHT;
        theApp.WriteProfileInt(_T("eMule Next"), _T("ThemeMode"), storedMode);
    }
    g_themeMode = static_cast<EmuleNextThemeMode>(storedMode);
    ApplyProcessMode();
}

EmuleNextThemeMode CEmuleNextTheme::GetMode()
{
    return g_themeMode;
}

void CEmuleNextTheme::SetMode(EmuleNextThemeMode mode)
{
    if (mode < ENTM_SYSTEM || mode > ENTM_DARK)
        mode = ENTM_SYSTEM;
    g_themeMode = mode;
    theApp.WriteProfileInt(_T("eMule Next"), _T("ThemeMode"), static_cast<int>(mode));
    theApp.WriteProfileInt(_T("eMule Next"), _T("DarkMode"), mode == ENTM_DARK ? 1 : 0);
    ApplyProcessMode();
}

bool CEmuleNextTheme::IsDarkMode()
{
    return g_darkMode;
}

void CEmuleNextTheme::SetDarkMode(bool enabled)
{
    SetMode(enabled ? ENTM_DARK : ENTM_LIGHT);
}

void CEmuleNextTheme::RefreshSystemMode()
{
    if (g_themeMode == ENTM_SYSTEM)
        ApplyProcessMode();
}

void CEmuleNextTheme::ApplyToWindow(HWND root)
{
    if (!::IsWindow(root))
        return;
    ResolveEffectiveMode();
    ApplyOne(root);
    ::EnumChildWindows(root, ApplyChild, 0);
    ::RedrawWindow(root, NULL, NULL,
        RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN | RDW_FRAME | RDW_UPDATENOW);
}

COLORREF CEmuleNextTheme::BackgroundColor()
{
    return RGB(24, 25, 28);
}

COLORREF CEmuleNextTheme::SurfaceColor()
{
    return RGB(32, 34, 38);
}

COLORREF CEmuleNextTheme::SurfaceAltColor()
{
    return RGB(42, 45, 50);
}

COLORREF CEmuleNextTheme::BorderColor()
{
    return RGB(70, 74, 82);
}

COLORREF CEmuleNextTheme::TextColor()
{
    return RGB(235, 237, 240);
}

COLORREF CEmuleNextTheme::MutedTextColor()
{
    return RGB(165, 170, 178);
}

COLORREF CEmuleNextTheme::AccentColor()
{
    return RGB(72, 144, 230);
}
