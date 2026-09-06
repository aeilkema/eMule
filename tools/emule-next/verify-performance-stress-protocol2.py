#!/usr/bin/env python3
'''Final-state gate for Performance / Stress / Protocol Regression 2.0.'''
from __future__ import annotations

import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
HERE = pathlib.Path(__file__).resolve().parent


def read(name: str) -> str:
    path = SRC / name
    if not path.exists():
        raise SystemExit(f"Perf2 verification: missing {name}")
    return path.read_bytes().decode("latin-1", errors="ignore")


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise SystemExit(f"Perf2 verification: {label} missing {marker}")


def activation_order() -> list[str]:
    path = HERE / "activate-features.py"
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Tuple, ast.List)):
            values = [item.value for item in node.elts if isinstance(item, ast.Constant) and isinstance(item.value, str) and item.value.endswith(".py")]
            if "activate-performance-stress-regression2.py" in values:
                return values
    return []


def main() -> int:
    stress_h = read("EmuleNextStressDiagnostics.h")
    stress_cpp = read("EmuleNextStressDiagnostics.cpp")
    diag_h = read("EmuleNextDiagnosticsWnd.h")
    diag_cpp = read("EmuleNextDiagnosticsWnd.cpp")
    project = read("emule.vcxproj")
    download_h = read("DownloadQueue.h")
    upload_h = read("UploadQueue.h")
    part_h = read("PartFile.h")
    known_h = read("KnownFile.h")
    search_cpp = read("SearchResultsWnd.cpp")
    client_index = read("ClientIndex.cpp")
    download_index = read("DownloadIndex.cpp")
    scheduler = read("EmuleNextSmartScheduler.cpp")

    for marker in (
        "RunIndexStress",
        "clientEntries > 20000",
        "downloadEntries > 10000",
        "CClientIndex clientIndex",
        "CDownloadIndex downloadIndex",
        "RegisterClient(FakeClient(i)",
        "FindByUserHash",
        "FindByTcpEndpoint",
        "FindByUdpEndpoint",
        "FindByKadEndpoint",
        "UpdateClient",
        "UnregisterClient",
        "RegisterFile(FakeFile(i)",
        "FindByHash",
        "FindByKadSearchId",
        "UpdateKadSearchId",
        "UnregisterFile",
        "ValidateSize",
    ):
        require(stress_cpp, marker, "deterministic index stress")
    require(stress_h, "Pure in-memory deterministic stress test", "stress safety contract")
    for forbidden in ("sqlite3_", "AfxBeginThread", "SendPacket", "SendUDPPacket", "theApp."):
        if forbidden in stress_cpp:
            raise SystemExit(f"Perf2 verification: stress test leaked side-effect token {forbidden}")

    require(diag_h, "OnStressClicked", "Diagnostics stress action")
    for marker in (
        '#include "EmuleNextStressDiagnostics.h"',
        "ENMA_STRESS",
        "RunIndexStress(10000, 5000",
        "AfxBeginThread(MaintenanceWorker",
        "Run index stress test",
    ):
        require(diag_cpp, marker, "Diagnostics stress wiring")
    require(project, '<ClCompile Include="EmuleNextStressDiagnostics.cpp" />', "stress project source")
    require(project, '<ClInclude Include="EmuleNextStressDiagnostics.h" />', "stress project header")

    # Static protocol-regression contracts. These are deliberately not called
    # runtime proof: real eD2K/Kad/upload/download validation remains manual.
    for marker in ("AddFileLinkToDownload", "SendLocalSrcRequest", "KademliaSearchFile", "DoKademliaFileRequest"):
        require(download_h, marker, "legacy download/source-discovery contract")
    for marker in ("AddClientToQueue", "RemoveFromUploadQueue", "GetUploadQueueLength", "GetDatarate"):
        require(upload_h, marker, "legacy upload contract")
    for marker in ("PauseFile", "ResumeFile", "LoadPartFile", "PartFileHashFinished", "HashSinglePart", "ProcessA4AFClients"):
        target = part_h if marker != "ProcessA4AFClients" else read("ClientList.h")
        require(target, marker, "pause/restart/hash/A4AF contract")
    for marker in ("CreateFromFile", "CreateHash"):
        require(known_h, marker, "legacy file hashing contract")
    for marker in ("SearchTypeEd2kServer", "SearchTypeEd2kGlobal", "SearchTypeKademlia", "StartNewSearch(pParams)"):
        require(search_cpp, marker, "legacy search routing")
    require(scheduler, "ENSM_ANALYSIS_ONLY", "analysis-only safe default contract")

    # Index implementation itself must retain both fast lookup and explicit
    # size validation; the stress test depends on these exact public semantics.
    for source, markers, label in (
        (client_index, ("m_registrations", "FindByUserHash", "FindByTcpEndpoint", "ValidateSize"), "ClientIndex"),
        (download_index, ("m_registrations", "FindByHash", "FindByKadSearchId", "ValidateSize"), "DownloadIndex"),
    ):
        for marker in markers:
            require(source, marker, label)

    order = activation_order()
    if not order:
        raise SystemExit("Perf2 verification: activation order unavailable")
    required = (
        "activate-database-recovery-diagnostics2-hardening.py",
        "verify-winsqlite-maintenance-compat.py",
        "activate-performance-stress-regression2.py",
        "verify-performance-stress-protocol2.py",
        "audit-activators.py",
    )
    for name in required:
        if name not in order:
            raise SystemExit(f"Perf2 verification: activation step missing {name}")
    indexes = [order.index(name) for name in required]
    if indexes != sorted(indexes):
        raise SystemExit("Perf2 verification: unsafe activation/gate ordering")

    print("eMule Next Performance / Stress / Protocol Regression 2.0 verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
