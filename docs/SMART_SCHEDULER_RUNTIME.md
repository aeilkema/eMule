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
- Hot history cache: configurable and bounded; default 4096 files.
- In-memory telemetry ring: configurable 16..4096 events, default 256.
- Telemetry persistence queue: maximum 8192 pending events; oldest pending event is dropped when full.
- Telemetry SQLite writes are batched up to 256 events per transaction.
- No SQLite access occurs from the queue tick, transfer-insight builder, A4AF comparison, block-ranking hook or Dashboard refresh path.

`verify-no-hotpath-sqlite.py` enforces the last invariant against the materialized build tree.

## Persistent history cache

`CEmuleNextHistoryCache` remains the memory-only read path used by the scheduler and Dashboard. Persistence is isolated behind its own worker thread and bounded queue.

When the eMule Next runtime database is available, the scheduler supplies the existing `emule-next.sqlite3` path to the history cache. The worker restores previously observed EWMA rates and asynchronously persists new observations. Failure to open or use the database does not make the scheduler block on SQLite; the cache continues as an in-memory fallback.

The history cache exposes persistence readiness, generation and refresh state for runtime diagnostics. Disabling `SmartHistoryCache` stops using historical rates in scheduler decisions without changing the legacy transfer core.

## Persistent scheduler telemetry

`CEmuleNextSchedulerTelemetry` keeps a bounded in-memory ring for immediate diagnostics and has a separate SQLite persistence worker. The scheduler only enqueues an `EmuleNextSchedulerEvent`; it never executes SQL itself.

Persistent events are stored in `scheduler_decisions` with:

- timestamp and file name;
- scheduler mode and selected action;
- health and attention scores;
- discovery budget and A4AF score;
- selected rare-part index when applicable;
- whether the decision was applied immediately;
- the policy reason.

The persistent table is pruned to approximately the latest 10,000 decisions. Runtime diagnostics expose whether telemetry persistence is ready, the pending write count and the number of persistence events dropped because the worker/queue was unavailable or full.

A4AF and rare-part hooks can mark a scheduler snapshot as applied after the original evaluation event was recorded. The in-memory intervention count reflects those late applications. The original persisted evaluation row is intentionally not mutated from the hot hook; exact late-hook event correlation can be added later without violating the no-SQL-hotpath rule.

## Shared transfer intelligence

Dashboard and Smart Scheduler use `CEmuleNextTransferInsights::Build` as the canonical transfer-signal builder. Health, stall diagnosis, Smart ETA and attention therefore come from the same calculations used for scheduler decisions instead of separate Dashboard-only implementations.

The Dashboard may read historical EWMA values from the in-memory history cache. It does not read SQLite directly.

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

Settings exposes mode, profile, cooldown, pass size, A4AF threshold, feature flags, history, telemetry and telemetry retention. `GetRuntimeStatusText()` reports scheduler mode/profile, scan size, cooldown, tracked/history counts, history persistence state, telemetry persistence state, pending/dropped telemetry writes, decision count and applied intervention count.

Dashboard and Settings use shared `EmuleNextUiMetrics` geometry for the eMule Next layout/columns that were added by this project. This makes those areas DPI-aware without rewriting unrelated legacy MFC layout code.

## Verification

The local activation pipeline runs these relevant checks before compilation:

- `verify-smart-scheduling.py`
- `verify-smart-scheduler-runtime.py`
- `verify-smart-scheduler-product.py`
- `verify-dashboard-shared-insights.py`
- `verify-ui-metrics.py`
- `verify-no-hotpath-sqlite.py`
- `verify-scheduler-persistence.py`
- `audit-activators.py`
- `verify-next-integration.py`

The verifiers are intentionally fail-fast: a missing runtime hook, project entry, persistence worker, shared-intelligence contract or hot-path SQLite violation stops the local build before MSBuild starts.
