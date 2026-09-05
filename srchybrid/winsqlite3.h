// Minimal WinSQLite ABI declarations used by eMule Next.
//
// Windows provides the implementation in winsqlite3.dll. The upstream
// Windows SDK header is intentionally not required here because some hosted
// SDK packages expose it in a form that is incompatible with this legacy MFC
// translation unit. Keep this file limited to the stable SQLite C ABI that
// EmuleNextDatabase.cpp actually consumes.
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

typedef struct sqlite3 sqlite3;
typedef struct sqlite3_stmt sqlite3_stmt;
typedef struct sqlite3_backup sqlite3_backup;
typedef long long sqlite3_int64;
typedef void (*sqlite3_destructor_type)(void*);
typedef int (*sqlite3_callback)(void*, int, char**, char**);

int sqlite3_open16(const void* filename, sqlite3** ppDb);
int sqlite3_close(sqlite3* db);
int sqlite3_busy_timeout(sqlite3* db, int ms);

int sqlite3_exec(sqlite3* db, const char* sql, sqlite3_callback callback, void* arg, char** errmsg);
void sqlite3_free(void* ptr);

int sqlite3_prepare_v2(sqlite3* db, const char* sql, int nByte, sqlite3_stmt** statement, const char** tail);
int sqlite3_step(sqlite3_stmt* statement);
int sqlite3_finalize(sqlite3_stmt* statement);

int sqlite3_bind_blob(sqlite3_stmt* statement, int index, const void* value, int bytes, sqlite3_destructor_type destructor);
int sqlite3_bind_text16(sqlite3_stmt* statement, int index, const void* value, int bytes, sqlite3_destructor_type destructor);
int sqlite3_bind_null(sqlite3_stmt* statement, int index);
int sqlite3_bind_int(sqlite3_stmt* statement, int index, int value);
int sqlite3_bind_int64(sqlite3_stmt* statement, int index, sqlite3_int64 value);

const void* sqlite3_column_blob(sqlite3_stmt* statement, int column);
const void* sqlite3_column_text16(sqlite3_stmt* statement, int column);
int sqlite3_column_int(sqlite3_stmt* statement, int column);
sqlite3_int64 sqlite3_column_int64(sqlite3_stmt* statement, int column);

sqlite3_backup* sqlite3_backup_init(sqlite3* destination, const char* destinationName,
    sqlite3* source, const char* sourceName);
int sqlite3_backup_step(sqlite3_backup* backup, int pages);
int sqlite3_backup_finish(sqlite3_backup* backup);

int sqlite3_wal_checkpoint_v2(sqlite3* db, const char* databaseName, int mode,
    int* logFrames, int* checkpointedFrames);

#ifdef __cplusplus
}
#endif

#define SQLITE_OK 0
#define SQLITE_ROW 100
#define SQLITE_DONE 101
#define SQLITE_CHECKPOINT_PASSIVE 0
#define SQLITE_TRANSIENT ((sqlite3_destructor_type)-1)
