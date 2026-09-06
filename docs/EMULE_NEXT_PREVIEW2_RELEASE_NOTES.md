# eMule Next 0.2.0 Preview 2

Preview 2 is the productization/usability release around the existing eMule v0.72a protocol core. It does **not** replace eD2K/Kad/search/download/upload/hashing; it adds bounded intelligence, persistent knowledge, recovery tooling and a modern Windows workspace layer around that core.

## Primary shell

Primary navigation:

- Dashboard
- Transfers
- Search
- Library
- Shared Files
- Known Users
- Messages
- Servers
- Kad
- Statistics
- Settings
- Diagnostics
- IRC

The classic toolbar/dialogs remain available where required for compatibility, but the Preview 2 sidebar/header is the primary product chrome. Header connection/rate status reuses existing eMule refresh paths.

## Search

Search opens Search 2 as the normal workspace. Search 2 is an intelligence/history presentation layer and does not implement a second network engine.

**Network search...** opens the existing legacy eD2K/Kad search parameters/result tabs. Server/global/Kad routing therefore remains upstream-authoritative.

## Settings

The modern Settings shell has four eMule Next categories:

- Appearance
- Peer knowledge
- Intelligence
- Advanced

It also exposes all 15 production upstream Preferences pages:

- General
- Display
- Connection
- Proxy
- Server
- Directories
- Files
- Notifications
- Statistics
- IRC
- Messages
- Security
- Scheduler
- Web Server
- Tweaks

Original pages remain authoritative and are opened through the existing page-ID/`ShowPreferences` path; Preview 2 does not duplicate hundreds of legacy preference values into another storage model.

## Theme / UI

- Shared DPI-aware ModernUi layer.
- Segoe UI Variable with Segoe UI fallback.
- System / Light / Dark centrally controlled.
- Primary legacy workspaces are re-themed when activated.
- Theme Apply refreshes the main window tree.
- Messages/Chat has explicit Friends/tab/input/RichEdit theme handling to prevent a system-white conversation surface in Dark mode.
- Settings navigation is scrollable for smaller windows/high DPI.

## Dashboard

Primary filters:

- All
- Attention
- Stalled
- No sources
- Active

Primary actions:

- Open Transfers
- Open Sources
- Pause/Resume
- Refresh
- More...

`More...` keeps rare-parts, low-health, intervention, A4AF, priority, forced-analysis and history-reset actions available without a permanent button wall.

## Search 2 / Library 2 / Known Users 2

Preview 2 includes the current bounded/background Search 2, Library 2 and Known Users 2 functionality. Library and Known Users are promoted into primary navigation. User identity remains the 16-byte userhash; file identity remains eD2K hash + size.

## Diagnostics / recovery / performance

Diagnostics includes:

- database health/schema;
- async writer queue;
- Smart Scheduler runtime;
- integrity/backup/restore/prune/checkpoint;
- performance stress self-test;
- report export and privacy-bounded support tooling.

Stress targets:

- ClientIndex: 10,000
- DownloadIndex: 5,000
- temporary async DB writer: 10,000 events

PASS requires queued=0, processed=expected, dropped=0 and errors=0.

## Zero-warning Release x64 contract

The Release x64 FullRebuild is now a zero-warning build:

- compiler warnings are errors;
- linker warnings are errors;
- LTCG is explicit;
- x64 pointer/handle truncations exposed by the full rebuild were corrected;
- eMule Next `CWnd::Create` hiding is systematically hardened;
- MFC C4191 handling is scoped only around real active message-map macro tables;
- commented-out MFC macro text is never materialized as active code;
- Microsoft/MFC vendor-header warning handling is locally scoped rather than globally disabled.

The user-confirmed FullRebuild on `7a8844a7d329fc5a8bd787f62b209763f73fe9a6` completed with **0 compilerwarnings, 0 linkerwarnings and 0 errors**.

## Build-bound runtime acceptance

Preview 2 now includes `preview2-runtime-acceptance.ps1`.

It writes `artifacts/preview2-runtime-acceptance.json` containing:

- Git HEAD;
- SHA256 of the exact tested executable;
- PASS/FAIL/NOT_TESTED for each acceptance item;
- notes/timestamps.

A record from another HEAD or executable hash is rejected.

Core acceptance includes:

- startup/shell and all primary routes;
- Search 2 → Network search bridge;
- all 19 Settings categories/page routing;
- live header and Dashboard actions;
- Dark/Light/System + DPI/resize;
- Diagnostics stress/DB maintenance;
- real eD2K and Kad behavior;
- upload/queue/intelligence;
- Known Users and Library;
- restart persistence and recovery;
- support report/bundle privacy.

`finalize-preview2-rc.ps1` refuses to create the RC artifact set until `preview2-runtime-acceptance.ps1 -VerifyCore` passes for the exact current build.

After artifact creation, package checks cover portable start and MSI install/upgrade/uninstall. `preview2-runtime-acceptance.ps1 -VerifyAll` is the final package-ready gate.

## Packaging

Repository tooling:

- `build-local.ps1` → `artifacts/eMule-Next-0.2.0-Preview2-x64.exe`
- `package-preview2.ps1` → portable ZIP + SHA256 manifest
- `build-preview2-installer.ps1` → x64 WiX MSI
- `create-preview2-support-bundle.ps1` → privacy-bounded support ZIP
- `preview2-runtime-acceptance.ps1` → exact-build acceptance evidence
- `finalize-preview2-rc.ps1` → acceptance gate, release verification, portable, optional MSI and RC hash manifest

The portable package contains release/test documentation, the support helper and acceptance harness, but no user configuration, intelligence database, peer history or download state.

The MSI owns application binaries/shortcuts only. Normal install/upgrade/uninstall must not delete user configuration, intelligence DB or incomplete downloads.

The RC manifest records Git HEAD plus SHA256 for the executable, portable ZIP, optional MSI and the acceptance record.

## Safety defaults

- Smart Scheduling defaults to **Analysis only** unless an existing profile explicitly selected another mode.
- Automatic intervention remains opt-in.
- No aggressive peer scanning is introduced.
- SQLite remains outside network/scheduler/GUI hot paths.
- Intelligence/database failure is designed not to block the legacy networking core.

## Runtime proof still required

Build/static completion is now proven for the zero-warning Release tranche. Live eD2K/Kad, UI/theme/DPI, persistence/recovery and package behavior still require execution on the actual Windows runtime. Those results must be recorded through the build-bound acceptance harness before Preview 2 is called a Release Candidate/package-ready build.
