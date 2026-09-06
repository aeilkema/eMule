#!/usr/bin/env python3
'''Materialize Database / Recovery / Diagnostics 2.0 on the final activated tree.'''
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
DB_H = SRC / "EmuleNextDatabase.h"
DB_CPP = SRC / "EmuleNextDatabase.cpp"
RT_H = SRC / "EmuleNextRuntime.h"
RT_CPP = SRC / "EmuleNextRuntime.cpp"
HOST_H = SRC / "SearchResultsWnd.h"
HOST_CPP = SRC / "SearchResultsWnd.cpp"
PROJECT = SRC / "emule.vcxproj"


def read(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def write(path: pathlib.Path, text: str, enc: str) -> None:
    path.write_bytes(text.encode(enc))


def insert_after(text: str, anchor: str, addition: str, marker: str) -> str:
    if marker in text:
        return text
    if anchor not in text:
        raise SystemExit(f"DB2: insertion anchor missing for {marker}")
    return text.replace(anchor, anchor + addition, 1)


def replace_once(text: str, old: str, new: str, marker: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise SystemExit(f"DB2: replacement anchor missing for {marker}")
    return text.replace(old, new, 1)


def patch_database() -> None:
    text, enc = read(DB_H)
    if "struct EmuleNextDatabaseQueueDiagnostics" not in text:
        pos = text.find("class CEmuleNextDatabase")
        if pos < 0:
            raise SystemExit("DB2: database class missing")
        text = text[:pos] + '''struct EmuleNextDatabaseQueueDiagnostics\n{\n    uint64 queued;\n    uint64 peakQueued;\n    uint64 processed;\n    uint64 dropped;\n    uint64 errors;\n    CStringW lastError;\n    EmuleNextDatabaseQueueDiagnostics();\n};\n\n''' + text[pos:]
    text = insert_after(text,
        "    bool BackupTo(const CStringW& destinationPath) const;\n",
        "    EmuleNextDatabaseQueueDiagnostics GetQueueDiagnostics() const;\n",
        "GetQueueDiagnostics() const")
    write(DB_H, text, enc)

    text, enc = read(DB_CPP)
    if "VALUES('schema_version','3')" not in text:
        if "VALUES('schema_version','2')" not in text:
            raise SystemExit("DB2: scheduler schema v2 must be materialized first")
        text = text.replace("VALUES('schema_version','2')", "VALUES('schema_version','3')", 1)
    if "CREATE TABLE IF NOT EXISTS maintenance_meta" not in text:
        anchor = '            "COMMIT;";\n'
        addition = '            "CREATE TABLE IF NOT EXISTS maintenance_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);"\n'
        if anchor not in text:
            raise SystemExit("DB2: schema commit anchor missing")
        text = text.replace(anchor, addition + anchor, 1)

    text = insert_after(text,
        "EmuleNextFavoriteRecord::EmuleNextFavoriteRecord()\n    : fileSize(0), autoRestore(false)\n{\n}\n",
        '''\nEmuleNextDatabaseQueueDiagnostics::EmuleNextDatabaseQueueDiagnostics()\n    : queued(0), peakQueued(0), processed(0), dropped(0), errors(0)\n{\n}\n''',
        "EmuleNextDatabaseQueueDiagnostics::EmuleNextDatabaseQueueDiagnostics")

    text = replace_once(text,
        "        : m_stop(false), m_running(false), m_initDone(false), m_initSucceeded(false)\n",
        "        : m_stop(false), m_running(false), m_initDone(false), m_initSucceeded(false), m_peakQueue(0), m_processedEvents(0), m_droppedEvents(0), m_writeErrors(0)\n",
        "queue diagnostic constructor")

    old_queue = '''            if (m_queue.size() >= 50000) {\n                m_lastError = L"eMule Next database queue reached safety limit; oldest event discarded";\n                m_queue.pop_front();\n            }\n            m_queue.push_back(std::move(event));\n'''
    new_queue = '''            if (m_queue.size() >= 50000) {\n                m_lastError = L"eMule Next database queue reached safety limit; oldest event discarded";\n                m_queue.pop_front();\n                ++m_droppedEvents;\n            }\n            m_queue.push_back(std::move(event));\n            const uint64 queued = static_cast<uint64>(m_queue.size());\n            uint64 peak = m_peakQueue.load();\n            while (queued > peak && !m_peakQueue.compare_exchange_weak(peak, queued)) {}\n'''
    text = replace_once(text, old_queue, new_queue, "queue accounting")

    old_commit = '''                if (!ExecSql(db, "COMMIT;"))\n                    ExecSql(db, "ROLLBACK;");\n'''
    new_commit = '''                if (!ExecSql(db, "COMMIT;")) {\n                    ++m_writeErrors;\n                    ExecSql(db, "ROLLBACK;");\n                }\n                else\n                    m_processedEvents.fetch_add(static_cast<uint64>(batch.size()));\n'''
    text = replace_once(text, old_commit, new_commit, "writer outcome accounting")

    if "EmuleNextDatabaseQueueDiagnostics GetQueueDiagnostics() const" not in text:
        marker = "private:\n    void SetError"
        pos = text.find(marker)
        if pos < 0:
            raise SystemExit("DB2: Impl private boundary missing")
        method = '''    EmuleNextDatabaseQueueDiagnostics GetQueueDiagnostics() const\n    {\n        EmuleNextDatabaseQueueDiagnostics result;\n        {\n            std::lock_guard<std::mutex> lock(m_mutex);\n            result.queued = static_cast<uint64>(m_queue.size());\n            result.lastError = m_lastError;\n        }\n        result.peakQueued = m_peakQueue.load();\n        result.processed = m_processedEvents.load();\n        result.dropped = m_droppedEvents.load();\n        result.errors = m_writeErrors.load();\n        return result;\n    }\n\n'''
        text = text[:pos] + method + text[pos:]

    text = insert_after(text,
        "    CStringW m_lastError;\n",
        "    std::atomic<uint64> m_peakQueue;\n    std::atomic<uint64> m_processedEvents;\n    std::atomic<uint64> m_droppedEvents;\n    std::atomic<uint64> m_writeErrors;\n",
        "m_peakQueue")
    text = insert_after(text,
        "bool CEmuleNextDatabase::BackupTo(const CStringW& destinationPath) const { return m_impl->BackupTo(destinationPath); }\n",
        "EmuleNextDatabaseQueueDiagnostics CEmuleNextDatabase::GetQueueDiagnostics() const { return m_impl->GetQueueDiagnostics(); }\n",
        "CEmuleNextDatabase::GetQueueDiagnostics")
    write(DB_CPP, text, enc)


def patch_runtime() -> None:
    text, enc = read(RT_H)
    if '#include "EmuleNextDatabaseMaintenance.h"' not in text:
        text = text.replace('#include "EmuleNextDatabase.h"\n', '#include "EmuleNextDatabase.h"\n#include "EmuleNextDatabaseMaintenance.h"\n', 1)
    if "struct EmuleNextDatabaseDiagnostics" not in text:
        pos = text.find("class CEmuleNextRuntime")
        if pos < 0:
            raise SystemExit("DB2: runtime class missing")
        struct_text = '''struct EmuleNextDatabaseDiagnostics\n{\n    bool running;\n    bool recoveryRequired;\n    int schemaVersion;\n    uint64 databaseBytes;\n    uint64 walBytes;\n    uint32 backupCount;\n    uint64 lastBackupAt;\n    uint64 lastIntegrityAt;\n    CStringW lastIntegrityResult;\n    uint64 peerCount;\n    uint64 fileCount;\n    uint64 libraryCount;\n    uint64 transferCount;\n    uint64 schedulerDecisionCount;\n    uint64 schedulerOutcomeCount;\n    CStringW status;\n    CStringW databasePath;\n    CStringW backupFolder;\n    EmuleNextDatabaseQueueDiagnostics queue;\n    EmuleNextDatabaseDiagnostics();\n};\n\n'''
        text = text[:pos] + struct_text + text[pos:]
    text = insert_after(text,
        "    const CEmuleNextDatabase& Database() const;\n",
        '''\n    bool LoadDatabaseDiagnostics(EmuleNextDatabaseDiagnostics& diagnostics) const;\n    bool RunDatabaseIntegrityCheck(bool full, CStringW& result);\n    bool CreateDatabaseBackup(LPCTSTR reason, CStringW& backupPath, CStringW& result);\n    bool RestoreDatabaseBackup(const CStringW& backupPath, CStringW& result);\n    bool PruneDatabaseTelemetry(uint64& removedRows, CStringW& result);\n    bool CheckpointDatabase(CStringW& result);\n    CStringW GetDatabaseBackupFolder() const;\n''',
        "LoadDatabaseDiagnostics")
    text = insert_after(text,
        "    bool SavePeerMetadata(const EmuleNextHash16& hash, const CStringW& alias, bool favorite);\n",
        "    void StartMaintenanceThread();\n    void StopMaintenanceThread();\n    void MaintenanceMain();\n    void MaybeAutomaticDatabaseBackup();\n",
        "MaintenanceMain()")
    if "#include <thread>" not in text:
        text = text.replace("#include <mutex>\n", "#include <mutex>\n#include <thread>\n#include <condition_variable>\n#include <atomic>\n", 1)
    text = insert_after(text,
        "    mutable std::map<std::array<unsigned char, 16>, uint64> m_autoShareRequests;\n",
        '''\n    std::thread m_maintenanceThread;\n    mutable std::mutex m_maintenanceMutex;\n    std::condition_variable m_maintenanceCondition;\n    bool m_maintenanceStop;\n    std::atomic<bool> m_recoveryRequired;\n    CStringW m_maintenanceStatus;\n    CStringW m_databasePath;\n''',
        "m_maintenanceThread")
    write(RT_H, text, enc)

    text, enc = read(RT_CPP)
    if "#include <chrono>" not in text:
        text = text.replace("#include <winsqlite3.h>\n", "#include <winsqlite3.h>\n#include <chrono>\n", 1)
    text = insert_after(text,
        "CEmuleNextRuntime theEmuleNext;\n",
        '''\nEmuleNextDatabaseDiagnostics::EmuleNextDatabaseDiagnostics()\n    : running(false), recoveryRequired(false), schemaVersion(0), databaseBytes(0), walBytes(0),\n      backupCount(0), lastBackupAt(0), lastIntegrityAt(0), peerCount(0), fileCount(0),\n      libraryCount(0), transferCount(0), schedulerDecisionCount(0), schedulerOutcomeCount(0)\n{\n}\n''',
        "EmuleNextDatabaseDiagnostics::EmuleNextDatabaseDiagnostics")
    text = replace_once(text,
        "CEmuleNextRuntime::CEmuleNextRuntime()\n{\n}\n",
        "CEmuleNextRuntime::CEmuleNextRuntime()\n    : m_maintenanceStop(false)\n    , m_recoveryRequired(false)\n{\n}\n",
        "runtime maintenance constructor")

    start = re.compile(r"bool CEmuleNextRuntime::Start\(\)\n\{.*?\n\}\n\nvoid CEmuleNextRuntime::Stop\(\)", re.S)
    if "pre-migration" not in text[text.find("bool CEmuleNextRuntime::Start()"):text.find("void CEmuleNextRuntime::Stop()")]:
        replacement = '''bool CEmuleNextRuntime::Start()\n{\n    if (m_database.IsRunning())\n        return true;\n\n    m_databasePath = CStringW(thePrefs.GetMuleDirectory(EMULE_CONFIGDIR)) + L"emule-next.sqlite3";\n    m_recoveryRequired = false;\n    { std::lock_guard<std::mutex> lock(m_maintenanceMutex); m_maintenanceStatus = L"Starting"; }\n\n    if (CEmuleNextDatabaseMaintenance::FileExists(m_databasePath)) {\n        CStringW check;\n        if (!CEmuleNextDatabaseMaintenance::CheckDatabaseFile(m_databasePath, false, check)) {\n            m_recoveryRequired = true;\n            { std::lock_guard<std::mutex> lock(m_maintenanceMutex); m_maintenanceStatus = L"Recovery required: " + check; }\n            AddLogLine(true, _T("eMule Next intelligence database disabled; recovery required: %s"), static_cast<LPCTSTR>(CString(check)));\n            return false;\n        }\n        if (CEmuleNextDatabaseMaintenance::ReadSchemaVersion(m_databasePath) < 3) {\n            CStringW backupPath, backupResult;\n            if (!CEmuleNextDatabaseMaintenance::CreateBackup(m_databasePath, _T("pre-migration"), backupPath, backupResult, 5)) {\n                m_recoveryRequired = true;\n                { std::lock_guard<std::mutex> lock(m_maintenanceMutex); m_maintenanceStatus = L"Migration blocked: " + backupResult; }\n                return false;\n            }\n        }\n    }\n\n    const bool started = m_database.Start(m_databasePath);\n    if (started) {\n        InitializePeerMetadata();\n        { std::lock_guard<std::mutex> lock(m_maintenanceMutex); m_maintenanceStatus = L"Healthy"; }\n        StartMaintenanceThread();\n        AddLogLine(false, _T("eMule Next intelligence database: %s"), static_cast<LPCTSTR>(CString(m_databasePath)));\n    }\n    else {\n        { std::lock_guard<std::mutex> lock(m_maintenanceMutex); m_maintenanceStatus = L"Disabled: " + m_database.GetLastError(); }\n        AddLogLine(true, _T("eMule Next intelligence database disabled: %s"), static_cast<LPCTSTR>(CString(m_database.GetLastError())));\n    }\n    return started;\n}\n\nvoid CEmuleNextRuntime::Stop()'''
        text, count = start.subn(lambda _: replacement, text, count=1)
        if count != 1:
            raise SystemExit("DB2: runtime Start boundary missing")

    stop_start = text.find("void CEmuleNextRuntime::Stop()")
    stop_end = text.find("bool CEmuleNextRuntime::IsRunning", stop_start)
    if stop_start < 0 or stop_end < 0:
        raise SystemExit("DB2: runtime Stop boundary missing")
    if "StopMaintenanceThread();" not in text[stop_start:stop_end]:
        text = text.replace("void CEmuleNextRuntime::Stop()\n{\n", "void CEmuleNextRuntime::Stop()\n{\n    StopMaintenanceThread();\n", 1)

    if "bool CEmuleNextRuntime::LoadDatabaseDiagnostics" not in text:
        pos = text.find("bool CEmuleNextRuntime::InitializePeerMetadata()")
        if pos < 0:
            raise SystemExit("DB2: runtime method insertion point missing")
        methods = '''void CEmuleNextRuntime::StartMaintenanceThread()\n{\n    StopMaintenanceThread();\n    { std::lock_guard<std::mutex> lock(m_maintenanceMutex); m_maintenanceStop = false; }\n    try { m_maintenanceThread = std::thread(&CEmuleNextRuntime::MaintenanceMain, this); }\n    catch (...) { std::lock_guard<std::mutex> lock(m_maintenanceMutex); m_maintenanceStatus = L"Healthy; automatic backup worker unavailable"; }\n}\n\nvoid CEmuleNextRuntime::StopMaintenanceThread()\n{\n    { std::lock_guard<std::mutex> lock(m_maintenanceMutex); m_maintenanceStop = true; }\n    m_maintenanceCondition.notify_all();\n    if (m_maintenanceThread.joinable() && m_maintenanceThread.get_id() != std::this_thread::get_id()) m_maintenanceThread.join();\n}\n\nvoid CEmuleNextRuntime::MaintenanceMain()\n{\n    std::unique_lock<std::mutex> lock(m_maintenanceMutex);\n    while (!m_maintenanceStop) {\n        lock.unlock(); MaybeAutomaticDatabaseBackup(); lock.lock();\n        m_maintenanceCondition.wait_for(lock, std::chrono::hours(1), [this]() { return m_maintenanceStop; });\n    }\n}\n\nvoid CEmuleNextRuntime::MaybeAutomaticDatabaseBackup()\n{\n    if (!m_database.IsRunning() || m_databasePath.IsEmpty()) return;\n    if (!CEmuleNextDatabaseMaintenance::ShouldCreateAutomaticBackup(m_databasePath, 24ui64 * 60ui64 * 60ui64)) return;\n    CStringW backupPath, result;\n    CreateDatabaseBackup(_T("auto"), backupPath, result);\n}\n\nCStringW CEmuleNextRuntime::GetDatabaseBackupFolder() const\n{\n    const CStringW path = m_databasePath.IsEmpty() ? CStringW(thePrefs.GetMuleDirectory(EMULE_CONFIGDIR)) + L"emule-next.sqlite3" : m_databasePath;\n    return CEmuleNextDatabaseMaintenance::BackupFolderFor(path);\n}\n\nbool CEmuleNextRuntime::LoadDatabaseDiagnostics(EmuleNextDatabaseDiagnostics& diagnostics) const\n{\n    diagnostics = EmuleNextDatabaseDiagnostics();\n    diagnostics.running = m_database.IsRunning(); diagnostics.recoveryRequired = m_recoveryRequired.load();\n    const CStringW path = m_databasePath.IsEmpty() ? CStringW(thePrefs.GetMuleDirectory(EMULE_CONFIGDIR)) + L"emule-next.sqlite3" : m_databasePath;\n    EmuleNextDatabaseMaintenanceSnapshot snapshot;\n    const bool loaded = CEmuleNextDatabaseMaintenance::LoadSnapshot(path, snapshot);\n    diagnostics.schemaVersion = snapshot.schemaVersion; diagnostics.databaseBytes = snapshot.databaseBytes; diagnostics.walBytes = snapshot.walBytes;\n    diagnostics.backupCount = snapshot.backupCount; diagnostics.lastBackupAt = snapshot.lastBackupAt; diagnostics.lastIntegrityAt = snapshot.lastIntegrityAt; diagnostics.lastIntegrityResult = snapshot.lastIntegrityResult;\n    diagnostics.peerCount = snapshot.peerCount; diagnostics.fileCount = snapshot.fileCount; diagnostics.libraryCount = snapshot.libraryCount; diagnostics.transferCount = snapshot.transferCount;\n    diagnostics.schedulerDecisionCount = snapshot.schedulerDecisionCount; diagnostics.schedulerOutcomeCount = snapshot.schedulerOutcomeCount; diagnostics.databasePath = path; diagnostics.backupFolder = snapshot.backupFolder; diagnostics.queue = m_database.GetQueueDiagnostics();\n    { std::lock_guard<std::mutex> lock(m_maintenanceMutex); diagnostics.status = m_maintenanceStatus; }\n    if (diagnostics.status.IsEmpty()) diagnostics.status = diagnostics.running ? L"Healthy" : (diagnostics.recoveryRequired ? L"Recovery required" : L"Disabled");\n    return loaded || diagnostics.running || CEmuleNextDatabaseMaintenance::FileExists(path);\n}\n\nbool CEmuleNextRuntime::RunDatabaseIntegrityCheck(bool full, CStringW& result)\n{\n    const CStringW path = m_databasePath.IsEmpty() ? CStringW(thePrefs.GetMuleDirectory(EMULE_CONFIGDIR)) + L"emule-next.sqlite3" : m_databasePath;\n    const bool ok = CEmuleNextDatabaseMaintenance::CheckDatabaseFile(path, full, result);\n    CEmuleNextDatabaseMaintenance::RecordIntegrityResult(path, result, RuntimeNowSeconds());\n    { std::lock_guard<std::mutex> lock(m_maintenanceMutex); m_maintenanceStatus = ok ? L"Healthy" : L"Integrity warning: " + result; }\n    return ok;\n}\n\nbool CEmuleNextRuntime::CreateDatabaseBackup(LPCTSTR reason, CStringW& backupPath, CStringW& result)\n{\n    const CStringW path = m_databasePath.IsEmpty() ? CStringW(thePrefs.GetMuleDirectory(EMULE_CONFIGDIR)) + L"emule-next.sqlite3" : m_databasePath;\n    return CEmuleNextDatabaseMaintenance::CreateBackup(path, reason, backupPath, result, 5);\n}\n\nbool CEmuleNextRuntime::RestoreDatabaseBackup(const CStringW& backupPath, CStringW& result)\n{\n    const CStringW path = m_databasePath.IsEmpty() ? CStringW(thePrefs.GetMuleDirectory(EMULE_CONFIGDIR)) + L"emule-next.sqlite3" : m_databasePath;\n    CStringW validation;\n    if (!CEmuleNextDatabaseMaintenance::CheckDatabaseFile(backupPath, true, validation)) { result = L"Backup rejected by integrity_check: " + validation; return false; }\n    Stop();\n    CStringW archive;\n    if (!CEmuleNextDatabaseMaintenance::RestoreBackup(backupPath, path, archive, result)) return false;\n    m_recoveryRequired = false;\n    if (!Start()) { result += L" Database restored, but intelligence restart failed: " + m_database.GetLastError(); return false; }\n    if (!archive.IsEmpty()) result += L" Previous database archived as " + archive;\n    return true;\n}\n\nbool CEmuleNextRuntime::PruneDatabaseTelemetry(uint64& removedRows, CStringW& result)\n{\n    if (!m_database.IsRunning()) { result = L"Database is not running."; return false; }\n    const uint64 cutoff = RuntimeNowSeconds() - 90ui64 * 24ui64 * 60ui64 * 60ui64;\n    return CEmuleNextDatabaseMaintenance::PruneOldTelemetry(m_databasePath, cutoff, removedRows, result);\n}\n\nbool CEmuleNextRuntime::CheckpointDatabase(CStringW& result)\n{\n    if (!m_database.IsRunning()) { result = L"Database is not running."; return false; }\n    return CEmuleNextDatabaseMaintenance::CheckpointWal(m_databasePath, result);\n}\n\n'''
        text = text[:pos] + methods + text[pos:]
    write(RT_CPP, text, enc)


def patch_view_and_project() -> None:
    text, enc = read(PROJECT)
    compile_anchor = '    <ClCompile Include="EmuleNextDatabase.cpp" />\n'
    for name in ("EmuleNextDatabaseMaintenance.cpp", "EmuleNextDiagnosticsWnd.cpp"):
        if f'Include="{name}"' not in text:
            if compile_anchor not in text:
                raise SystemExit("DB2: project compile anchor missing")
            text = text.replace(compile_anchor, compile_anchor + f'    <ClCompile Include="{name}" />\n', 1)
    header_anchor = '    <ClInclude Include="EmuleNextDatabase.h" />\n'
    for name in ("EmuleNextDatabaseMaintenance.h", "EmuleNextDiagnosticsWnd.h"):
        if f'Include="{name}"' not in text:
            if header_anchor not in text:
                raise SystemExit("DB2: project header anchor missing")
            text = text.replace(header_anchor, header_anchor + f'    <ClInclude Include="{name}" />\n', 1)
    write(PROJECT, text, enc)

    text, enc = read(HOST_H)
    if '#include "EmuleNextDiagnosticsWnd.h"' not in text:
        text = text.replace('#include "EmuleNextSettingsWnd.h"\n', '#include "EmuleNextSettingsWnd.h"\n#include "EmuleNextDiagnosticsWnd.h"\n', 1)
    if "m_diagnosticsWnd;" not in text:
        text = text.replace("\tCEmuleNextSettingsWnd m_nextSettingsWnd;\n", "\tCEmuleNextSettingsWnd m_nextSettingsWnd;\n\tCEmuleNextDiagnosticsWnd m_diagnosticsWnd;\n", 1)
    write(HOST_H, text, enc)

    text, enc = read(HOST_CPP)
    if "searchID == EMULENEXT_DIAGNOSTICS_VIEW_ID" not in text:
        old = "\t\t|| searchID == EMULENEXT_SETTINGS_VIEW_ID;"
        if old not in text:
            raise SystemExit("DB2: persistent view predicate anchor missing")
        text = text.replace(old, "\t\t|| searchID == EMULENEXT_SETTINGS_VIEW_ID\n\t\t|| searchID == EMULENEXT_DIAGNOSTICS_VIEW_ID;", 1)
    if "m_diagnosticsWnd.Create(this)" not in text:
        marker = "\t// Restore the last eMule Next workspace; fall back to Known Users."
        pos = text.find(marker)
        if pos < 0:
            raise SystemExit("DB2: UI2 workspace restore marker missing")
        block = '''\tif (m_diagnosticsWnd.Create(this)) {\n\t\tm_diagnosticsWnd.ShowWindow(SW_HIDE);\n\t\tm_diagnosticsWnd.MoveWindow(&nextViewRect);\n\t\tAddAnchor(m_diagnosticsWnd, TOP_LEFT, BOTTOM_RIGHT);\n\t\tSSearchParams *diagnostics = new SSearchParams;\n\t\tdiagnostics->dwSearchID = EMULENEXT_DIAGNOSTICS_VIEW_ID;\n\t\tdiagnostics->strExpression = _T("Diagnostics");\n\t\tdiagnostics->strSpecialTitle = _T("Diagnostics");\n\t\tif (!CreateOrFindTab(diagnostics, false)) delete diagnostics;\n\t}\n\n'''
        text = text[:pos] + block + text[pos:]
    show_pos = text.find("void CSearchResultsWnd::ShowResults")
    if show_pos < 0:
        raise SystemExit("DB2: ShowResults missing")
    if "m_diagnosticsWnd.ShowWindow(SW_HIDE);" not in text[show_pos:]:
        text = text.replace("\tm_nextSettingsWnd.ShowWindow(SW_HIDE);\n", "\tm_nextSettingsWnd.ShowWindow(SW_HIDE);\n\tm_diagnosticsWnd.ShowWindow(SW_HIDE);\n", 1)
    if "pParams->dwSearchID == EMULENEXT_DIAGNOSTICS_VIEW_ID" not in text[show_pos:]:
        anchor = '''\t\telse if (pParams->dwSearchID == EMULENEXT_SETTINGS_VIEW_ID) {\n\t\t\tm_nextSettingsWnd.ShowWindow(SW_SHOW);\n\t\t\tm_nextSettingsWnd.Refresh();\n\t\t}\n'''
        addition = '''\t\telse if (pParams->dwSearchID == EMULENEXT_DIAGNOSTICS_VIEW_ID) {\n\t\t\tm_diagnosticsWnd.ShowWindow(SW_SHOW);\n\t\t\tm_diagnosticsWnd.Refresh(false);\n\t\t}\n'''
        if anchor not in text:
            raise SystemExit("DB2: Settings ShowResults branch missing")
        text = text.replace(anchor, anchor + addition, 1)
    write(HOST_CPP, text, enc)


def main() -> int:
    for path in (DB_H, DB_CPP, RT_H, RT_CPP, HOST_H, HOST_CPP, PROJECT):
        if not path.exists():
            raise SystemExit(f"DB2: missing {path}")
    for path in (SRC / "EmuleNextDatabaseMaintenance.h", SRC / "EmuleNextDatabaseMaintenance.cpp", SRC / "EmuleNextDiagnosticsWnd.h", SRC / "EmuleNextDiagnosticsWnd.cpp"):
        if not path.exists():
            raise SystemExit(f"DB2: maintenance source missing {path.name}")
    patch_database()
    patch_runtime()
    patch_view_and_project()
    print("eMule Next Database / Recovery / Diagnostics 2.0 materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
