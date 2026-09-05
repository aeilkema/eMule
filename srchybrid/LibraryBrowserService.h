//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include "EmuleNextDatabase.h"
#include <vector>

enum EmuleNextLibraryViewFilter
{
    ENLV_HISTORY = 0,
    ENLV_FAVORITES,
    ENLV_COMPLETED,
    ENLV_MISSING,
    ENLV_DOWNLOAD_LATER
};

struct EmuleNextLibraryBrowseRow
{
    EmuleNextHash16 fileHash;
    uint64 fileSize;
    CStringW fileName;
    CStringW aichHash;
    uint64 lastSeen;
    bool favorite;
    bool completed;
    bool missing;
    bool downloadLater;
    CStringW localPath;

    EmuleNextLibraryBrowseRow();
};

class CLibraryBrowserService
{
public:
    explicit CLibraryBrowserService(const CStringW& databasePath);
    bool List(EmuleNextLibraryViewFilter filter,
        std::vector<EmuleNextLibraryBrowseRow>& rows,
        size_t maximumRows = 5000) const;

private:
    CStringW m_databasePath;
};
