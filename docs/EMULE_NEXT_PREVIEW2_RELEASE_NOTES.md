# eMule Next 0.2.0 Preview 2

Preview 2 is a productization and usability release built on the existing eMule v0.72a protocol core. The release does **not** replace the legacy eD2K/Kad implementation; it adds bounded intelligence, persistent knowledge, recovery tooling and a modernized eMule Next workspace layer around that core.

## Main changes

### Modern Preview 2 workspace

- Shared `EmuleNextModernUi` design layer for DPI-aware spacing, surfaces, cards, fonts and list styling.
- Segoe UI Variable is used when available, with Segoe UI fallback.
- Permanent Search / Library / Known Users / Settings / Diagnostics workspaces get a dedicated Preview 2 navigation sidebar rather than relying only on legacy search-tab semantics.
- Search, Library, Known Users, Dashboard and Transfers use the same modern list/header theming while keeping their existing product logic.
- Dark/light/System appearance continues to use the existing theme service.

### Settings restructured

Normal Settings now contains only user-facing choices:

- **Appearance** — System/Light/Dark and Smart ETA/Health display.
- **Peer knowledge** — automatic shared-file knowledge collection and bounded concurrency.
- **Intelligence** — Analysis / Assist / Automatic mode, scheduler profile and capability toggles.
- **Advanced** — optional explicit scheduler tuning.

History-cache and scheduler-telemetry capacities are no longer normal user controls. Preview 2 keeps these bounded services enabled with conservative internal limits. Runtime counters, integrity status, backups and stress actions belong in Diagnostics instead of Settings.

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

Preview 2 includes the current Search 2, Library 2 and Known Users 2 product tranches, including bounded/background reads, persistence, modern workspace integration and their existing completion gates. Real peer/network behavior still requires the runtime validation matrix before being called fully release-proven.

## Packaging

The repository now provides:

- `build-local.ps1` -> `artifacts/eMule-Next-0.2.0-Preview2-x64.exe`
- `package-preview2.ps1` -> portable Preview 2 ZIP + SHA-256 manifest
- `build-preview2-installer.ps1` -> x64 MSI through WiX CLI
- `installer/preview2/Product.wxs` -> MajorUpgrade-capable MSI definition

The portable ZIP contains no user configuration, intelligence database or download state. The MSI installs only application binaries and shortcuts; normal uninstall/upgrade therefore does not intentionally remove user data.

## Safety defaults

- Smart Scheduling defaults to **Analysis only** unless an existing user profile explicitly selected another mode.
- Automatic intervention remains opt-in.
- User identity remains the 16-byte userhash.
- File identity remains eD2K hash + size.
- No new aggressive peer scanning is introduced.
- SQLite remains outside network/scheduler/GUI hot paths.
- Intelligence/database failure is designed not to block the legacy eMule networking core.

## Still requiring runtime proof

A successful Release x64 build proves compilation and static contracts, not live network compatibility. Before a Preview 2 build is promoted as runtime-proven, complete the runtime matrix in `docs/EMULE_NEXT_RUNTIME_TEST_MATRIX.md` / Diagnostics against real eD2K/Kad peers and real incomplete downloads.
