#!/usr/bin/env python3
"""Record completed eMule upload slots in eMule Next transfer history."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "UploadClient.cpp"


def load() -> tuple[str, str]:
    raw = PATH.read_bytes()
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    newline = "\r\n" if crlf >= lf and crlf else "\n"
    return raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n"), newline


def save(text: str, newline: str) -> None:
    if newline != "\n":
        text = text.replace("\n", newline)
    PATH.write_bytes(text.encode("latin-1"))


def main() -> int:
    text, newline = load()

    include_anchor = '#include "UploadDiskIOThread.h"\n'
    if '#include "EmuleNextRuntime.h"' not in text:
        if include_anchor not in text:
            raise RuntimeError("UploadClient include anchor not found")
        text = text.replace(include_anchor,
            include_anchor + '#include "EmuleNextRuntime.h"\n#include <time.h>\n', 1)

    old = '''void CUpDownClient::SetUploadState(EUploadState eNewState)\n{\n\tif (eNewState != m_eUploadState) {\n\t\tif (m_eUploadState == US_UPLOADING) {\n\t\t\t// Reset upload data rate computation\n\t\t\tm_nUpDatarate = 0;\n\t\t\tm_nSumForAvgUpDataRate = 0;\n\t\t\tm_AverageUDR_hist.RemoveAll();\n\t\t}\n'''
    new = '''void CUpDownClient::SetUploadState(EUploadState eNewState)\n{\n\tif (eNewState != m_eUploadState) {\n\t\tif (m_eUploadState == US_UPLOADING) {\n\t\t\t// Persist the slot before legacy state cleanup/reset. UploadQueue calls\n\t\t\t// ResetSessionUp when a new slot starts, so this is the authoritative\n\t\t\t// lifecycle boundary for the just-finished upload session.\n\t\t\tconst uint64 nextBytes = static_cast<uint64>(GetQueueSessionPayloadUp());\n\t\t\tconst uint32 nextElapsedMs = GetUpStartTimeDelay();\n\t\t\tif (nextBytes > 0 && HasValidHash()) {\n\t\t\t\tCKnownFile *nextFile = theApp.sharedfiles->GetFileByID(GetUploadFileID());\n\t\t\t\tif (nextFile == NULL)\n\t\t\t\t\tnextFile = theApp.knownfiles->FindKnownFileByID(GetUploadFileID());\n\t\t\t\tif (nextFile != NULL) {\n\t\t\t\t\tconst uint64 nextNow = static_cast<uint64>(time(NULL));\n\t\t\t\t\tconst uint64 nextDuration = nextElapsedMs > 0 ? max<uint64>(1, nextElapsedMs / 1000) : 1;\n\t\t\t\t\tuint64 nextAverage64 = nextBytes / nextDuration;\n\t\t\t\t\tif (nextAverage64 > 0xFFFFFFFFui64)\n\t\t\t\t\t\tnextAverage64 = 0xFFFFFFFFui64;\n\n\t\t\t\t\tEmuleNextTransferObservation nextObservation;\n\t\t\t\t\tnextObservation.peerHash = EmuleNextHash16(GetUserHash());\n\t\t\t\t\tnextObservation.fileHash = EmuleNextHash16(nextFile->GetFileHash());\n\t\t\t\t\tnextObservation.fileSize = nextFile->GetFileSize();\n\t\t\t\t\tnextObservation.bytesTransferred = nextBytes;\n\t\t\t\t\tnextObservation.averageBytesPerSecond = static_cast<uint32>(nextAverage64);\n\t\t\t\t\tnextObservation.successful = true;\n\t\t\t\t\tnextObservation.direction = _T("upload");\n\t\t\t\t\tswitch (eNewState) {\n\t\t\t\t\tcase US_ONUPLOADQUEUE: nextObservation.result = _T("slot-complete-queued"); break;\n\t\t\t\t\tcase US_BANNED: nextObservation.result = _T("slot-ended-banned"); break;\n\t\t\t\t\tcase US_CONNECTING: nextObservation.result = _T("slot-reconnecting"); break;\n\t\t\t\t\tcase US_NONE: nextObservation.result = _T("slot-complete"); break;\n\t\t\t\t\tdefault: nextObservation.result = _T("slot-ended"); break;\n\t\t\t\t\t}\n\t\t\t\t\tnextObservation.finishedAt = nextNow;\n\t\t\t\t\tnextObservation.startedAt = nextNow > nextDuration ? nextNow - nextDuration : 0;\n\t\t\t\t\ttheEmuleNext.Database().RecordTransfer(nextObservation);\n\t\t\t\t}\n\t\t\t}\n\n\t\t\t// Reset upload data rate computation\n\t\t\tm_nUpDatarate = 0;\n\t\t\tm_nSumForAvgUpDataRate = 0;\n\t\t\tm_AverageUDR_hist.RemoveAll();\n\t\t}\n'''
    if new not in text:
        if old not in text:
            raise RuntimeError("SetUploadState lifecycle anchor not found")
        text = text.replace(old, new, 1)

    save(text, newline)
    print("eMule Next upload transfer lifecycle active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
