//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later

#include "stdafx.h"
#include "emule.h"
#include "EmuleNextRuntime.h"
#include "SearchDlg.h"
#include "SearchFile.h"
#include "SearchList.h"

namespace
{
    bool SearchListMatchesEndpoint(const SearchList& files, uint32 peerIP, uint16 peerPort)
    {
        if (peerIP == 0 || peerPort == 0)
            return false;

        for (POSITION pos = files.GetHeadPosition(); pos != NULL;) {
            const CSearchFile* file = files.GetNext(pos);
            if (file == NULL || file->GetListParent() != NULL)
                continue;
            if (file->GetClientID() == peerIP && file->GetClientPort() == peerPort)
                return true;
        }
        return false;
    }
}

bool CSearchList::ImportClientSharedFilesForPeer(LPCTSTR userName,
    const uchar* peerHash,
    uint32 peerIP,
    uint16 peerPort,
    uint32& fileCount,
    uint64& totalBytes)
{
    fileCount = 0;
    totalBytes = 0;

    EmuleNextHash16 hash(peerHash);
    if (!hash.valid || userName == NULL || *userName == _T('\0')
        || theApp.emuledlg == NULL || theApp.emuledlg->searchwnd == NULL)
        return false;

    CArray<SearchListsStruct*, SearchListsStruct*> candidates;
    for (POSITION pos = m_listFileLists.GetHeadPosition(); pos != NULL;) {
        SearchListsStruct* list = m_listFileLists.GetNext(pos);
        if (list == NULL)
            continue;

        const SSearchParams* params = theApp.emuledlg->searchwnd->GetSearchParamsBySearchID(list->m_nSearchID);
        if (params == NULL || !params->bClientSharedFiles)
            continue;
        if (params->strExpression.CompareNoCase(userName) == 0)
            candidates.Add(list);
    }

    if (candidates.IsEmpty())
        return false;

    SearchListsStruct* selected = NULL;
    if (candidates.GetCount() == 1)
        selected = candidates[0];
    else {
        for (INT_PTR i = 0; i < candidates.GetCount(); ++i) {
            if (SearchListMatchesEndpoint(candidates[i]->m_listSearchFiles, peerIP, peerPort)) {
                if (selected != NULL)
                    return false; // more than one endpoint match: do not guess identity
                selected = candidates[i];
            }
        }
    }

    if (selected == NULL)
        return false;

    for (POSITION pos = selected->m_listSearchFiles.GetHeadPosition(); pos != NULL;) {
        CSearchFile* file = selected->m_listSearchFiles.GetNext(pos);
        if (file == NULL || file->GetListParent() != NULL || file->GetFileSize() == 0)
            continue;

        theEmuleNext.RecordFileSeen(file->GetFileHash(), file->GetFileSize(), file->GetFileName());
        theEmuleNext.RecordPeerFileSeen(peerHash, file->GetFileHash(), file->GetFileSize(),
            file->GetFileName(), CString(), _T("legacy-restored-share"));
        ++fileCount;
        totalBytes += file->GetFileSize();
    }

    return fileCount > 0;
}
