#!/usr/bin/env python3
"""Repair legacy compatibility regressions before the final Preview 2 layer.

This helper remains the last base-activation step. It only repairs legacy
compile-compatibility contracts. The outer activate-features.py entry point is
the single owner that invokes activate-preview2.py exactly once afterwards.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


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


def replace_if_present(text: str, old: str, new: str) -> str:
    return text.replace(old, new, 1) if old in text else text


def patch_client_list_header() -> None:
    path = SRC / "ClientList.h"
    text, newline = load(path)

    text = replace_if_present(
        text,
        "\tbool\tIncomingBuddy(const Kademlia::CContact &contact, const Kademlia::CUInt128 &buddyID);\n",
        "\tbool\tIncomingBuddy(const Kademlia::CContact *contact, const Kademlia::CUInt128 &buddyID);\n",
    )

    duplicate = (
        "\tCClientIndex m_index;\n"
        "\tCPeerShareScanner m_peerShareScanner;\n"
        "\t// Fast identity/endpoint lookup kept in lock-step with the canonical MFC list.\n"
        "\tCClientIndex m_index;\n"
    )
    corrected = (
        "\t// Fast identity/endpoint lookup kept in lock-step with the canonical MFC list.\n"
        "\tCClientIndex m_index;\n"
        "\tCPeerShareScanner m_peerShareScanner;\n"
    )
    text = replace_if_present(text, duplicate, corrected)

    if text.count("CClientIndex m_index;") != 1:
        raise RuntimeError("ClientList.h must contain exactly one CClientIndex m_index member")
    if "IncomingBuddy(const Kademlia::CContact *contact" not in text:
        raise RuntimeError("ClientList.h IncomingBuddy pointer signature was not restored")

    save(path, text, newline)


def patch_client_list_cpp() -> None:
    path = SRC / "ClientList.cpp"
    text, newline = load(path)

    text = replace_if_present(
        text,
        "\tnextMaxConcurrent = max(1, min(8, nextMaxConcurrent));\n",
        "\tif (nextMaxConcurrent < 1)\n"
        "\t\tnextMaxConcurrent = 1;\n"
        "\telse if (nextMaxConcurrent > 8)\n"
        "\t\tnextMaxConcurrent = 8;\n",
    )
    text = replace_if_present(
        text,
        "\tmaxConcurrent = max<uint32>(1, min<uint32>(8, maxConcurrent));\n",
        "\tif (maxConcurrent < 1)\n"
        "\t\tmaxConcurrent = 1;\n"
        "\telse if (maxConcurrent > 8)\n"
        "\t\tmaxConcurrent = 8;\n",
    )

    if "max<uint32>" in text or "nextMaxConcurrent = max(" in text:
        raise RuntimeError("ClientList.cpp still contains incompatible min/max clamp syntax")
    save(path, text, newline)


def patch_settings() -> None:
    path = SRC / "EmuleNextSettingsWnd.cpp"
    text, newline = load(path)

    replacement = (
        "    if (concurrent < 1)\n"
        "        concurrent = 1;\n"
        "    else if (concurrent > 8)\n"
        "        concurrent = 8;\n"
    )
    text = text.replace("    concurrent = max(1, min(8, concurrent));\n", replacement)
    if "concurrent = max(1, min(8, concurrent))" in text:
        raise RuntimeError("EmuleNextSettingsWnd.cpp still contains incompatible min/max clamp syntax")
    save(path, text, newline)


def patch_theme() -> None:
    path = SRC / "EmuleNextTheme.cpp"
    text, newline = load(path)

    old = '''    bool SystemWantsDarkMode()
    {
        DWORD appsUseLightTheme = 1;
        DWORD bytes = sizeof(appsUseLightTheme);
        const LSTATUS status = ::RegGetValueW(HKEY_CURRENT_USER,
            L"Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Themes\\\\Personalize",
            L"AppsUseLightTheme", RRF_RT_REG_DWORD, NULL, &appsUseLightTheme, &bytes);
        return status == ERROR_SUCCESS && appsUseLightTheme == 0;
    }
'''
    new = '''    bool SystemWantsDarkMode()
    {
        HKEY key = NULL;
        DWORD appsUseLightTheme = 1;
        DWORD type = 0;
        DWORD bytes = sizeof(appsUseLightTheme);
        if (::RegOpenKeyExW(HKEY_CURRENT_USER,
            L"Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Themes\\\\Personalize",
            0, KEY_QUERY_VALUE, &key) != ERROR_SUCCESS) {
            return false;
        }

        const LSTATUS status = ::RegQueryValueExW(key, L"AppsUseLightTheme",
            NULL, &type, reinterpret_cast<LPBYTE>(&appsUseLightTheme), &bytes);
        ::RegCloseKey(key);
        return status == ERROR_SUCCESS && type == REG_DWORD && appsUseLightTheme == 0;
    }
'''
    text = replace_if_present(text, old, new)
    if "RegGetValueW" in text:
        raise RuntimeError("EmuleNextTheme.cpp still uses RegGetValueW")
    if "RegQueryValueExW" not in text:
        raise RuntimeError("EmuleNextTheme.cpp registry compatibility replacement is missing")
    save(path, text, newline)


def main() -> int:
    patch_client_list_header()
    patch_client_list_cpp()
    patch_settings()
    patch_theme()
    print("eMule Next legacy compile compatibility fixes active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
