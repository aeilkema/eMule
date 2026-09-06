# eMule Next — living TODO

Dit bestand is de operationele werklijst voor de verdere ontwikkeling van eMule Next.

- **Projectplan / requirements:** `docs/EMULE_NEXT_PROJECT_PLAN.md`
- **Runtime/stress/protocolmatrix:** `docs/EMULE_NEXT_RUNTIME_TEST_MATRIX.md`
- Een taak is pas volledig DONE als code, runtime-koppeling en relevante lokale runtime/buildtest zijn uitgevoerd.
- Iedere grotere tranche moet terug te voeren zijn op minimaal één requirement-ID uit het projectplan.

## Huidige bewezen basis

- Werkbranch: `goal-1-5`
- Laatst lokaal succesvol gebouwde head: `57b468ffcbb2934007d664e98b9b44cb50e673a2`
- Release x64 lokale build: **geslaagd**, inclusief geïsoleerde activation-stage en volledige verifier-keten.
- Dashboard/Transfers Intelligence 2.0 + Scheduler persistence: **build bevestigd; runtime-smoketest blijft open**.
- Known Users 2.0: **implementatie + completion gate + build bevestigd; runtime-smoketest blijft open**.
- Search 2.0: **grote producttranche + compile-contracts gebouwd; runtime-smoketest blijft open**.
- Library 2.0: **grote producttranche + recovery/download-again gebouwd; runtime-smoketest blijft open**.
- UI / Navigation Modernization 2.0: **build bevestigd op `fe4ec51186f6854f0f6a744883a0d19bba248c8e`; DPI/runtimepraktijktest blijft open**.
- Database / Recovery / Diagnostics 2.0: **build bevestigd op `57b468ffcbb2934007d664e98b9b44cb50e673a2`; runtime restore/migration/maintenance-tests blijven open**.
- Smart Scheduler default: **Analysis only**.
- Protocolregel: legacy eD2K/Kad/search/download/upload-logica blijft leidend.

## Statuslegenda

- `[ ]` nog doen
- `[~]` in uitvoering / gedeeltelijk aanwezig
- `[x]` functioneel geïmplementeerd; runtime-validatie kan nog als aparte taak volgen

---

# P0 — functionele tranches

## 1. Branch / buildbasis
**Requirements:** CORE-01, CORE-02, CI-01

- [x] Activation-stage is geïsoleerd van de echte checkout.
- [x] Activator/verifier-keten faalt vóór MSBuild bij bekende structurele contractproblemen.
- [x] Intelligence 2.0 / Scheduler buildbasis `250f87f70029bd6cacb4cd10000206c50e7a442f`.
- [x] Known Users 2.0 buildbasis `98f8272bd84a70f22da6a0ec1dad34af1c59bd75`.
- [x] Search 2.0 compile-contract buildbasis `af6f0070ad63d7f383cd8e9d84881b370ed9bf65`.
- [x] UI / Navigation Modernization 2.0 buildbasis `fe4ec51186f6854f0f6a744883a0d19bba248c8e`.
- [x] Database / Recovery / Diagnostics 2.0 buildbasis `57b468ffcbb2934007d664e98b9b44cb50e673a2`.
- [ ] Pas na expliciete toestemming `goal-1-5` naar `develop` promoveren.

## 2. Dashboard & Transfers Intelligence 2.0
**Requirements:** INTEL-01, UI-01, UI-03, PERF-01

- [x] Eén canonical `CEmuleNextTransferInsights`-model voor Dashboard, Transfers en Scheduler.
- [x] Bounded live source-quality sampling.
- [x] Persistente historische EWMA-rate.
- [x] Sorteerbare/persistente Dashboardkolommen en filters.
- [x] Last intervention / last useful source / source profile zichtbaar.
- [x] Force analysis / reset intelligence.
- [x] Dashboard maximaal 1000 files per refresh en adaptief refreshinterval.
- [ ] Runtime-smoketest kleine/grote downloadqueue.

## 3. Scheduler/history persistentie
**Requirements:** INTEL-01, DATA-01, PERF-01

- [x] Async scheduler history/decisions/outcomes persistence.
- [x] Action-specifieke cooldowns en anti-flapping.
- [x] 30s/120s outcome-metingen.
- [x] Query-only diagnostics reader.
- [x] DATA-01 scheduler schema-v2 migratie blijft onder huidig totaal-schema v3 behouden.
- [x] SQLite blijft buiten scheduler/network/UI hotpaths.
- [ ] Runtime Analysis / Assist / Automatic vergelijken.
- [ ] 30s/120s outcomes met echte downloads controleren.

## 4. Known Users 2.0
**Requirements:** PEER-01 t/m PEER-05, SESSION-01, PERF-01

- [x] Current / History / Favorites / Recent 7d.
- [x] Search/sort/persistente viewstate.
- [x] Userhash primaire identiteit; endpoint-disambiguatie voor dubbele namen.
- [x] First/last seen, endpoint, browse-status en selected-peer file-history.
- [x] Per-peer refresh met privacy/failure cooldowns.
- [x] Async Delete history zonder alias/favorite te verwijderen.
- [x] Bounded query-only reads: maximaal 2000 peers / 2000 files per peer.
- [ ] Echte peer-runtimecases uit runtime-matrix uitvoeren.

## 5. Search 2.0
**Requirements:** SEARCH-01, PERF-01, UI-03

- [x] Historische background search en bounded paging.
- [x] Live legacy result snapshot + historical rows gecombineerd op eD2K hash + size.
- [x] Bronlabels Live eD2K / Live Kad / Historical / Previously downloaded / Known peer.
- [x] Extension, size, last-seen, peers en statusfilters.
- [x] Sortering, saved-search last-run/new-since-last-run.
- [x] Bulkacties/contextmenu/CSV-export.
- [x] Zichtbaar block-rule beheer.
- [x] Geen nieuwe network search engine; legacy eD2K/Kad blijft autoritatief.
- [ ] Runtime Search 2 + legacy Search parallel testen.

## 6. Library 2.0
**Requirements:** LIB-01, SESSION-01, PERF-01, UI-03

- [x] History / Favorites / Completed / Missing / Download Later.
- [x] Background database-load en bounded resultaten.
- [x] Debounced tekstfilter.
- [x] Download Later add/remove/toggle.
- [x] Download again via legacy DownloadQueue + duplicate guard.
- [x] Recover/relink met exacte eD2K hash + size verificatie in worker.
- [x] Missing/available-again model en Search/history rediscovery.
- [x] Sortering/kolommen/view/filter persistent.
- [x] Multi-select bulkacties/contextmenu/CSV-export.
- [ ] Runtime download-again/relink/missing/available-again testen.

## 7. UI / Navigation Modernization 2.0
**Requirements:** UI-01, UI-02, UI-03, UI-04, SESSION-01

- [x] Gedeelde workspace spacing/action-height/list styling.
- [x] DPI-aware Next-layouts en permanente tab-padding.
- [x] Dark-mode list styling voor Next-workspaces.
- [x] Laatst gebruikte Next-workspace persistent herstellen.
- [x] Search/Library/Known Users/Settings/Dashboard keyboardcontracten gelijkgetrokken waar toepasselijk.
- [x] Dashboard en Next-workspaces visueel geharmoniseerd zonder protocolrouting te wijzigen.
- [ ] 100/125/150/175/200% praktische DPI-test.
- [ ] Resize/minimum-window praktijktest.
- [ ] Resterende legacy dialogs/contextmenus visueel nalopen.

---

# P1 — hardening vóór Preview 2

## Database / Recovery / Diagnostics 2.0
**Requirements:** DATA-01, SESSION-01, PERF-01

- [x] Totaal database-schema v3 met maintenance metadata.
- [x] `quick_check` vóór openen van bestaande DB.
- [x] Gevalideerde SQLite online backup vóór migratie.
- [x] Automatische backup bij ouder dan 24 uur; maximaal 5 geroteerde backups.
- [x] Handmatige full `integrity_check`.
- [x] Corrupte intelligence-DB blokkeert legacy eMule niet; recovery-required status.
- [x] Restore valideert backup, archiveert huidige DB, restoreert en valideert opnieuw.
- [x] 90-dagen pruning alleen voor oude telemetry/outcomes/mislukte transfers; favorites/aliases/library-history beschermd.
- [x] Writerqueue queued/peak/processed/dropped/errors diagnostics.
- [x] Diagnostics-workspace met backup/restore/integrity/prune/checkpoint.
- [ ] Runtime migratie van bestaande v2 DB controleren.
- [ ] Restore-failure/recovery scenario praktisch testen.

## Performance / Stress / Protocol Regression 2.0
**Requirements:** PERF-01, PERF-02, CORE-02, PEER-02, INTEL-01

- [~] Grote tranche in uitvoering op huidige branch na bewezen DB2-head.
- [x] Deterministische in-memory `ClientIndex`/`DownloadIndex` stress self-test toegevoegd.
- [x] Stress-test begrensd: maximaal 20.000 clients / 10.000 downloads; UI-actie gebruikt 10.000 / 5.000.
- [x] Hash/TCP/UDP/Kad lookup, update en unregister worden door de self-test geverifieerd.
- [x] Stress-test draait via Diagnostics background worker en raakt netwerk/SQLite/scheduler niet.
- [x] Statische protocol-contract gate bewaakt legacy Search, DownloadQueue, UploadQueue, A4AF, pause/resume en hashing APIs.
- [x] Runtime/stress/protocolmatrix vastgelegd in `docs/EMULE_NEXT_RUNTIME_TEST_MATRIX.md`.
- [ ] Lokale Release x64 build van deze tranche bevestigen.
- [ ] Diagnostics index-stresstest werkelijk uitvoeren.
- [ ] Echte eD2K/Kad/upload/download/runtime matrix uitvoeren; statische gates tellen hiervoor niet als bewijs.

---

# P2 — Preview 2 productisering

**Requirements:** CORE-01, UI-04, CI-01

- [ ] Preview 2 versienummer/branding bepalen.
- [ ] Release notes genereren uit TODO + relevante commits.
- [ ] Portable ZIP maken/testen.
- [ ] Installerstrategie bepalen en bouwen.
- [ ] Upgrade van Preview 1/data/config naar Preview 2 testen.
- [ ] Clean install testen.
- [ ] Optioneel executable signing voorbereiden.
- [ ] Definitieve runtime-smoketestmatrix uitvoeren en afsluiten.

---

# Beslisregels voor volgende `/goal`-rondes

1. Eerst deze TODO lezen en het projectplan erbij houden.
2. Een build-success is geen runtime/protocol-success.
3. Bij een grote tranche meerdere samenhangende taken tegelijk uitvoeren voordat opnieuw wordt gebouwd.
4. Geen backend-only checkbox als DONE wanneer de gebruiker het nog niet kan gebruiken/zien waar dat vereist is.
5. Nieuwe SQL mag niet in scheduler-, network- of GUI-hotpaths terechtkomen.
6. User identity blijft primair `userhash`; file identity blijft primair eD2K hash + size.
7. Nieuwe automatische schedulerfunctionaliteit blijft opt-in; Analysis only blijft veilige default.
8. Iedere succesvolle lokale build wordt bovenaan bij **Huidige bewezen basis** bijgewerkt voordat de volgende grote tranche start.
9. Verifiers moeten de uiteindelijke materialized eindtoestand bewaken en geen fragiele functievolgorde/multiline tussenankers vereisen.
