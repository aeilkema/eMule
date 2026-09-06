# eMule Next 0.2.0 Preview 2

Preview 2 is a productization and usability release built on the existing eMule v0.72a protocol core. The release does **not** replace the legacy eD2K/Kad implementation; it adds bounded intelligence, persistent knowledge, recovery tooling and a modernized eMule Next workspace layer around that core.

## Main changes

### One primary Preview 2 shell

The modern Preview 2 shell is now the primary product chrome rather than an extra layer behind the classic toolbar.

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

The classic toolbar and upstream dialogs remain available for compatibility, but Library, Known Users, Settings and Diagnostics no longer require users to navigate through an internal Search sidebar.

The header includes the active section, Connect/Disconnect and live connection/transfer status using the existing eMule refresh paths rather than a second polling loop.

### Modern Search with preserved legacy network search

**Search** now opens Search 2 as the normal Preview 2 search workspace.

Search 2 remains an intelligence/history layer. It does not implement a second eD2K/Kad network engine. A visible **Network search...** action switches to the existing `CSearchDlg`, restores the legacy Search result selector/tabs and opens the existing Search parameters. Server/global/Kad network routing therefore remains upstream-authoritative.

The late Search bridge also has an explicit compile-order contract so it does not depend on accidental precompiled-header side effects.

### Modern Preview 2 workspace styling

- Shared `EmuleNextModernUi` design layer for DPI-aware spacing, surfaces, cards, fonts and list styling.
- Segoe UI Variable is used when available, with Segoe UI fallback.
- Search, Library, Known Users, Dashboard and Transfers use the same modern list/header theming while keeping their existing product logic.
- Dark/light/System appearance continues to use the existing theme service.
- Every legacy primary workspace is re-themed whenever it becomes active.
- The complete original Preferences tree receives the active Preview 2 theme after its pages are initialized.
- Messages/Chat has additional explicit dark/light handling for Friends, tabs, input controls and existing/new RichEdit chat logs so Dark mode does not leave the conversation surface system-white.

### Dashboard progressive complexity

Dashboard remains the daily transfer overview but no longer presents every specialist action as a permanent button.

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

`More...` keeps Rare parts, Low health, Intervention, A4AF, priority changes, forced analysis and intelligence reset available without dominating the normal workflow. The summary line is reduced to daily state: downloads, active items, attention count, transfer rate, uploads and scheduler state.

### Complete Settings entry point

Preview 2 keeps its four native categories directly editable in the modern Settings workspace:

- **Appearance** — System/Light/Dark and Smart ETA/Health display.
- **Peer knowledge** — automatic shared-file knowledge collection and bounded concurrency.
- **Intelligence** — Analysis / Assist / Automatic mode, scheduler profile and capability toggles.
- **Advanced** — optional explicit scheduler tuning.

The same Settings navigation now also represents **all 15 production upstream eMule Preferences pages**:

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

For those original pages, Preview 2 deliberately does not duplicate hundreds of values into a second settings database or UI model. Selecting a category exposes a targeted **Open … settings...** action which opens that exact original property page through the existing `CemuleDlg::ShowPreferences(pageId)` path. The original validation, Apply/OK behavior and `thePrefs` storage therefore remain authoritative.

The resource ID for each original page is derived from its existing `PPg*.h` declaration during clean activation. The Settings navigation is scrollable for smaller windows/high DPI. Applying a theme refreshes the complete application window tree rather than only the Settings host.

History-cache and scheduler-telemetry capacities remain bounded internal product defaults. Runtime counters, integrity status, backups and stress actions belong in Diagnostics rather than normal Settings.

### Diagnostics and runtime validation

Diagnostics is now a status dashboard with cards for:

- database health and schema;
- async writer queue;
- Smart Scheduler runtime;
- performance self-test.

Maintenance actions remain background operations. The existing backup/integrity/recovery/WAL/pruning functionality is preserved.

A persistent runtime-validation matrix is included for real-world tests that cannot honestly be proven by static source gates alone, including:

- eD2K server/download;
- Kad network/search;
- upload to legacy peers;
- manual View Shared Files;
- pause/resume/restart;
- Scheduler modes;
- A4AF;
- rare-part selection;
- hashing/recovery;
- Preview 2 DPI/UX.

Tests can be marked PASS/FAIL/reset in Diagnostics and exported together with the current database/writer/scheduler snapshot.

### Performance and recovery foundation

Preview 2 includes the previously implemented hardening blocks:

- bounded ClientIndex / DownloadIndex lookups;
- deterministic index stress test;
- disposable 10,000-event async writer-queue stress test;
- database schema v3;
- online SQLite backup;
- pre-migration backup;
- integrity and quick checks;
- safe restore with pre-restore archive;
- WAL checkpoint;
- bounded telemetry pruning;
- writer queue counters and recovery-required state.

### Search 2 / Library 2 / Known Users 2

Preview 2 includes the current Search 2, Library 2 and Known Users 2 product tranches, including bounded/background reads, persistence, modern workspace integration and their existing completion gates. Library and Known Users are promoted into primary navigation. Real peer/network behavior still requires the runtime validation matrix before being called fully release-proven.

## Clean build and materialization

`build-local.ps1` builds from a clean activation overlay. The base runtime/UI chain runs first, followed by `activate-preview2.py` exactly once as the explicit final product layer. The Preview 2 orchestrator parses all late scripts before applying them and then runs dedicated activation-chain, Settings/theme, UX and product final-state gates.

This prevents a successful Preview 2 build from accidentally depending on stale generated source from a previous local build.

## Packaging and support

The repository provides:

- `build-local.ps1` -> `artifacts/eMule-Next-0.2.0-Preview2-x64.exe`
- `package-preview2.ps1` -> portable Preview 2 ZIP + SHA-256 manifest
- `build-preview2-installer.ps1` -> x64 MSI through WiX CLI
- `installer/preview2/Product.wxs` -> MajorUpgrade-capable MSI definition
- `create-preview2-support-bundle.ps1` -> privacy-bounded support ZIP from an exported Diagnostics report
- `finalize-preview2-rc.ps1` -> release verification, portable package, optional MSI and final SHA-256 RC manifest

The portable ZIP contains no user configuration, intelligence database or download state. The MSI installs only application binaries and shortcuts; normal uninstall/upgrade therefore does not intentionally remove user data.

The support bundle explicitly excludes the intelligence SQLite database, Preferences/config files, peer history/`known.met` and incomplete `.part/.part.met` downloads.

## Safety defaults

- Smart Scheduling defaults to **Analysis only** unless an existing user profile explicitly selected another mode.
- Automatic intervention remains opt-in.
- User identity remains the 16-byte userhash.
- File identity remains eD2K hash + size.
- No new aggressive peer scanning is introduced.
- SQLite remains outside network/scheduler/GUI hot paths.
- Intelligence/database failure is designed not to block the legacy eMule networking core.

## Still requiring runtime proof

A successful Release x64 build proves compilation and static contracts, not live network compatibility or final theme coverage. Before a Preview 2 build is promoted as runtime-proven, complete the runtime matrix in `docs/EMULE_NEXT_RUNTIME_TEST_MATRIX.md` / Diagnostics and verify all 19 Settings categories plus Light/Dark/System across the primary workspaces on real runtime state.
