# eMule Next - Preview 2 runtime / stress / protocol matrix

This matrix separates what can be proven deterministically offline from what must be validated against real eD2K/Kad peers and real files. A green local build or static verifier never counts as a successful network/runtime test.

## A. Deterministic offline self-tests

| ID | Test | Expected | Status |
|---|---|---|---|
| PERF-STRESS-01 | Diagnostics -> Run index stress test | 10,000 ClientIndex + 5,000 DownloadIndex registrations, lookups, updates and unregisters complete with PASS | Open |
| PERF-STRESS-02 | Repeat PERF-STRESS-01 10 times in one session | No crash, no progressive slowdown, no UI freeze; worker remains outside GUI thread | Open |
| DATA-RECOVERY-01 | Full integrity check | `ok` | Open |
| DATA-RECOVERY-02 | Manual backup | Validated `.sqlite3` appears under `emule-next-backups` | Open |
| DATA-RECOVERY-03 | WAL checkpoint | Completes without writer/database error | Open |
| DATA-RECOVERY-04 | Restore a validated backup | Current DB archived first; restored DB passes integrity check and intelligence restarts | Open |

## B. Performance and scale runtime tests

| ID | Scenario | Observation / acceptance | Status |
|---|---|---|---|
| PERF-RUN-01 | 0 downloads | Dashboard/Transfers/Search/Library/Diagnostics remain responsive; no error spam | Open |
| PERF-RUN-02 | 1 active download | No visible scheduler/UI overhead regression | Open |
| PERF-RUN-03 | Large queue (target 100+ downloads when practical) | Dashboard remains bounded to 1000 rows; refresh remains responsive/adaptive | Open |
| PERF-RUN-04 | Known Users with large history | No UI blocking; query remains bounded to 2000 peers / 2000 files per peer | Open |
| PERF-RUN-05 | Large Search 2 result/history set | Page 500, hard result bound 2000; filters/sort/export remain responsive | Open |
| PERF-RUN-06 | Large Library database | UI max 5000 rows; SQL hard cap 10000; filter debounce works | Open |
| PERF-RUN-07 | Writer queue load | Diagnostics: queued/peak/processed/dropped/errors remain understandable; no silent unbounded growth | Open |
| PERF-RUN-08 | Long-running session | Scheduler snapshots/history/telemetry do not show unbounded memory/data growth | Open |

## C. eD2K / server regression

| ID | Test | Expected | Status |
|---|---|---|---|
| ED2K-01 | Connect to an eD2K server | Existing server connection behavior unchanged | Open |
| ED2K-02 | Legacy server search | Results arrive in classic Search; Search 2 additions do not break legacy search | Open |
| ED2K-03 | Start a download from server-search result | Download starts through legacy DownloadQueue | Open |
| ED2K-04 | Source discovery / local server requests | Existing source discovery remains functional | Open |
| ED2K-05 | Pause and resume incomplete download | State and `.part.met` survive pause/resume | Open |
| ED2K-06 | Restart eMule with incomplete download | Incomplete file reloads and continues correctly | Open |

## D. Kad regression

| ID | Test | Expected | Status |
|---|---|---|---|
| KAD-01 | Connect/bootstrap Kad | Existing Kad state reaches connected/open/firewalled as appropriate | Open |
| KAD-02 | Legacy Kad search | Results arrive normally | Open |
| KAD-03 | Kad source discovery for active download | Sources are discovered through existing Kad route | Open |
| KAD-04 | Search 2 while Kad is active | Search 2 historical/live snapshot features do not create duplicate network searches/tabs | Open |

## E. Upload regression

| ID | Test | Expected | Status |
|---|---|---|---|
| UP-01 | Peer enters waiting queue | Existing upload queue behavior unchanged | Open |
| UP-02 | Upload starts | Data rate and slot handling remain normal | Open |
| UP-03 | Completed/aborted upload session | Transfer history/intelligence records outcome without blocking upload path | Open |

## F. Peer share / Known Users regression

| ID | Test | Expected | Status |
|---|---|---|---|
| PEER-01 | Manual View Shared Files | Classic manual tab opens and works | Open |
| PEER-02 | Automatic eligible peer discovery | Data stored without creating a legacy Search tab per peer | Open |
| PEER-03 | Denied share request | Denied/failure cooldown respected | Open |
| PEER-04 | Manual refresh after stale success TTL | Selected peer refreshes; privacy/failure cooldown is not bypassed | Open |
| PEER-05 | Duplicate usernames | Different userhash/endpoints remain separate | Open |
| PEER-06 | Delete intelligence history | Alias/favorite remain intact | Open |

## G. Smart Scheduler regression

Run the same representative download set in each mode.

| ID | Mode/test | Expected | Status |
|---|---|---|---|
| SCHED-01 | Analysis only | No scheduler/network behavior is changed; only analysis/telemetry | Open |
| SCHED-02 | Assist | Recommendations visible; no automatic source-discovery intervention | Open |
| SCHED-03 | Automatic | Only bounded, cooldown-protected enabled actions run | Open |
| SCHED-04 | A4AF comparison | Legacy eligibility/priorities remain authoritative; intelligence only influences permitted choice | Open |
| SCHED-05 | Rare-part selection | No invalid part selection; effect measurable in telemetry | Open |
| SCHED-06 | 30s/120s outcomes | Applied interventions receive bounded outcome samples | Open |

## H. Hashing / completion / recovery regression

| ID | Test | Expected | Status |
|---|---|---|---|
| HASH-01 | New completed download | Legacy eD2K hashing/completion succeeds | Open |
| HASH-02 | Recheck incomplete file | Existing hash/check path succeeds | Open |
| HASH-03 | Library Relink correct file | Accepted only when exact eD2K hash + size match | Open |
| HASH-04 | Library Relink wrong file | Rejected; original library identity unchanged | Open |
| HASH-05 | Download again from Library | Uses legacy DownloadQueue and duplicate guard | Open |

## I. UI / DPI regression

Test at Windows scaling 100%, 125%, 150%, 175% and 200%.

- Dashboard, Transfers, Known Users, Search 2, Library, Settings and Diagnostics.
- No clipped action buttons or overlapping controls at supported minimum window size.
- Ctrl+F / Ctrl+A / F5 / Enter behavior where implemented.
- Dark mode common controls remain readable.
- Last eMule Next workspace is restored correctly after restart.

## Acceptance rule

Preview 2 protocol/runtime hardening is complete only when the relevant rows above have been performed on an actual local build. Static gates prove architecture and compile contracts only; they must not be used to mark real server/Kad/upload/download behavior as tested.
