# eMule Next — living TODO

Dit bestand is de operationele werklijst voor de verdere ontwikkeling van eMule Next.

- **Projectplan / requirements:** `docs/EMULE_NEXT_PROJECT_PLAN.md`
- **Deze TODO:** concrete eerstvolgende werkzaamheden, prioriteiten en acceptatiechecks.
- Een taak is pas **DONE** als de code aanwezig is, de runtime-koppeling klopt en de relevante lokale runtime/buildtest is uitgevoerd.
- Iedere grotere tranche moet terug te voeren zijn op minimaal één requirement-ID uit het projectplan.

## Huidige bewezen basis

- Werkbranch: `goal-1-5`
- Laatst lokaal succesvol gebouwde head: `250f87f70029bd6cacb4cd10000206c50e7a442f`
- Release x64 lokale build: **geslaagd**, inclusief geïsoleerde activation-stage en verifier-keten.
- Dashboard/Transfers Intelligence 2.0 + Scheduler persistence: **build bevestigd; runtime-smoketest blijft open**.
- Known Users 2.0: **implementatie + completion gate gereed; eerstvolgende lokale buildtest**.
- Smart Scheduler default: **Analysis only**
- Protocolregel: legacy eD2K/Kad-logica blijft leidend.

## Statuslegenda

- `[ ]` nog doen
- `[~]` in uitvoering / gedeeltelijk aanwezig
- `[x]` functioneel geïmplementeerd; runtime-validatie kan nog als aparte taak volgen

---

# P0 — eerstvolgende tranche

## 1. Branch consolideren en regressiecheck
**Requirements:** CORE-01, CORE-02, CI-01

- [~] `goal-1-5` volledig vergelijken met `develop` en de tranche als samenhangende update consolideren.
- [x] Activator/verifier-keten uitgebreid met completion gates voor Dashboard/Transfers Intelligence 2.0 + Scheduler persistence en Known Users 2.0.
- [x] Lokale buildactivatie werkt via een staging-overlay zodat de echte repository-overlay niet wordt gemuteerd.
- [x] `build/activation-stage` blijft bij falen beschikbaar en wordt bij succes standaard verwijderd; `-KeepActivationStage` kan hem expliciet bewaren.
- [x] Intelligence 2.0 / Scheduler-completion head `250f87f70029bd6cacb4cd10000206c50e7a442f` lokaal Release x64 gebouwd.
- [ ] Known Users 2.0 head lokaal Release x64 bouwen.
- [ ] Runtime-smoketest uitvoeren.
- [ ] Daarna `goal-1-5` naar `develop` promoveren.

## 2. Dashboard & Transfers Intelligence 2.0
**Requirements:** INTEL-01, UI-01, UI-03, PERF-01

- [x] Dashboard, Transfers en Smart Scheduler gebruiken dezelfde canonical `CEmuleNextTransferInsights`-builder voor file-intelligence.
- [x] Bounded live source-quality sampling in `CEmuleNextTransferInsights`.
- [x] Persistente historische EWMA-rate beschikbaar voor scheduler/Dashboard/Transfers.
- [x] Scheduler action/applied/runtime persistence status zichtbaar.
- [x] Dashboardkolommen volledig sorteerbaar.
- [x] Kolombreedtes, sorteervolgorde en actieve filter persistent.
- [x] Extra filters: low health, scheduler intervention, A4AF opportunity.
- [x] `Last intervention` en `Last useful source` zichtbaar.
- [x] Historische snelheid, live snelheid en bronkwaliteit duidelijk naast elkaar.
- [x] Detailpaneel met strong/normal/weak/failed/transferring source-profiel.
- [x] Force analysis / reset intelligence per download.
- [x] Transfers-view gebruikt dezelfde intelligencevelden; oude dubbele file-signalberekening verwijderd.
- [x] Dashboard-refresh begrensd en adaptief: maximaal 1000 files per pass; refreshinterval vergroot wanneer rendering >250 ms duurt.
- [x] Lokale Release x64 build van deze implementatie bevestigd op `250f87f70029bd6cacb4cd10000206c50e7a442f`.
- [ ] Runtime-smoketest met kleine en grotere downloadqueue uitvoeren; pas daarna hoofdblok als volledig DONE beschouwen.

## 3. Scheduler/history persistentie afronden
**Requirements:** INTEL-01, DATA-01, PERF-01

- [x] Async `scheduler_file_history` persistence.
- [x] Async `scheduler_decisions` persistence.
- [x] Late A4AF/rare-part applied-state duurzaam corrigeren.
- [x] File hash als primaire telemetry-identiteit.
- [x] Bounded queues + drop diagnostics.
- [x] SQLite buiten scheduler/A4AF/part-ranking/UI hot paths.
- [x] Scheduler snapshots van verwijderde/voltooide downloads periodiek opruimen.
- [x] Interventietimestamps gesplitst in discovery / A4AF / rare-part; source-discovery cooldown wordt niet meer door andere acties onnodig geblokkeerd.
- [x] Anti-flapping voor A4AF en rare-part telemetry/interventies.
- [x] Interventieresultaten meten via baseline + 30 s + 120 s samples van snelheid/source-count.
- [x] Persistent telemetry query/read service voor diagnoseweergave; query-only en buiten de UI-thread.
- [x] Formele DATA-01 schema v2 voor `scheduler_file_history`, `scheduler_decisions` en `scheduler_outcomes`.
- [x] Upgradepad voor bestaande Preview-databases zonder `file_hash`.
- [x] Integrity/backup-smoketest dekt scheduler-tabellen en controleert teruglezen uit de backup.
- [x] Per-file intelligence reset verwijdert runtime snapshot en persisted history.
- [x] Completion gate `verify-intelligence-goal-complete.py` plus activator-audit bewaken de volledige implementatie.
- [x] Lokale Release x64 build bevestigd op `250f87f70029bd6cacb4cd10000206c50e7a442f`.
- [ ] Runtime-test in Analysis/Assist/Automatic uitvoeren en 30/120s outcome-registratie controleren.

## 4. Known Users 2.0
**Requirements:** PEER-01 t/m PEER-05, SESSION-01, PERF-01

- [x] Background user/file refresh.
- [x] Userhash als primaire live/historical match.
- [x] User- en filequery expliciet begrensd tot maximaal 2000 peers / 2000 files per peer.
- [x] Useraggregatie geoptimaliseerd; read-service gebruikt `PRAGMA query_only=ON`.
- [x] Zoekveld voor Known Users.
- [x] Filters: Current / History / Favorites / Recent 7d.
- [x] Sorteren op naam, first/last seen, file count, shared size, endpoint, browse-status en overige zichtbare kolommen.
- [x] Kolombreedtes, sortering, mode en zoektekst persistent.
- [x] First seen zichtbaar naast last seen.
- [x] Laatste endpoint/IP/TCP-poort en browse-status tonen.
- [x] Favorite/alias duidelijk in lijst/detail tonen en bewerkbaar maken.
- [x] Selected peer: first/last seen per file tonen.
- [x] Selected peer: current vs historical file state onderscheiden.
- [x] Restored View Shared Files-koppeling blijft primair userhash-gebaseerd met endpoint-disambiguatie voor dubbele namen.
- [x] Deterministische duplicate-username verifier bewijst dat gelijke usernames met verschillende hashes/endpoints niet worden samengevoegd.
- [x] Denied/timeout/unsupported/error/success-TTL/cooldown zichtbaar maken voor diagnose.
- [x] Handmatige refresh van één peer toegevoegd zonder globale scan en zonder denied/failure-cooldowns te omzeilen.
- [x] Lokale intelligence-history voor één peer asynchroon en gecontroleerd verwijderen; lokale alias/favorite blijven behouden.
- [x] `verify-known-users2.py` completion gate + activator-audit + algemene integratieverifier bewaken het hoofdstuk.
- [ ] Lokale Release x64 build van Known Users 2.0 bevestigen.
- [ ] Runtime: Current/History/Favorites/Recent + sort/filter/session-state controleren.
- [ ] Runtime: restored View Shared Files-tab op userhash-deduplicatie testen.
- [ ] Runtime: twee peers met dezelfde username en verschillende endpoints praktisch testen.
- [ ] Runtime: success, denied, timeout en cooldown-diagnose met echte peers controleren.
- [ ] Runtime: per-peer refresh en Delete history zonder UI-freeze/crash controleren.

## 5. Search 2.0
**Requirements:** SEARCH-01, PERF-01, UI-03

- [x] Historische search draait in background worker.
- [x] Search-resultaten zijn gepaged en begrensd.
- [x] Saved-search metadata refresh naar background worker verplaatst.
- [x] Saved-search save/delete en hash-block writes uit de UI-thread gehaald.
- [x] Missing/Favorites/Previously downloaded/block/saved-search basis aanwezig.
- [ ] Live eD2K/Kad-resultaten en historische resultaten duidelijk in één resultatenmodel combineren.
- [ ] Resultaatbron labelen: Live / Historical / Previously downloaded / Known peer.
- [ ] Filetype/extensiefilter toevoegen.
- [ ] Min/max size in UI aanbieden.
- [ ] Last-seen periodefilter toevoegen.
- [ ] Availability/source-count filters toevoegen.
- [ ] Sorteren op naam, size, peers, last seen, status.
- [ ] Saved-search UX uitbreiden met last run / new since last run.
- [ ] Bulkacties en contextmenu toevoegen.
- [ ] Export van geselecteerde/resultaatset toevoegen.
- [ ] Block rules beheer zichtbaar maken i.p.v. alleen hash-block actie.

## 6. Library 2.0
**Requirements:** LIB-01, SESSION-01, PERF-01, UI-03

- [x] History/Favorites/Completed/Missing/Download Later views aanwezig.
- [x] Background database-load.
- [x] Resultaatset begrensd.
- [x] Tekstfilter krijgt debounce zodat list-control niet per toetsaanslag volledig wordt herbouwd.
- [ ] Download Later kunnen verwijderen/togglen.
- [ ] `Download again` echte actie maken.
- [ ] `Recover/relink` voor missing completed file toevoegen.
- [ ] Local-path controle/verversing expliciet uitvoeren zonder UI-block.
- [ ] Status `available again` kunnen vastleggen en tonen.
- [ ] Hash-match gebruiken als eerder gedownload bestand opnieuw gevonden wordt.
- [ ] Sorteren en kolomstate persistent maken.
- [ ] Bulkacties/contextmenu toevoegen.
- [ ] Library-view/filter/textfilter na restart herstellen.

## 7. UI / DPI modernisering
**Requirements:** UI-01, UI-02, UI-03, UI-04

- [x] Gedeelde `EmuleNextUiMetrics` toegevoegd.
- [~] Dashboard, Settings, Search 2, Library en Known Users naar gedeelde DPI-metrics brengen; Known Users 2.0 gebruikt de gedeelde metrics nu voor zijn nieuwe layout.
- [ ] Alle nieuwe vaste pixelmaten in deze views verder elimineren waar schaalbaar layoutgedrag beter is.
- [ ] 100/125/150/175/200% DPI praktijktest uitvoeren.
- [ ] Resize/minimum-window tests uitvoeren.
- [ ] Dark mode consistent maken voor resterende common controls/contextmenus.
- [ ] Consistente spacing/headers/buttons/list styles toepassen.
- [ ] Hoofdnavigatie Search / Known Users / Library / Transfers / Settings verder moderniseren.
- [ ] Oude legacy toolbar/tab-visuele inconsistenties verminderen zonder protocol/UI routing te breken.
- [ ] Keyboard focus/Enter/contextmenu gedrag in alle Next-views gelijk trekken.
- [ ] Branding naar Preview 2 voorbereiden wanneer functionaliteit stabiel genoeg is.

---

# P1 — hardening vóór Preview 2

## Database en herstel
**Requirements:** DATA-01, SESSION-01

- [~] Formele schema-versioning/migrations: schedulerdeel staat nu op schema v2; volgende schemawijzigingen moeten dit patroon volgen.
- [ ] Automatische periodieke databasebackup ontwerpen/implementeren.
- [ ] Integrity check vanuit Settings/diagnostics beschikbaar maken.
- [ ] Herstelpad bij corrupte intelligence-database testen.
- [ ] Writer-queue en nieuwe persistence queues onder stress testen.
- [ ] Databasegrootte/pruning beleid documenteren en testen.

## Performance/stress
**Requirements:** PERF-01, PERF-02

- [ ] 0 downloads / 1 download / honderden downloads testen.
- [ ] 2000 Known Users + grote peer/file-history praktijktest.
- [ ] Grote peer-share met duizenden files testen.
- [ ] Grote Search/Library database testen.
- [ ] Memory growth van scheduler snapshots/history/telemetry controleren.
- [ ] UI-refresh timings meten en probleemgrenzen documenteren.
- [ ] ClientIndex/DownloadIndex fallbackpaden en stale entries testen.

## Protocolregressie
**Requirements:** CORE-02, PEER-02, INTEL-01

- [ ] ED2K server connect/download.
- [ ] Kad connect/search/source discovery.
- [ ] Upload naar legacy peers.
- [ ] Handmatige View Shared Files.
- [ ] Automatische shared-file discovery zonder extra legacy tabs.
- [ ] A4AF in Analysis/Assist/Automatic vergelijken.
- [ ] Rare-part selection Automatic testen.
- [ ] Pause/resume/restart van incomplete downloads.
- [ ] Hashing/checking/recovery regressie.

---

# P2 — Preview 2 productisering

**Requirements:** CORE-01, UI-04, CI-01

- [ ] Preview 2 versienummer/branding bepalen.
- [ ] Release notes genereren uit deze TODO + relevante commits.
- [ ] Portable ZIP maken/testen.
- [ ] Installerstrategie bepalen en bouwen.
- [ ] Upgrade van Preview 1/data/config naar Preview 2 testen.
- [ ] Clean install testen.
- [ ] Optioneel executable signing voorbereiden.
- [ ] Definitieve runtime-smoketestmatrix vastleggen.

---

# Beslisregels voor volgende `/goal`-rondes

1. Eerst deze TODO lezen en het projectplan erbij houden.
2. P0 gaat vóór P1/P2, tenzij een build/runtime-bug blokkeert.
3. Bij een grote tranche meerdere samenhangende taken tegelijk uitvoeren voordat opnieuw wordt gebouwd.
4. Geen backend-only checkbox als DONE wanneer de gebruiker het nog niet kan gebruiken/zien waar dat wel vereist is.
5. Nieuwe SQL mag niet in scheduler-, network- of GUI-hotpaths terechtkomen.
6. User identity blijft primair `userhash`; file identity blijft primair eD2K hash + size.
7. Nieuwe automatische schedulerfunctionaliteit blijft opt-in; Analysis only blijft veilige default.
8. Iedere succesvolle lokale build wordt bovenaan bij **Huidige bewezen basis** bijgewerkt voordat de volgende grote tranche start.
