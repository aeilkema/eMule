#!/usr/bin/env python3
'''Apply Preview 2 theme coverage to the legacy Messages/Chat workspace.'''
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
H = SRC / "ChatWnd.h"
CPP = SRC / "ChatWnd.cpp"
SEL_H = SRC / "ChatSelector.h"
SEL = SRC / "ChatSelector.cpp"


def load(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes()
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    newline = "\r\n" if crlf >= lf and crlf else "\n"
    return raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n"), newline


def save(path: pathlib.Path, text: str, newline: str) -> None:
    if newline != "\n":
        text = text.replace("\n", newline)
    path.write_bytes(text.encode("latin-1"))


def main() -> int:
    h, hn = load(H)
    cpp, cn = load(CPP)
    sel_h, shn = load(SEL_H)
    sel, sn = load(SEL)

    if "CBrush m_preview2ThemeBrush;" not in h:
        anchor = "\tCButton m_wndClose;\n"
        if anchor not in h:
            raise SystemExit("Preview2 theme coverage: ChatWnd member anchor missing")
        h = h.replace(anchor, anchor + "\tCBrush m_preview2ThemeBrush;\n", 1)
    if "void ApplyPreview2Theme();" not in h:
        anchor = "\tvoid SetAllIcons();\n"
        if anchor not in h:
            raise SystemExit("Preview2 theme coverage: ChatWnd helper anchor missing")
        h = h.replace(anchor, anchor + "\tvoid ApplyPreview2Theme();\n", 1)

    if "void ApplyPreview2Theme();" not in sel_h:
        anchor = "\tvoid\t\tUpdateFonts(CFont *pFont);\n"
        if anchor not in sel_h:
            raise SystemExit("Preview2 theme coverage: ChatSelector public helper anchor missing")
        sel_h = sel_h.replace(anchor, anchor + "\tvoid\t\tApplyPreview2Theme();\n", 1)

    for inc in ('#include "EmuleNextTheme.h"', '#include "EmuleNextModernUi.h"'):
        if inc not in cpp:
            anchor = '#include "SmileySelector.h"\n'
            if anchor not in cpp:
                raise SystemExit("Preview2 theme coverage: ChatWnd include anchor missing")
            cpp = cpp.replace(anchor, anchor + inc + "\n", 1)

    if "ApplyPreview2Theme();" not in cpp[cpp.find("BOOL CChatWnd::OnInitDialog()"):cpp.find("void CChatWnd::DoResize")]:
        anchor = "\tInitWindowStyles(this);\n"
        if anchor not in cpp:
            raise SystemExit("Preview2 theme coverage: ChatWnd init anchor missing")
        cpp = cpp.replace(anchor, anchor + "\tApplyPreview2Theme();\n", 1)

    if "void CChatWnd::ApplyPreview2Theme()" not in cpp:
        anchor = "void CChatWnd::SetAllIcons()\n"
        pos = cpp.find(anchor)
        if pos < 0:
            raise SystemExit("Preview2 theme coverage: ChatWnd insertion boundary missing")
        method = r'''void CChatWnd::ApplyPreview2Theme()
{
	if (m_preview2ThemeBrush.GetSafeHandle() != NULL)
		m_preview2ThemeBrush.DeleteObject();
	m_preview2ThemeBrush.CreateSolidBrush(CEmuleNextTheme::SurfaceColor());
	CEmuleNextTheme::ApplyToWindow(m_hWnd);
	CEmuleNextModernUi::ApplyList(m_FriendListCtrl);
	CEmuleNextModernUi::SetExplorerTheme(chatselector.m_hWnd);
	CEmuleNextModernUi::SetExplorerTheme(m_wndMessage.m_hWnd);
	CEmuleNextModernUi::SetExplorerTheme(m_wndSend.m_hWnd);
	CEmuleNextModernUi::SetExplorerTheme(m_wndClose.m_hWnd);
	CEmuleNextModernUi::SetExplorerTheme(m_wndFormat.m_hWnd);
	chatselector.ApplyPreview2Theme();
	Invalidate(TRUE);
}

'''
        cpp = cpp[:pos] + method + cpp[pos:]

    old_sys = '''void CChatWnd::OnSysColorChange()
{
	CResizableDialog::OnSysColorChange();
	SetAllIcons();
}
'''
    new_sys = '''void CChatWnd::OnSysColorChange()
{
	CResizableDialog::OnSysColorChange();
	SetAllIcons();
	ApplyPreview2Theme();
}
'''
    if old_sys in cpp:
        cpp = cpp.replace(old_sys, new_sys, 1)
    elif "ApplyPreview2Theme();" not in cpp[cpp.find("void CChatWnd::OnSysColorChange()"):cpp.find("void CChatWnd::UpdateFriendlistCount")]:
        raise SystemExit("Preview2 theme coverage: ChatWnd syscolor hook missing")

    old_ctl = '''HBRUSH CChatWnd::OnCtlColor(CDC *pDC, CWnd *pWnd, UINT nCtlColor)
{
	HBRUSH hbr = theApp.emuledlg->GetCtlColor(pDC, pWnd, nCtlColor);
	return hbr ? hbr : __super::OnCtlColor(pDC, pWnd, nCtlColor);
}'''
    new_ctl = '''HBRUSH CChatWnd::OnCtlColor(CDC *pDC, CWnd *pWnd, UINT nCtlColor)
{
	if (CEmuleNextTheme::IsDarkMode()) {
		pDC->SetTextColor(CEmuleNextTheme::TextColor());
		pDC->SetBkColor(CEmuleNextTheme::SurfaceColor());
		if (nCtlColor == CTLCOLOR_STATIC)
			pDC->SetBkMode(TRANSPARENT);
		if (nCtlColor == CTLCOLOR_STATIC || nCtlColor == CTLCOLOR_EDIT || nCtlColor == CTLCOLOR_DLG)
			return static_cast<HBRUSH>(m_preview2ThemeBrush.GetSafeHandle());
	}
	HBRUSH hbr = theApp.emuledlg->GetCtlColor(pDC, pWnd, nCtlColor);
	return hbr ? hbr : __super::OnCtlColor(pDC, pWnd, nCtlColor);
}'''
    if old_ctl in cpp:
        cpp = cpp.replace(old_ctl, new_ctl, 1)
    elif "m_preview2ThemeBrush.GetSafeHandle()" not in cpp[cpp.find("HBRUSH CChatWnd::OnCtlColor"):]:
        raise SystemExit("Preview2 theme coverage: ChatWnd color handler anchor missing")

    for inc in ('#include "EmuleNextTheme.h"', '#include "EmuleNextModernUi.h"'):
        if inc not in sel:
            anchor = '#include "FriendList.h"\n'
            if anchor not in sel:
                raise SystemExit("Preview2 theme coverage: ChatSelector include anchor missing")
            sel = sel.replace(anchor, anchor + inc + "\n", 1)

    if "void CChatSelector::ApplyPreview2Theme()" not in sel:
        anchor = "void CChatSelector::UpdateFonts(CFont *pFont)\n"
        pos = sel.find(anchor)
        if pos < 0:
            raise SystemExit("Preview2 theme coverage: ChatSelector method boundary missing")
        method = r'''void CChatSelector::ApplyPreview2Theme()
{
	CEmuleNextModernUi::SetExplorerTheme(m_hWnd);
	TCITEM ti = {};
	ti.mask = TCIF_PARAM;
	for (int i = 0; i < GetItemCount(); ++i) {
		if (!GetItem(i, &ti) || ti.lParam == NULL)
			continue;
		CChatItem* item = reinterpret_cast<CChatItem*>(ti.lParam);
		if (item->log == NULL || !::IsWindow(item->log->m_hWnd))
			continue;
		item->log->SetDfltForegroundColor(CEmuleNextTheme::TextColor());
		item->log->SetDfltBackgroundColor(CEmuleNextTheme::SurfaceColor());
		item->log->SetBackgroundColor(FALSE, CEmuleNextTheme::SurfaceColor());
		CEmuleNextModernUi::SetExplorerTheme(item->log->m_hWnd);
		item->log->Invalidate(TRUE);
	}
}

'''
        sel = sel[:pos] + method + sel[pos:]

    if "SetDfltForegroundColor(CEmuleNextTheme::TextColor())" not in sel[sel.find("CChatSelector::StartSession"):]:
        anchor = "\tchatitem->log->ApplySkin();\n"
        if anchor not in sel:
            raise SystemExit("Preview2 theme coverage: chat log skin anchor missing")
        addition = '''\tchatitem->log->SetDfltForegroundColor(CEmuleNextTheme::TextColor());
\tchatitem->log->SetDfltBackgroundColor(CEmuleNextTheme::SurfaceColor());
\tchatitem->log->SetBackgroundColor(FALSE, CEmuleNextTheme::SurfaceColor());
\tCEmuleNextModernUi::SetExplorerTheme(chatitem->log->m_hWnd);
'''
        sel = sel.replace(anchor, anchor + addition, 1)

    save(H, h, hn)
    save(CPP, cpp, cn)
    save(SEL_H, sel_h, shn)
    save(SEL, sel, sn)
    print("eMule Next Preview 2 Messages/Chat theme coverage materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
