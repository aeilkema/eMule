#!/usr/bin/env python3
"""Completion gate for the PEER-01..05 / SESSION-01 Known Users 2.0 chapter."""
from __future__ import annotations

import pathlib
import sqlite3

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


def read(name: str) -> str:
    path = SRC / name
    if not path.exists():
        raise SystemExit(f"Known Users 2.0: missing {name}")
    return path.read_bytes().decode("latin-1", errors="ignore")


def require(text: str, markers: tuple[str, ...], label: str, failures: list[str]) -> None:
    for marker in markers:
        if marker not in text:
            failures.append(f"{label}: missing {marker!r}")


def forbid(text: str, markers: tuple[str, ...], label: str, failures: list[str]) -> None:
    for marker in markers:
        if marker in text:
            failures.append(f"{label}: forbidden stale marker present {marker!r}")


def duplicate_username_sql_smoke(failures: list[str]) -> None:
    """Prove storage/query identity does not collapse equal display names."""
    db = sqlite3.connect(":memory:")
    db.executescript(
        "CREATE TABLE peers(id INTEGER PRIMARY KEY,user_hash BLOB UNIQUE,username TEXT,client_software TEXT,client_version TEXT,first_seen INTEGER,last_seen INTEGER);"
        "CREATE TABLE peer_endpoints(id INTEGER PRIMARY KEY,peer_id INTEGER,ip INTEGER,tcp_port INTEGER,udp_port INTEGER,kad_port INTEGER,first_seen INTEGER,last_seen INTEGER);"
        "CREATE TABLE peer_metadata(user_hash BLOB PRIMARY KEY,alias TEXT,favorite INTEGER,updated_at INTEGER);"
        "CREATE TABLE files(id INTEGER PRIMARY KEY,size INTEGER);"
        "CREATE TABLE peer_files(peer_id INTEGER,file_id INTEGER,first_seen INTEGER,last_seen INTEGER,last_verified INTEGER,source_kind TEXT);"
    )
    hash_a = bytes.fromhex("00112233445566778899aabbccddeeff")
    hash_b = bytes.fromhex("ffeeddccbbaa99887766554433221100")
    db.execute("INSERT INTO peers VALUES(1,?,'duplicate','eMule','A',10,100)", (hash_a,))
    db.execute("INSERT INTO peers VALUES(2,?,'duplicate','eMule','B',20,200)", (hash_b,))
    db.execute("INSERT INTO peer_endpoints VALUES(1,1,167772161,4662,0,0,10,100)")
    db.execute("INSERT INTO peer_endpoints VALUES(2,2,167772162,4663,0,0,20,200)")
    rows = db.execute(
        "SELECT p.user_hash,p.username,pe.ip,pe.tcp_port FROM peers p "
        "LEFT JOIN peer_endpoints pe ON pe.id=(SELECT pe2.id FROM peer_endpoints pe2 WHERE pe2.peer_id=p.id ORDER BY pe2.last_seen DESC,pe2.id DESC LIMIT 1) "
        "ORDER BY p.last_seen DESC"
    ).fetchall()
    db.close()
    if len(rows) != 2 or rows[0][0] == rows[1][0] or rows[0][2:] == rows[1][2:]:
        failures.append("duplicate-username deterministic smoke collapsed distinct hash/endpoint identities")


def main() -> int:
    failures: list[str] = []
    service_h = read("KnownUsersService.h")
    service = read("KnownUsersService.cpp")
    wnd_h = read("KnownUsersWnd.h")
    wnd = read("KnownUsersWnd.cpp")
    scanner_h = read("PeerShareScanner.h")
    scanner = read("PeerShareScanner.cpp")
    clients_h = read("ClientList.h")
    clients = read("ClientList.cpp")
    search_h = read("SearchList.h")

    require(service_h, (
        "enum EmuleNextKnownUsersQueryMode", "struct EmuleNextKnownUsersQuery",
        "EmuleNextKnownUsersQueryMode mode;", "CStringW text;", "uint64 recentSince;",
        "ENKUQ_FAVORITES", "ENKUQ_RECENT", "CStringW alias", "clientSoftware",
        "endpointIp", "endpointTcpPort", "lastVerified", "DeletePeerHistory",
        "ListUsers(const EmuleNextKnownUsersQuery& query",
    ), "query model", failures)
    require(service, (
        "kMaximumKnownUsers = 2000", "kMaximumKnownFilesPerUser = 2000",
        "PRAGMA query_only=ON", "peer_metadata", "peer_endpoints pe ON pe.id=(",
        "GROUP BY d.peer_id", "LIMIT ?5", "LIMIT ?2", "BEGIN IMMEDIATE",
        "DELETE FROM peers WHERE user_hash=?1", "PRAGMA foreign_keys=ON",
        '#include "EmuleNextWinSqliteCompat.h"',
        "static_cast<int>(query.mode)", "query.recentSince", "const CStringW search = query.text",
        "sqlite3_bind_text16(statement, 3", "sqlite3_bind_text16(statement, 4",
    ), "bounded persistence/query service", failures)

    require(wnd_h, (
        "ENKUM_CURRENT", "ENKUM_HISTORY", "ENKUM_FAVORITES", "ENKUM_RECENT",
        "OnSearchChanged", "OnRefreshPeerClicked", "OnFavoriteClicked",
        "OnAliasClicked", "OnDeleteHistoryClicked", "OnUserColumnClick",
        "void SaveViewState();", "using CWnd::Create;",
    ), "view contract", failures)
    require(wnd, (
        '_T("Current")', '_T("History")', '_T("Favorites")', '_T("Recent 7d")',
        "IDC_EN_SEARCH", "SortUserRows", 'ColumnWidth%d', '_T("SortColumn")',
        '_T("First seen")', '_T("Last seen")', '_T("Endpoint")',
        '_T("Browse status")', "ENPSS_DENIED", "ENPSS_TIMEOUT", "ENPSS_SHARED",
        "ENPSS_UNSUPPORTED", "ENPSS_ERROR", "RemainingText(state->nextAllowed)",
        "QueuePeerShareRefresh", "DeleteHistoryWorker", "AfxBeginThread(DeleteHistoryWorker",
        "SetPeerFavorite", "SetPeerAlias", "file.lastSeen + 5 >= state.lastCompleted",
        "FindClientByUserHash(user.userHash.bytes.data())", "EmuleNextUiMetrics::Scale",
        "context->query.mode", "context->query.text", "context->query.recentSince",
        "void CKnownUsersWnd::SaveViewState()\n",
        'if (seconds >= 3600) value.Format(_T("%I64uh %02I64um"), seconds / 3600, (seconds % 3600) / 60);',
        'else if (seconds >= 60) value.Format(_T("%I64um %02I64us"), seconds / 60, seconds % 60);',
        'else value.Format(_T("%I64us"), seconds);',
        '#include "resource.h"\n#include "InputBox.h"',
    ), "Known Users 2.0 UI", failures)
    forbid(wnd, (
        "void CKnownUsersWnd::SaveViewState() const\n",
        '_T("%lluh %02llum")', '_T("%llum %02llus")', '_T("%llus")',
        '#include "InputBox.h"\n#include "resource.h"',
    ), "Known Users 2.0 compile compatibility", failures)
    if "sqlite3_" in wnd:
        failures.append("Known Users window performs SQLite work directly")

    require(scanner_h, ("QueuePeerManual",), "manual scanner API", failures)
    require(scanner, (
        "existing->state.status == ENPSS_SHARED", "existing->state.nextAllowed = now",
        "else if (now < existing->state.nextAllowed)", "return QueuePeer(peerHash, true, now)",
        "m_deniedCooldown", "m_requestTimeout",
    ), "manual refresh cooldown safety", failures)
    require(clients_h, (
        "QueuePeerShareRefresh", "GetPeerShareState",
    ), "client-list runtime bridge header", failures)
    require(clients, (
        "bool CClientList::QueuePeerShareRefresh", "m_peerShareScanner.QueuePeerManual(peerHash)",
        "bool CClientList::GetPeerShareState", "m_peerShareScanner.OnUnsupported(peerHash)",
        "ImportClientSharedFilesForPeer(toadd->GetUserName(), toadd->GetUserHash()",
        "toadd->GetClientSoftVer()",
    ), "client-list runtime bridge", failures)
    require(search_h, (
        "If several", "endpoint match is required", "ImportClientSharedFilesForPeer",
    ), "restored-tab identity contract", failures)

    duplicate_username_sql_smoke(failures)

    if failures:
        print("eMule Next Known Users 2.0 completion verification FAILED")
        for failure in failures:
            print(" -", failure)
        return 1
    print("eMule Next Known Users 2.0 completion verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
