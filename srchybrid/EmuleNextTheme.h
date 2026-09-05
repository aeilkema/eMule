//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

class CEmuleNextTheme
{
public:
    // Dark mode is enabled by default for eMule Next. The preference is stored
    // in the normal eMule INI/profile and can be toggled without rebuilding.
    static void Initialize();
    static bool IsDarkMode();
    static void SetDarkMode(bool enabled);

    // Apply to an existing window tree. Safe to call repeatedly as new MFC
    // pages/controls are created.
    static void ApplyToWindow(HWND root);

    static COLORREF BackgroundColor();
    static COLORREF SurfaceColor();
    static COLORREF TextColor();
};
