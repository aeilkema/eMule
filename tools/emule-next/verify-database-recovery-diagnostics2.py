#!/usr/bin/env python3
'''Final-state completion gate for Database / Recovery / Diagnostics 2.0.'''
from __future__ import annotations

import ast
import pathlib
import sqlite3
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
HERE = pathlib.Path(__file__).resolve().parent


def read(name: str) -> str:
    path = SRC / name
    if not path.exists():
        raise SystemExit(f"DB2 verification: missing {name}")
    return path.read_bytes().decode("latin-1", errors="ignore")


def require(source: str, marker: str, label: str) -> None:
    if marker not in source:
        raise SystemExit(f"DB2 verification: missing {label}: {marker}")


def activation_order() -> list[str]:
    path = HERE / "activate-features.py"
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Tuple, ast.List)):
            values = [item.value for item in node.elts if isinstance(item, ast.Constant) and isinstance(item.value, str) and item.value.endswith(".py")]
            if "activate-database-recovery-diagnostics2.py" in values:
                return values
    return []


def schema_smoke() -> None:
    with tempfile.TemporaryDirectory(prefix="emule-next-db2-") as temp:
        source = pathlib.Path(temp) / "source.sqlite3"
        backup = pathlib.Path(temp) / "backup.sqlite3"
        db = sqlite3.connect(source)
        db.executescript("""
            CREATE TABLE schema_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            INSERT INTO schema_meta VALUES('schema_version','3');
            CREATE TABLE maintenance_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE favorites(file_id INTEGER PRIMARY KEY);
            CREATE TABLE peer_metadata(user_hash BLOB PRIMARY KEY,alias TEXT,favorite INTEGER,updated_at INTEGER);
            CREATE TABLE library_entries(file_id INTEGER PRIMARY KEY,completed_at INTEGER);
            CREATE TABLE scheduler_decisions(id INTEGER PRIMARY KEY,ts INTEGER);
            CREATE TABLE scheduler_outcomes(id INTEGER PRIMARY KEY,ts INTEGER);
            CREATE TABLE transfer_sessions(id INTEGER PRIMARY KEY,finished_at INTEGER,successful INTEGER);
        """)
        db.execute("INSERT INTO favorites VALUES(1)")
        db.execute("INSERT INTO peer_metadata VALUES(?,?,?,?)", (bytes(range(16)), "keep", 1, 1))
        db.execute("INSERT INTO library_entries VALUES(1,1)")
        db.execute("INSERT INTO scheduler_decisions VALUES(1,1)")
        db.execute("INSERT INTO scheduler_outcomes VALUES(1,1)")
        db.execute("INSERT INTO transfer_sessions VALUES(1,1,0)")
        db.commit()
        copy = sqlite3.connect(backup)
        db.backup(copy)
        copy.commit()
        if copy.execute("PRAGMA integrity_check").fetchone()[0].lower() != "ok":
            raise SystemExit("DB2 smoke: backup integrity failed")
        copy.close()
        db.execute("DELETE FROM scheduler_decisions WHERE ts<10")
        db.execute("DELETE FROM scheduler_outcomes WHERE ts<10")
        db.execute("DELETE FROM transfer_sessions WHERE finished_at<10 AND successful=0")
        db.commit()
        for table in ("favorites", "peer_metadata", "library_entries"):
            if db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] != 1:
                raise SystemExit(f"DB2 smoke: pruning touched protected table {table}")
        db.close()


def main() -> int:
    for script in ("activate-database-recovery-diagnostics2.py", "verify-database-recovery-diagnostics2.py"):
        path = HERE / script
        try:
            ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except SyntaxError as exc:
            raise SystemExit(f"DB2 verification: {script} syntax error line {exc.lineno}: {exc.msg}")

    order = activation_order()
    if not order:
        raise SystemExit("DB2 verification: activation order not found")
    for required in ("activate-scheduler-schema-v2.py", "activate-ui-navigation-modernization2-dashboard.py", "activate-database-recovery-diagnostics2.py", "verify-database-recovery-diagnostics2.py", "audit-activators.py"):
        if required not in order:
            raise SystemExit(f"DB2 verification: activation step missing: {required}")
    indexes = [order.index(name) for name in ("activate-scheduler-schema-v2.py", "activate-ui-navigation-modernization2-dashboard.py", "activate-database-recovery-diagnostics2.py", "verify-database-recovery-diagnostics2.py", "audit-activators.py")]
    if indexes != sorted(indexes):
        raise SystemExit("DB2 verification: unsafe activation/gate ordering")
    if order.count("activate-database-recovery-diagnostics2.py") != 1 or order.count("verify-database-recovery-diagnostics2.py") != 1:
        raise SystemExit("DB2 verification: duplicate database goal activation/gate")

    db_h, db_cpp = read("EmuleNextDatabase.h"), read("EmuleNextDatabase.cpp")
    maint_h, maint_cpp = read("EmuleNextDatabaseMaintenance.h"), read("EmuleNextDatabaseMaintenance.cpp")
    rt_h, rt_cpp = read("EmuleNextRuntime.h"), read("EmuleNextRuntime.cpp")
    diag_h, diag_cpp = read("EmuleNextDiagnosticsWnd.h"), read("EmuleNextDiagnosticsWnd.cpp")
    host_h, host_cpp = read("SearchResultsWnd.h"), read("SearchResultsWnd.cpp")
    project = read("emule.vcxproj")

    require(db_cpp, "VALUES('schema_version','3')", "schema v3")
    require(db_cpp, "CREATE TABLE IF NOT EXISTS maintenance_meta", "maintenance metadata schema")
    for marker in ("m_peakQueue", "m_processedEvents", "m_droppedEvents", "m_writeErrors", "GetQueueDiagnostics"):
        require(db_cpp, marker, "writer-queue diagnostics")
    require(db_h, "EmuleNextDatabaseQueueDiagnostics", "queue diagnostics contract")

    for marker, label in (
        ('#include "EmuleNextWinSqliteCompat.h"', "WinSQLite compatibility include"),
        ("sqlite3_backup_init", "SQLite online backup API"),
        ("PRAGMA quick_check", "quick integrity check"),
        ("PRAGMA integrity_check", "full integrity check"),
        ("archive-pre-restore", "pre-restore archival"),
        ("MOVEFILE_WRITE_THROUGH", "durable archive move"),
        ("emule-next-backup-*.sqlite3", "backup rotation set"),
        ("RotateBackups(folder, keep)", "bounded backup retention"),
        ("DELETE FROM scheduler_decisions", "scheduler telemetry pruning"),
        ("DELETE FROM scheduler_outcomes", "scheduler outcome pruning"),
        ("successful=0", "failed transfer pruning only"),
        ("SQLITE_CHECKPOINT_TRUNCATE", "WAL checkpoint"),
    ):
        require(maint_cpp, marker, label)
    for forbidden in ("DELETE FROM favorites", "DELETE FROM peer_metadata", "DELETE FROM library_entries"):
        if forbidden in maint_cpp:
            raise SystemExit(f"DB2 verification: protected data pruning found: {forbidden}")

    for marker, label in (
        ("ReadSchemaVersion(m_databasePath) < 3", "migration detection"),
        ("_T(\"pre-migration\")", "pre-migration backup"),
        ("CheckDatabaseFile(m_databasePath, false", "startup quick check"),
        ("m_recoveryRequired = true", "recovery-required state"),
        ("StartMaintenanceThread();", "periodic maintenance worker"),
        ("std::chrono::hours(1)", "hourly maintenance wake"),
        ("24ui64 * 60ui64 * 60ui64", "24-hour automatic backup age"),
        ("RestoreDatabaseBackup", "runtime restore API"),
        ("Stop();", "database stop before restore"),
        ("RestoreBackup(backupPath, path", "offline restore routing"),
        ("if (!Start())", "database restart after restore"),
        ("90ui64 * 24ui64 * 60ui64 * 60ui64", "90-day telemetry retention"),
    ):
        require(rt_cpp, marker, label)
    for marker in ("std::thread m_maintenanceThread", "std::condition_variable m_maintenanceCondition", "std::atomic<bool> m_recoveryRequired"):
        require(rt_h, marker, "maintenance runtime compile contract")

    start_body = rt_cpp[rt_cpp.find("bool CEmuleNextRuntime::Start()"):rt_cpp.find("void CEmuleNextRuntime::Stop()")]
    if start_body.find("CheckDatabaseFile") < 0 or start_body.find("m_database.Start") < 0 or start_body.find("CheckDatabaseFile") > start_body.find("m_database.Start"):
        raise SystemExit("DB2 verification: startup quick_check runs after database start")
    if start_body.find("_T(\"pre-migration\")") < 0 or start_body.find("_T(\"pre-migration\")") > start_body.find("m_database.Start"):
        raise SystemExit("DB2 verification: pre-migration backup runs after migration start")
    restore = rt_cpp[rt_cpp.find("bool CEmuleNextRuntime::RestoreDatabaseBackup"):rt_cpp.find("bool CEmuleNextRuntime::PruneDatabaseTelemetry")]
    for a, b, label in (("CheckDatabaseFile", "Stop();", "validate before stop"), ("Stop();", "RestoreBackup", "stop before restore"), ("RestoreBackup", "if (!Start())", "restore before restart")):
        if restore.find(a) < 0 or restore.find(b) < 0 or restore.find(a) > restore.find(b):
            raise SystemExit(f"DB2 verification: unsafe restore order: {label}")

    for marker in ("EMULENEXT_DIAGNOSTICS_VIEW_ID", "MaintenanceWorker", "AfxBeginThread(MaintenanceWorker", "Restore backup...", "Full integrity check", "Prune old telemetry", "Checkpoint WAL", "Open backup folder"):
        require(diag_cpp if marker != "EMULENEXT_DIAGNOSTICS_VIEW_ID" else diag_h, marker, "diagnostics UI")
    for marker in ("ON_WM_CREATE()", "ON_WM_SIZE()", "ON_MESSAGE(WM_EN_DIAG_RESULT, OnMaintenanceResult)"):
        require(diag_cpp, marker, "Diagnostics MFC message-map contract")
    if "sqlite3_" in diag_cpp or "winsqlite3" in diag_cpp.lower():
        raise SystemExit("DB2 verification: SQLite leaked into Diagnostics GUI")
    require(host_h, "CEmuleNextDiagnosticsWnd m_diagnosticsWnd", "Diagnostics host member")
    require(host_cpp, "searchID == EMULENEXT_DIAGNOSTICS_VIEW_ID", "persistent Diagnostics navigation")
    require(host_cpp, 'strSpecialTitle = _T("Diagnostics")', "Diagnostics tab label")
    require(host_cpp, "m_diagnosticsWnd.Refresh(false)", "Diagnostics refresh routing")
    require(project, '<ClCompile Include="EmuleNextDatabaseMaintenance.cpp" />', "maintenance project source")
    require(project, '<ClCompile Include="EmuleNextDiagnosticsWnd.cpp" />', "Diagnostics project source")
    require(project, '<ClInclude Include="EmuleNextDatabaseMaintenance.h" />', "maintenance project header")
    require(project, '<ClInclude Include="EmuleNextDiagnosticsWnd.h" />', "Diagnostics project header")

    schema_smoke()
    print("eMule Next Database / Recovery / Diagnostics 2.0 verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
