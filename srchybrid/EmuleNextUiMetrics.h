//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

class CEmuleNextUiMetrics
{
public:
    static UINT DpiForWindow(HWND window);
    static int Scale(HWND window, int value96Dpi);
    static int ScaleForDpi(int value96Dpi, UINT dpi);
};
