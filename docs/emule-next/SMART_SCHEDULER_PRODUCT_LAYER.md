# Smart Scheduler product layer

This tranche turns the Smart Scheduler runtime into an inspectable, configurable eMule Next feature without moving database work into GUI or transfer hot paths.

## Runtime controls

The eMule Next Settings view exposes the existing three scheduler modes plus a scheduler profile (`Conservative`, `Balanced`, `Responsive`), intervention cooldown, maximum files analysed per two-second pass, minimum A4AF score, history cache, telemetry, and telemetry retention capacity.

The safe default remains **Analysis only**. Neither Analysis only nor Assist executes a source-discovery intervention. Automatic remains explicit opt-in.

## Bounded work

`SmartSchedulerMaxFilesPerRound` is clamped to 1..32. A scheduler pass runs no more than once every two seconds. The existing round-robin cursor ensures large download queues are sampled over multiple passes rather than rescanned in full.

History sampling can be disabled independently. Telemetry retention is clamped to 16..4096 in-memory events.

## Telemetry semantics

Telemetry distinguishes a recommendation from an actually applied intervention. `appliedInterventions` increments only when runtime code really changes behavior: an extra source request is queued, a rare-part rank is adjusted, or Smart A4AF changes a legacy false preference into a true candidate preference.

The event model records action, health, attention, discovery budget, A4AF score, preferred rare-part index, reason, and applied state. The scheduler snapshot is also marked applied when a later A4AF or rare-part hook actually uses the recommendation.

## Dashboard

The Dashboard receives Scheduler and Applied columns and appends runtime mode/profile/batch/cooldown/tracked/decision/intervention status to the summary. Selected-file details display the cached scheduler action, applied state, and decision reason.

Dashboard reads only `CEmuleNextSmartScheduler` memory snapshots. No SQLite call is permitted in Dashboard, DownloadListCtrl, DownloadQueue, or PartFile.

## Safety invariants

- Analysis only is the default.
- Automatic remains opt-in.
- Existing eD2K/Kad protocol restrictions remain authoritative.
- A4AF intelligence can only turn an already valid legacy candidate comparison from false to true; it never bypasses suspension/source/protocol checks.
- Rare-part intelligence applies a bounded ranking adjustment.
- Extra source discovery uses the existing `SendLocalSrcRequest` path and scheduler cooldown.
- No synchronous database query is introduced into paint, list refresh, queue processing, or part-selection paths.
