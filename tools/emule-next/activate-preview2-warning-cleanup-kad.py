#!/usr/bin/env python3
'''Fix the real x64 Kad vararg truncation warnings.'''
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


def load(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes(); crlf = raw.count(b"\r\n"); lf = raw.count(b"\n") - crlf
    nl = "\r\n" if crlf >= lf and crlf else "\n"
    return raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n"), nl

def save(path: pathlib.Path, text: str, nl: str) -> None:
    if nl != "\n": text = text.replace("\n", nl)
    path.write_bytes(text.encode("latin-1"))

def main() -> int:
    search_list = SRC / "SearchList.cpp"
    text, nl = load(search_list)
    old = '''\t\tUINT uPropType = va_arg(args, UINT);\n\t\tLPCSTR pszPropName = va_arg(args, LPCSTR);\n\t\tLPCTSTR pvPropValue = va_arg(args, LPCTSTR);\n\t\tif (uPropType == TAGTYPE_STRING) {\n\t\t\tif (pvPropValue && *pvPropValue) {\n\t\t\t\tif (strlen(pszPropName) == 1) {\n\t\t\t\t\tCTag tagProp((uint8)*pszPropName, pvPropValue);\n\t\t\t\t\ttagProp.WriteTagToFile(temp, eStrEncode);\n\t\t\t\t} else {\n\t\t\t\t\tCTag tagProp(pszPropName, pvPropValue);\n\t\t\t\t\ttagProp.WriteTagToFile(temp, eStrEncode);\n\t\t\t\t}\n\t\t\t\tverifierEntry.AddTag(new Kademlia::CKadTagStr(pszPropName, pvPropValue));\n\t\t\t\t++tagcount;\n\t\t\t}\n\t\t} else if (uPropType == TAGTYPE_UINT32) {\n\t\t\tif ((uint32)pvPropValue != 0) {\n\t\t\t\tCTag tagProp(pszPropName, (uint32)pvPropValue);\n\t\t\t\ttagProp.WriteTagToFile(temp, eStrEncode);\n\t\t\t\t++tagcount;\n\t\t\t\tverifierEntry.AddTag(new Kademlia::CKadTagUInt(pszPropName, (uint32)pvPropValue));\n\t\t\t}\n\t\t} else\n\t\t\tASSERT(0);\n'''
    new = '''\t\tUINT uPropType = va_arg(args, UINT);\n\t\tLPCSTR pszPropName = va_arg(args, LPCSTR);\n\t\tif (uPropType == TAGTYPE_STRING) {\n\t\t\tLPCTSTR pszPropValue = va_arg(args, LPCTSTR);\n\t\t\tif (pszPropValue && *pszPropValue) {\n\t\t\t\tif (strlen(pszPropName) == 1) { CTag tagProp((uint8)*pszPropName, pszPropValue); tagProp.WriteTagToFile(temp, eStrEncode); }\n\t\t\t\telse { CTag tagProp(pszPropName, pszPropValue); tagProp.WriteTagToFile(temp, eStrEncode); }\n\t\t\t\tverifierEntry.AddTag(new Kademlia::CKadTagStr(pszPropName, pszPropValue)); ++tagcount;\n\t\t\t}\n\t\t} else if (uPropType == TAGTYPE_UINT32) {\n\t\t\tconst uint32 uPropValue = va_arg(args, uint32);\n\t\t\tif (uPropValue != 0) { CTag tagProp(pszPropName, uPropValue); tagProp.WriteTagToFile(temp, eStrEncode); ++tagcount; verifierEntry.AddTag(new Kademlia::CKadTagUInt(pszPropName, uPropValue)); }\n\t\t} else { ASSERT(0); (void)va_arg(args, LPCTSTR); }\n'''
    if old in text: text = text.replace(old, new, 1)
    elif "const uint32 uPropValue = va_arg(args, uint32);" not in text: raise SystemExit("Kad warning cleanup: varargs block missing")
    save(search_list, text, nl)

    kad = SRC / "kademlia" / "kademlia" / "Search.cpp"
    text, nl = load(kad)
    for name in ("uLength", "uBitrate", "uAvailability"): text = text.replace(f"(LPCTSTR){name}", name)
    text = text.replace("#pragma warning(push)\n#pragma warning(disable:4312)\nvoid CSearch::ProcessResultKeyword", "void CSearch::ProcessResultKeyword", 1)
    text = text.replace("}\n#pragma warning(pop)\n\nvoid CSearch::SendFindValue", "}\n\nvoid CSearch::SendFindValue", 1)
    save(kad, text, nl)
    print("Preview 2 Kad x64 warning cleanup materialized"); return 0

if __name__ == "__main__": raise SystemExit(main())
