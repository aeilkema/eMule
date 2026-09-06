#!/usr/bin/env python3
"""Materialize Library 2.0 writer-queue mutations.

Library 2 never writes SQLite from the GUI. Download-Later removal, path
verification and relinking are queued on the existing eMule Next database
writer thread. File identity is always ED2K hash + size.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
HEADER = SRC / "EmuleNextDatabase.h"
CPP = SRC / "EmuleNextDatabase.cpp"


def read(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def write(path: pathlib.Path, text: str, encoding: str) -> None:
    path.write_bytes(text.encode(encoding))


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Library 2 database: expected one {label} anchor, found {count}")
    return text.replace(old, new, 1)


def patch_header() -> None:
    text, enc = read(HEADER)
    marker = "void RemoveDownloadLater(const EmuleNextHash16& fileHash, uint64 fileSize);"
    if marker not in text:
        old = """    void SaveDownloadLater(const EmuleNextFileObservation& file);\n    void MarkLibraryCompleted(const EmuleNextFileObservation& file, const CStringW& localPath);"""
        new = """    void SaveDownloadLater(const EmuleNextFileObservation& file);\n    void RemoveDownloadLater(const EmuleNextHash16& fileHash, uint64 fileSize);\n    void UpdateLibraryVerification(const EmuleNextHash16& fileHash, uint64 fileSize, bool missing);\n    void RelinkLibraryFile(const EmuleNextHash16& fileHash, uint64 fileSize, const CStringW& localPath);\n    void MarkLibraryCompleted(const EmuleNextFileObservation& file, const CStringW& localPath);"""
        text = replace_once(text, old, new, "public mutation API")
    write(HEADER, text, enc)


def patch_cpp() -> None:
    text, enc = read(CPP)

    if "RemoveDownloadLater," not in text:
        old = """        RemoveFavorite,\n        DownloadLater,\n        LibraryCompleted"""
        new = """        RemoveFavorite,\n        DownloadLater,\n        RemoveDownloadLater,\n        LibraryVerified,\n        LibraryRelinked,\n        LibraryCompleted"""
        text = replace_once(text, old, new, "event kinds")

    if "bool missing;" not in text:
        old = """        uint64 fileSize;\n        CStringW localPath;\n\n        explicit DatabaseEvent(EventKind value)\n            : kind(value), fileSize(0)"""
        new = """        uint64 fileSize;\n        CStringW localPath;\n        bool missing;\n\n        explicit DatabaseEvent(EventKind value)\n            : kind(value), fileSize(0), missing(false)"""
        text = replace_once(text, old, new, "event missing flag")

    marker = "if (event.kind == EventKind::RemoveDownloadLater && event.hash.valid)"
    if marker not in text:
        anchor = """        EmuleNextFileObservation file;\n        if (event.kind == EventKind::SaveFavorite) {"""
        block = """        if (event.kind == EventKind::RemoveDownloadLater && event.hash.valid) {\n            sqlite3_stmt* stmt = NULL;\n            if (sqlite3_prepare_v2(db, \"DELETE FROM download_later WHERE file_id=(SELECT id FROM files WHERE ed2k_hash=?1 AND size=?2)\", -1, &stmt, NULL) == SQLITE_OK) {\n                BindHash(stmt, 1, event.hash);\n                sqlite3_bind_int64(stmt, 2, static_cast<sqlite3_int64>(event.fileSize));\n                sqlite3_step(stmt);\n            }\n            if (stmt != NULL) sqlite3_finalize(stmt);\n            return;\n        }\n        if (event.kind == EventKind::LibraryVerified && event.hash.valid) {\n            sqlite3_stmt* stmt = NULL;\n            const char* sql = event.missing\n                ? \"UPDATE library_entries SET last_verified=?3,missing_since=COALESCE(missing_since,?3) WHERE file_id=(SELECT id FROM files WHERE ed2k_hash=?1 AND size=?2)\"\n                : \"UPDATE library_entries SET last_verified=?3,missing_since=NULL WHERE file_id=(SELECT id FROM files WHERE ed2k_hash=?1 AND size=?2)\";\n            if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) == SQLITE_OK) {\n                BindHash(stmt, 1, event.hash);\n                sqlite3_bind_int64(stmt, 2, static_cast<sqlite3_int64>(event.fileSize));\n                sqlite3_bind_int64(stmt, 3, static_cast<sqlite3_int64>(NowSeconds()));\n                sqlite3_step(stmt);\n            }\n            if (stmt != NULL) sqlite3_finalize(stmt);\n            return;\n        }\n        if (event.kind == EventKind::LibraryRelinked && event.hash.valid && !event.localPath.IsEmpty()) {\n            sqlite3_stmt* stmt = NULL;\n            if (sqlite3_prepare_v2(db, \"UPDATE library_entries SET local_path=?3,last_verified=?4,missing_since=NULL WHERE file_id=(SELECT id FROM files WHERE ed2k_hash=?1 AND size=?2)\", -1, &stmt, NULL) == SQLITE_OK) {\n                BindHash(stmt, 1, event.hash);\n                sqlite3_bind_int64(stmt, 2, static_cast<sqlite3_int64>(event.fileSize));\n                BindText(stmt, 3, event.localPath);\n                sqlite3_bind_int64(stmt, 4, static_cast<sqlite3_int64>(NowSeconds()));\n                sqlite3_step(stmt);\n            }\n            if (stmt != NULL) sqlite3_finalize(stmt);\n            return;\n        }\n\n"""
        if anchor not in text:
            raise SystemExit("Library 2 database: ProcessEvent mutation anchor missing")
        text = text.replace(anchor, block + anchor, 1)

    if "CEmuleNextDatabase::RemoveDownloadLater" not in text:
        old = """void CEmuleNextDatabase::SaveDownloadLater(const EmuleNextFileObservation& file) { DatabaseEvent e(EventKind::DownloadLater); e.file = file; m_impl->Queue(std::move(e)); }\nvoid CEmuleNextDatabase::MarkLibraryCompleted"""
        new = """void CEmuleNextDatabase::SaveDownloadLater(const EmuleNextFileObservation& file) { DatabaseEvent e(EventKind::DownloadLater); e.file = file; m_impl->Queue(std::move(e)); }\nvoid CEmuleNextDatabase::RemoveDownloadLater(const EmuleNextHash16& fileHash, uint64 fileSize) { DatabaseEvent e(EventKind::RemoveDownloadLater); e.hash = fileHash; e.fileSize = fileSize; m_impl->Queue(std::move(e)); }\nvoid CEmuleNextDatabase::UpdateLibraryVerification(const EmuleNextHash16& fileHash, uint64 fileSize, bool missing) { DatabaseEvent e(EventKind::LibraryVerified); e.hash = fileHash; e.fileSize = fileSize; e.missing = missing; m_impl->Queue(std::move(e)); }\nvoid CEmuleNextDatabase::RelinkLibraryFile(const EmuleNextHash16& fileHash, uint64 fileSize, const CStringW& localPath) { DatabaseEvent e(EventKind::LibraryRelinked); e.hash = fileHash; e.fileSize = fileSize; e.localPath = localPath; m_impl->Queue(std::move(e)); }\nvoid CEmuleNextDatabase::MarkLibraryCompleted"""
        text = replace_once(text, old, new, "public mutation implementations")

    write(CPP, text, enc)


def main() -> int:
    for path in (HEADER, CPP):
        if not path.exists():
            raise SystemExit(f"Library 2 database: missing {path}")
    patch_header()
    patch_cpp()
    print("Library 2.0 queued database mutations materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
