//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#include "stdafx.h"
#include "EmuleNextUiMetrics.h"

UINT CEmuleNextUiMetrics::DpiForWindow(HWND window)
{
    HDC dc = ::GetDC(window);
    HWND dcWindow = window;
    if (dc == NULL) {
        dc = ::GetDC(NULL);
        dcWindow = NULL;
    }
    UINT dpi = 96;
    if (dc != NULL) {
        const int value = ::GetDeviceCaps(dc, LOGPIXELSX);
        if (value > 0)
            dpi = static_cast<UINT>(value);
        ::ReleaseDC(dcWindow, dc);
    }
    if (dpi < 72)
        dpi = 72;
    if (dpi > 384)
        dpi = 384;
    return dpi;
}

int CEmuleNextUiMetrics::ScaleForDpi(int value96Dpi, UINT dpi)
{
    if (dpi == 0)
        dpi = 96;
    return ::MulDiv(value96Dpi, static_cast<int>(dpi), 96);
}

int CEmuleNextUiMetrics::Scale(HWND window, int value96Dpi)
{
    return ScaleForDpi(value96Dpi, DpiForWindow(window));
}
