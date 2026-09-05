# eMule Next Smart Scheduler runtime

This tranche turns the existing deterministic `DownloadIntelligence` policy layer into a bounded runtime system while keeping the legacy eD2K/Kad protocol core authoritative.

## Runtime hooks

The compatibility activator `tools/emule-next/activate-smart-scheduler-runtime.py` materializes only three legacy hooks:

1. `CDownloadQueue::Process()` calls `theEmuleNextScheduler.Tick(this)`. The scheduler internally runs at most once every two seconds and evaluates at most eight downloads per pass using round-robin traversal.
2. `CUpDownClient::SwapToAnotherFile()` lets the Smart Scheduler raise an A4AF candidate above the legacy preference only in Automatic mode and only when the candidate clears the configured score margin. The legacy result remains the fallback.
3. `CPartFile::GetNextRequestedBlock()` applies a bounded rank bonus to one completion-critical rare part in Automatic mode. Existing legacy rank computation remains the baseline.

All three hooks are idempotently materialized during `build-local.ps1` and are verified before compilation.

## Modes

`SmartSchedulingMode` remains the master safety switch:

- `0` Analysis only: collect/evaluate intelligence without changing scheduler choices.
- `1` Assist: recommendations and snapshots only.
- `2` Automatic: feature-gated source-discovery, A4AF and rare-part interventions may be applied.

Existing feature flags remain independent:

- `SmartSourceDiscovery`
- `SmartA4AF`
- `SmartRareParts`
- `SmartEtaHealthDisplay`

## Profiles and cooldown

The runtime supports `SmartSchedulerProfile`:

- `0` Conservative: smaller discovery budget, stronger A4AF threshold, 180 s default cooldown.
- `1` Balanced: default; moderate budgets and 90 s cooldown.
- `2` Responsive: larger discovery budget, lower A4AF threshold, 45 s cooldown.

`SmartSchedulerCooldown` can override the profile cooldown from 30 to 1800 seconds. `SmartA4AFMinimumScore` can override the default A4AF threshold.

## Performance boundaries

- Scheduler tick gate: 2 seconds.
- Maximum files evaluated per pass: 8.
- Scheduler snapshots: maximum 4096 files.
- Session EWMA history cache: maximum 4096 files.
- Scheduler telemetry ring: default 256 events.
- No SQLite access occurs from the queue tick, A4AF comparison or block-ranking hook.

The session history cache deliberately holds only hot runtime EWMA data. The existing SQLite transfer/source history remains the durable store; a later persistence bridge can refresh the cache off-thread without changing the hot-path contract.

## Source discovery

Automatic discovery does not bypass legacy throttling. When intelligence detects a low-source download and the intervention cooldown allows action, the scheduler calls the existing `CDownloadQueue::SendLocalSrcRequest` path. The existing queue/rate-limit behavior therefore remains in control of actual network requests.

## A4AF

The scheduler does not replace `RightFileHasHigherPrio`. It receives the legacy answer and may promote a candidate only when:

- Automatic mode is active;
- Smart A4AF is enabled;
- the candidate has a cached scheduler snapshot;
- the candidate clears the minimum A4AF score;
- its score exceeds the current file by at least 80 points; and
- its attention score is not lower than the current file.

Otherwise the exact legacy preference is returned.

## Rare parts

`DownloadIntelligence::ChooseRarestRiskPart` remains deterministic. `EmuleNextTransferInsights` keeps its part vector aligned to actual part numbers, including completed parts as protected high-availability entries. The runtime therefore cannot accidentally interpret a compact vector index as an eMule part number.

## Verification

`verify-smart-scheduler-runtime.py` checks source presence, build-project inclusion and all three runtime hooks. It runs automatically from `activate-features.py` after runtime materialization and before compilation.
