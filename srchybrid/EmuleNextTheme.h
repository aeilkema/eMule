//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

enum EmuleNextThemeMode
{
    ENTM_SYSTEM = 0,
    ENTM_LIGHT = 1,
    ENTM_DARK = 2
};

class CEmuleNextTheme
{
public:
    // eMule Next supports System/Light/Dark. Existing installs which only have
    // the old DarkMode boolean are migrated automatically on first start.
    static void Initialize();
    static EmuleNextThemeMode GetMode();
    static void SetMode(EmuleNextThemeMode mode);
    static bool IsDarkMode();
    static void SetDarkMode(bool enabled); // compatibility shortcut
    static void RefreshSystemMode();

    // Apply to an existing window tree. Safe to call repeatedly as new MFC
    // pages/controls are created.
    static void ApplyToWindow(HWND root);

    static COLORREF BackgroundColor();
    static COLORREF SurfaceColor();
    static COLORREF SurfaceAltColor();
    static COLORREF BorderColor();
    static COLORREF TextColor();
    static COLORREF MutedTextColor();
    static COLORREF AccentColor();
};
