# eMule Next Smart Scheduler runtime

The Smart Scheduler turns the deterministic `DownloadIntelligence` policy layer into a bounded runtime system while keeping the legacy eD2K/Kad protocol core authoritative.

## Runtime hooks

The compatibility activator `tools/emule-next/activate-smart-scheduler-runtime.py` materializes only three legacy hooks:

1. `CDownloadQueue::Process()` calls `theEmuleNextScheduler.Tick(this)`. The scheduler internally runs at most once every two seconds and evaluates a bounded number of downloads using round-robin traversal.
2. `CUpDownClient::SwapToAnotherFile()` lets the Smart Scheduler raise an A4AF candidate above the legacy preference only in Automatic mode and only when the candidate clears the configured score margin. The legacy result remains the fallback.
3. `CPartFile::GetNextRequestedBlock()` applies a bounded rank bonus to one completion-critical rare part in Automatic mode. Existing legacy rank computation remains the baseline.

All hooks are idempotently materialized during `build-local.ps1` and verified before compilation.

## Modes

`SmartSchedulingMode` is the master safety switch:

- `0` Analysis only: collect and evaluate intelligence without changing scheduler choices.
- `1` Assist: recommendations and snapshots only.
- `2` Automatic: feature-gated source-discovery, A4AF and rare-part interventions may be applied.

The default remains Analysis only. Feature flags remain independent:

- `SmartSourceDiscovery`
- `SmartA4AF`
- `SmartRareParts`
- `SmartEtaHealthDisplay`
- `SmartHistoryCache`
- `SmartTelemetry`

## Profiles and cooldown

The runtime supports `SmartSchedulerProfile`:

- `0` Conservative: smaller discovery budget, stronger A4AF threshold, 180 s default cooldown.
- `1` Balanced: default; moderate budgets and 90 s cooldown.
- `2` Responsive: larger discovery budget, lower A4AF threshold, 45 s cooldown.

`SmartSchedulerCooldown` can override the profile cooldown from 30 to 1800 seconds. `SmartA4AFMinimumScore` can override the default A4AF threshold. `SmartSchedulerMaxFilesPerRound` is bounded to 1..32 and defaults to 8.

## Performance boundaries

- Scheduler tick gate: 2 seconds.
- Files evaluated per pass: configurable 1..32, default 8.
- Scheduler snapshots: maximum 4096 files.
- Hot history cache: configurable 128..16384 internally; Settings exposes practical presets from 512 through 16384, default 4096.
- History persistence queue: maximum 8192 pending writes.
- In-memory telemetry ring: configurable 16..4096 events, default 256.
- Combined telemetry decision/applied-update persistence queues: maximum 8192 pending items.
- History and telemetry SQLite writes are batched up to 256 items per transaction.
- No SQLite access occurs from the queue tick, transfer-insight builder, A4AF comparison, block-ranking hook or Dashboard refresh path.
- History startup reads SQLite rows into a worker-local buffer before acquiring the scheduler-facing cache mutex.
- History cache eviction is bounded and performed as one ordered pass rather than repeated full-map scans.

`verify-no-hotpath-sqlite.py` enforces the hot-path and cache-lock invariants against the materialized build tree.

## Persistent history cache

`CEmuleNextHistoryCache` is the memory-only read path used by the scheduler and Dashboard. Persistence is isolated behind its own worker thread and bounded queue.

When the eMule Next runtime database is available, the scheduler supplies the existing `emule-next.sqlite3` path to the history cache. The worker restores previously observed EWMA rates and asynchronously persists new observations in `scheduler_file_history`. Failure to open or use the database does not make the scheduler execute SQLite; the cache continues as an in-memory fallback and retries are rate-limited.

The cache exposes persistence readiness, generation, pending writes and dropped writes for runtime diagnostics. Disabling `SmartHistoryCache` stops using historical rates in scheduler decisions without changing the legacy transfer core.

## Persistent scheduler telemetry

`CEmuleNextSchedulerTelemetry` keeps a bounded in-memory ring for immediate diagnostics and has a separate SQLite persistence worker. The scheduler only enqueues value objects; it never executes SQL itself.

Persistent events are stored in `scheduler_decisions` with:

- timestamp;
- stable 16-byte eD2K file hash plus file name for presentation/legacy fallback;
- scheduler mode and selected action;
- health and attention scores;
- discovery budget and A4AF score;
- selected rare-part index when applicable;
- whether the decision was actually applied;
- the policy reason.

Existing Preview databases are migrated additively with a nullable `file_hash` column and a hash/applied lookup index. New rows are correlated by file hash. File-name matching is used only as fallback for old rows which predate hash telemetry.

The persistent table is pruned to approximately the latest 10,000 decisions. Runtime diagnostics expose persistence readiness, pending writes and persistence drops.

A4AF and rare-part hooks can apply a decision after its original evaluation row was recorded. Those hooks only update memory and enqueue a small applied-state item. The telemetry worker then marks the latest matching persistent decision `applied=1` by file hash. No SQL runs in the hook itself.

## Shared transfer intelligence

Dashboard and Smart Scheduler use `CEmuleNextTransferInsights::Build` as the canonical transfer-signal builder in both Dashboard list refresh and detail rendering. Health, stall diagnosis, Smart ETA and attention therefore come from the same calculations used for scheduler decisions instead of separate Dashboard-only implementations.

The Dashboard may read historical EWMA values from the in-memory history cache. It does not read SQLite directly.

Live source-quality sampling is bounded to 32 sources per file and at most 256 part checks per sampled source.

## Source discovery

Automatic discovery does not bypass legacy throttling. When intelligence detects a low-source download and the intervention cooldown allows action, the scheduler calls the existing `CDownloadQueue::SendLocalSrcRequest` path. The existing queue/rate-limit behavior remains in control of actual network requests.

The intelligence `discoveryBudget` is currently a policy signal and gate, not a direct instruction to issue that many network requests.

## A4AF

The scheduler does not replace `RightFileHasHigherPrio`. It receives the legacy answer and may promote the currently evaluated candidate only when:

- Automatic mode is active;
- Smart A4AF is enabled;
- the candidate has a cached scheduler snapshot;
- the candidate clears the minimum A4AF score;
- its score exceeds the current best file by at least 80 points; and
- its attention score is not lower than the current best file.

Otherwise the exact legacy preference is returned. The hook keeps the original `SwapTo`/`cur_file` orientation used by `CUpDownClient::SwapToAnotherFile`: `SwapTo` is the current best candidate and `cur_file` is the newly evaluated candidate.

## Rare parts

`DownloadIntelligence::ChooseRarestRiskPart` remains deterministic. `EmuleNextTransferInsights` keeps its part vector aligned to actual part numbers, including completed parts as protected high-availability entries. The runtime therefore cannot accidentally interpret a compact vector index as an eMule part number.

## UI and diagnostics

Settings exposes mode, profile, cooldown, pass size, A4AF threshold, feature flags, history enablement, history capacity, telemetry enablement and telemetry retention. `GetRuntimeStatusText()` reports scheduler mode/profile, scan size, cooldown, tracked/history counts, history generation, history persistence queue/drops, telemetry persistence queue/drops, decision count and applied intervention count.

Dashboard and Settings use shared `EmuleNextUiMetrics` geometry. Search 2, Library and Known Users receive the same DPI-aware metrics during activation.

Search 2 result lookup already runs in a background worker. Recurring saved-search metadata refresh is also moved to a below-normal worker so opening or refreshing the view does not perform that SQLite read on the MFC UI thread.

History-heavy UI data is explicitly bounded: Search 2 uses paged reads with a 2000-result UI cap, Library loads at most 5000 rows for a view, and Known Users caps both users and files for one peer at 5000 rows.

## Isolated local activation/build

`build-local.ps1` no longer runs integration/feature activators against the checked-out `srchybrid` directory. It creates `build/activation-stage`, copies the repository overlay and eMule Next tools there, and runs:

1. `integrate.py` in staging;
2. `activate-features.py` in staging;
3. `verify-activation-idempotence.py`, which runs activation a second time and requires an identical staged source tree;
4. the fully activated/verified staged overlay is copied over the generated upstream v0.72a source tree;
5. MSBuild compiles the generated x64 Release tree.

A successful build removes the activation stage unless `-KeepActivationStage` is supplied. A failed build keeps the stage for diagnosis. This separates activator/integration failures from actual C++ compiler/linker failures and prevents a normal build from dirtying the repository overlay.

## Verification

The local activation pipeline runs these relevant checks before compilation:

- `verify-search2-background-metadata.py`
- `verify-ui-data-bounds.py`
- `verify-smart-scheduling.py`
- `verify-smart-scheduler-runtime.py`
- `verify-smart-scheduler-product.py`
- `verify-transfer-insights-bounds.py`
- `verify-dashboard-shared-insights.py`
- `verify-ui-metrics.py`
- `verify-no-hotpath-sqlite.py`
- `verify-scheduler-persistence.py`
- `audit-activators.py`
- `verify-next-integration.py`

`build-local.ps1` then runs `verify-activation-idempotence.py` as a second complete activation pass. The verifiers are intentionally fail-fast: a missing runtime hook, stale implementation-specific assumption, project entry, persistence worker, data bound, shared-intelligence contract or hot-path SQLite violation stops the local build before MSBuild starts.