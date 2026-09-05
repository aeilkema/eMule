//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later

#include "stdafx.h"
#include "DownloadIntelligenceWnd.h"

#include "EmuleNextRuntime.h"
#include "EmuleNextTheme.h"
#include "OtherFunctions.h"

#include <memory>

namespace
{
    enum
    {
        IDC_EN_DI_REFRESH = 0x7E30,
        IDC_EN_DI_SUMMARY,
        IDC_EN_DI_LIST
    };

    const UINT WM_EN_DI_LOADED = WM_APP + 0x565;
    const UINT_PTR TIMER_EN_DI_REFRESH = 0x565;

    struct TransferLoadContext
    {
        HWND target;
        CStringW databasePath;
    };

    struct TransferLoadResult
    {
        bool ok;
        std::vector<EmuleNextTransferHistoryRecord> rows;
        TransferLoadResult() : ok(false) {}
    };

    UINT AFX_CDECL LoadTransfersWorker(LPVOID value)
    {
        std::unique_ptr<TransferLoadContext> context(static_cast<TransferLoadContext*>(value));
        std::unique_ptr<TransferLoadResult> result(new TransferLoadResult);
        CDownloadIntelligenceService service(context->databasePath);
        result->ok = service.ListRecentTransfers(250, result->rows);
        if (::IsWindow(context->target)
            && ::PostMessage(context->target, WM_EN_DI_LOADED, 0, reinterpret_cast<LPARAM>(result.get()))) {
            result.release();
        }
        return 0;
    }
}

BEGIN_MESSAGE_MAP(CDownloadIntelligenceWnd, CWnd)
    ON_WM_CREATE()
    ON_WM_SIZE()
    ON_WM_DESTROY()
    ON_WM_TIMER()
    ON_WM_ERASEBKGND()
    ON_WM_CTLCOLOR()
    ON_BN_CLICKED(IDC_EN_DI_REFRESH, OnRefreshClicked)
    ON_MESSAGE(WM_EN_DI_LOADED, OnTransfersLoaded)
END_MESSAGE_MAP()

CDownloadIntelligenceWnd::CDownloadIntelligenceWnd()
    : m_loading(false)
    , m_refreshTimer(0)
{
}

CDownloadIntelligenceWnd::~CDownloadIntelligenceWnd()
{
}

bool CDownloadIntelligenceWnd::Create(CWnd* parent)
{
    if (parent == NULL)
        return false;
    const CString className = AfxRegisterWndClass(CS_DBLCLKS,
        ::LoadCursor(NULL, IDC_ARROW),
        reinterpret_cast<HBRUSH>(COLOR_WINDOW + 1), NULL);
    CRect empty(0, 0, 0, 0);
    return CWnd::CreateEx(0, className, _T("eMule Next Download Intelligence"),
        WS_CHILD | WS_CLIPCHILDREN | WS_CLIPSIBLINGS,
        empty, parent, 0) != FALSE;
}

int CDownloadIntelligenceWnd::OnCreate(LPCREATESTRUCT createStruct)
{
    if (CWnd::OnCreate(createStruct) == -1)
        return -1;

    m_darkBrush.CreateSolidBrush(CEmuleNextTheme::BackgroundColor());
    CRect empty(0, 0, 0, 0);
    if (!m_refreshButton.Create(_T("Refresh"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            empty, this, IDC_EN_DI_REFRESH)
        || !m_summary.Create(_T("Download Intelligence is loading recent sessions..."), WS_CHILD | WS_VISIBLE | SS_LEFT,
            empty, this, IDC_EN_DI_SUMMARY)
        || !m_transfers.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | LVS_REPORT | LVS_SINGLESEL | LVS_SHOWSELALWAYS,
            empty, this, IDC_EN_DI_LIST)) {
        return -1;
    }

    CFont* font = CFont::FromHandle(static_cast<HFONT>(::GetStockObject(DEFAULT_GUI_FONT)));
    m_refreshButton.SetFont(font);
    m_summary.SetFont(font);
    m_transfers.SetFont(font);
    m_transfers.SetExtendedStyle(LVS_EX_FULLROWSELECT | LVS_EX_DOUBLEBUFFER | LVS_EX_GRIDLINES);

    m_transfers.InsertColumn(0, _T("Finished"), LVCFMT_LEFT, 135);
    m_transfers.InsertColumn(1, _T("File"), LVCFMT_LEFT, 280);
    m_transfers.InsertColumn(2, _T("Network name"), LVCFMT_LEFT, 150);
    m_transfers.InsertColumn(3, _T("Alias"), LVCFMT_LEFT, 130);
    m_transfers.InsertColumn(4, _T("Transferred"), LVCFMT_RIGHT, 105);
    m_transfers.InsertColumn(5, _T("Average"), LVCFMT_RIGHT, 105);
    m_transfers.InsertColumn(6, _T("Status"), LVCFMT_LEFT, 85);
    m_transfers.InsertColumn(7, _T("Result"), LVCFMT_LEFT, 230);

    CEmuleNextTheme::ApplyToWindow(m_hWnd);
    m_refreshTimer = SetTimer(TIMER_EN_DI_REFRESH, 15000, NULL);
    Refresh(true);
    return 0;
}

void CDownloadIntelligenceWnd::OnDestroy()
{
    if (m_refreshTimer != 0) {
        KillTimer(m_refreshTimer);
        m_refreshTimer = 0;
    }
    CWnd::OnDestroy();
}

void CDownloadIntelligenceWnd::OnSize(UINT type, int cx, int cy)
{
    CWnd::OnSize(type, cx, cy);
    if (::IsWindow(m_transfers.m_hWnd))
        LayoutControls(cx, cy);
}

void CDownloadIntelligenceWnd::LayoutControls(int cx, int cy)
{
    const int margin = 8;
    const int buttonWidth = 84;
    const int headerHeight = 27;
    m_refreshButton.MoveWindow(margin, margin, buttonWidth, 23);
    m_summary.MoveWindow(margin + buttonWidth + 10, margin + 4,
        max(0, cx - margin * 2 - buttonWidth - 10), 20);
    m_transfers.MoveWindow(margin, margin + headerHeight,
        max(0, cx - margin * 2), max(0, cy - margin * 2 - headerHeight));
}

void CDownloadIntelligenceWnd::Refresh(bool force)
{
    if (m_loading || !theEmuleNext.IsRunning())
        return;
    if (!force && !IsWindowVisible())
        return;

    const CStringW path = theEmuleNext.Database().GetDatabasePath();
    if (path.IsEmpty())
        return;

    std::unique_ptr<TransferLoadContext> context(new TransferLoadContext);
    context->target = m_hWnd;
    context->databasePath = path;
    m_loading = true;
    m_summary.SetWindowText(_T("Loading recent transfer sessions..."));
    if (AfxBeginThread(LoadTransfersWorker, context.get(), THREAD_PRIORITY_BELOW_NORMAL) == NULL) {
        m_loading = false;
        m_summary.SetWindowText(_T("Unable to start Download Intelligence refresh."));
        return;
    }
    context.release();
}

void CDownloadIntelligenceWnd::Populate()
{
    m_transfers.SetRedraw(FALSE);
    m_transfers.DeleteAllItems();

    for (size_t i = 0; i < m_rows.size(); ++i) {
        const EmuleNextTransferHistoryRecord& item = m_rows[i];
        CString file(item.fileName);
        if (file.IsEmpty())
            file = _T("<unknown file>");
        CString user(item.userName);
        if (user.IsEmpty())
            user = _T("<unknown user>");
        CString alias;
        if (item.peerHash.valid)
            theEmuleNext.GetPeerAlias(item.peerHash.bytes.data(), alias);

        const int row = m_transfers.InsertItem(static_cast<int>(i), DateText(item.finishedAt));
        m_transfers.SetItemText(row, 1, file);
        m_transfers.SetItemText(row, 2, user);
        m_transfers.SetItemText(row, 3, alias);
        m_transfers.SetItemText(row, 4, CastItoXBytes(item.bytesTransferred, false, false, 1));
        CString speed;
        speed.Format(_T("%s/s"), (LPCTSTR)CastItoXBytes(item.averageBytesPerSecond, false, false, 1));
        m_transfers.SetItemText(row, 5, speed);
        m_transfers.SetItemText(row, 6, item.successful ? _T("Success") : _T("Failed"));
        m_transfers.SetItemText(row, 7, CString(item.result));
    }

    m_transfers.SetRedraw(TRUE);
    m_transfers.Invalidate(FALSE);
    UpdateSummary();
}

void CDownloadIntelligenceWnd::UpdateSummary()
{
    uint64 bytes = 0;
    uint64 weightedSpeedBytes = 0;
    uint64 weightedTransferred = 0;
    size_t successful = 0;
    for (size_t i = 0; i < m_rows.size(); ++i) {
        const EmuleNextTransferHistoryRecord& item = m_rows[i];
        bytes += item.bytesTransferred;
        if (item.successful)
            ++successful;
        if (item.bytesTransferred > 0 && item.averageBytesPerSecond > 0) {
            weightedSpeedBytes += static_cast<uint64>(item.averageBytesPerSecond) * item.bytesTransferred;
            weightedTransferred += item.bytesTransferred;
        }
    }
    const uint64 average = weightedTransferred > 0 ? weightedSpeedBytes / weightedTransferred : 0;
    CString text;
    text.Format(_T("Recent sessions: %u   Success: %u   Transferred: %s   Weighted avg: %s/s"),
        static_cast<unsigned>(m_rows.size()), static_cast<unsigned>(successful),
        (LPCTSTR)CastItoXBytes(bytes, false, false, 1),
        (LPCTSTR)CastItoXBytes(average, false, false, 1));
    m_summary.SetWindowText(text);
}

CString CDownloadIntelligenceWnd::DateText(uint64 timestamp)
{
    if (timestamp == 0)
        return CString();
    CTime time(static_cast<time_t>(timestamp));
    return time.Format(_T("%Y-%m-%d %H:%M"));
}

void CDownloadIntelligenceWnd::OnTimer(UINT_PTR timerId)
{
    if (timerId == TIMER_EN_DI_REFRESH) {
        Refresh(false);
        return;
    }
    CWnd::OnTimer(timerId);
}

BOOL CDownloadIntelligenceWnd::OnEraseBkgnd(CDC* dc)
{
    if (!CEmuleNextTheme::IsDarkMode())
        return CWnd::OnEraseBkgnd(dc);
    CRect rect;
    GetClientRect(&rect);
    dc->FillSolidRect(rect, CEmuleNextTheme::BackgroundColor());
    return TRUE;
}

HBRUSH CDownloadIntelligenceWnd::OnCtlColor(CDC* dc, CWnd* wnd, UINT ctlColor)
{
    if (!CEmuleNextTheme::IsDarkMode())
        return CWnd::OnCtlColor(dc, wnd, ctlColor);
    dc->SetTextColor(CEmuleNextTheme::TextColor());
    dc->SetBkColor(CEmuleNextTheme::BackgroundColor());
    if (ctlColor == CTLCOLOR_STATIC || ctlColor == CTLCOLOR_DLG)
        return static_cast<HBRUSH>(m_darkBrush.GetSafeHandle());
    return CWnd::OnCtlColor(dc, wnd, ctlColor);
}

void CDownloadIntelligenceWnd::OnRefreshClicked()
{
    Refresh(true);
}

LRESULT CDownloadIntelligenceWnd::OnTransfersLoaded(WPARAM, LPARAM value)
{
    std::unique_ptr<TransferLoadResult> result(reinterpret_cast<TransferLoadResult*>(value));
    m_loading = false;
    if (!result || !result->ok) {
        m_summary.SetWindowText(_T("Unable to read Download Intelligence history."));
        return 0;
    }
    m_rows.swap(result->rows);
    Populate();
    return 0;
}
