# eMule Next — living TODO

Dit bestand is de operationele werklijst voor eMule Next.

- **Projectplan / requirements:** `docs/EMULE_NEXT_PROJECT_PLAN.md`
- **Runtime/stress/protocolmatrix:** `docs/EMULE_NEXT_RUNTIME_TEST_MATRIX.md`
- **Preview 2 release notes:** `docs/EMULE_NEXT_PREVIEW2_RELEASE_NOTES.md`
- Een functie is pas volledig DONE als implementatie, relevante lokale build en vereiste runtimevalidatie zijn uitgevoerd.
- Een compile/static gate is nooit vervanging voor een echte eD2K/Kad/runtimetest.

## Huidige bewezen basis

- Werkbranch: `goal-1-5`
- Laatst door gebruiker lokaal succesvol gebouwde head: `4294bd9983c3da0286e4e1736b61032fedf1621d`
- Release x64 build op die head: **geslaagd**, inclusief volledige Preview 2 activation/final-state gate.
- Runtimebevinding op `4294bd99…`: executable start en werkt, maar de zichtbare hoofdinterface bleef vrijwel de klassieke eMule-shell. Dit geldt als een **UI-acceptatiefout**, niet als buildfout.
- Performance / Stress / Protocol Regression 2.0: **build bevestigd; daadwerkelijke Diagnostics-self-test en netwerk-runtime matrix blijven open**.
- Database / Recovery / Diagnostics 2.0: **build bevestigd**.
- Search 2.0, Library 2.0 en Known Users 2.0: **implementatie + lokale builds bevestigd; runtimecases blijven open**.
- Smart Scheduler default: **Analysis only**.
- Legacy eD2K/Kad/search/download/upload-protocolcode blijft autoritatief.

## Statuslegenda

- `[ ]` nog doen / nog niet bewezen
- `[~]` implementatie aanwezig maar lokale build of runtimevalidatie voor deze tranche nog open
- `[x]` implementatie en relevante statische/buildstap bevestigd; eventuele runtimevalidatie staat apart vermeld

---

# P0 — Preview 2 producttranche

## 1. Preview 2 UI-architectuur
**Requirements:** UI-01, UI-02, UI-03, UI-04, SESSION-01

- [x] `eMule Next 0.2.0 Preview 2` als productidentiteit materialiseren en lokaal bouwen.
- [x] Gedeelde `CEmuleNextModernUi` toolkit toegevoegd voor DPI, fonts, surfaces, list styling en cards.
- [x] Segoe UI Variable gebruiken indien beschikbaar; Segoe UI fallback zonder fonts mee te leveren.
- [x] Permanente Preview 2 workspace-sidebar toegevoegd voor Search / Library / Known Users / Settings / Diagnostics binnen de bestaande Search-host.
- [x] Legacy eD2K/Kad Search-tabrouter blijft autoritatief; Preview 2 verandert geen protocol-searchengine.
- [x] Search, Library, Known Users, Dashboard en Transfers gebruiken dezelfde moderne list/header theming.
- [x] Known Users heeft geen aparte Dark-modeknop meer; appearance hoort centraal in Settings.
- [x] Preview 2 Release x64 compile bevestigd op `4294bd9983c3da0286e4e1736b61032fedf1621d`.
- [~] **Zichtbare moderne hoofd-shell** toegevoegd als late Preview2-laag: owner-drawn hoofdsidebar, Preview2-header, connectactie en nieuwe contentgeometrie; klassieke toolbar blijft technisch aanwezig maar wordt visueel niet meer primair. Nieuwe lokale build/runtimecheck open.
- [ ] Bij startup moet de nieuwe hoofdsidebar direct zichtbaar zijn; dit is de eerstvolgende UI-acceptatiecheck.
- [ ] 100/125/150/175/200% DPI praktijktest.
- [ ] Resize/minimum-window praktijktest.
- [ ] Light/Dark/System praktijktest over alle Preview 2 workspaces.

## 2. Settings herstructureren
**Requirements:** UI-01, UI-03, INTEL-01, PEER-02

- [x] Settings opgesplitst in `Appearance`, `Peer knowledge`, `Intelligence`, `Advanced` en compile-bewezen.
- [x] Appearance bevat alleen theme en zichtbare Smart ETA/Health-presentatie.
- [x] Peer knowledge bevat automatische shared-file knowledge + eenvoudige bounded concurrencykeuze.
- [x] Intelligence bevat Analysis / Assist / Automatic, profile en capability toggles.
- [x] Advanced toont scheduler tuning alleen na expliciete `Use custom scheduler tuning` keuze.
- [x] `Analysis only` blijft de aanbevolen/default veilige modus.
- [x] History cache en scheduler telemetry zijn geen normale gebruikersknoppen meer.
- [x] History/telemetry blijven intern bounded: history 4096 files, telemetry 256 events als productdefaults.
- [x] Runtime schedulerstatus, DB-maintenance en stressacties zijn uit Settings verwijderd en horen in Diagnostics.
- [ ] Next-specifieke settings waar mogelijk verder integreren in de normale hoofd-Settings/Preferences-ervaring; geen tweede verborgen instellingenwereld als eindproduct.
- [ ] Runtime controleren dat bestaande Preview 1 profielwaarden correct worden ingelezen en opgeslagen.

## 3. Diagnostics / runtime validation dashboard
**Requirements:** DATA-01, PERF-01, PERF-02, TEST-01, SUPPORT-01

- [x] Diagnostics omgebouwd naar cards voor Database, Writer queue, Scheduler en Performance en compile-bewezen.
- [x] Bestaande background acties behouden: integrity, backup, restore, prune, checkpoint en stress self-test.
- [x] Stress self-test blijft bounded: 10.000 ClientIndex, 5.000 DownloadIndex en 10.000 tijdelijke async writer-events.
- [x] Runtime-testmatrix geïntegreerd in Diagnostics.
- [x] Teststatus persistent: Not tested / PASS / FAIL; reset ondersteund.
- [x] Diagnostics rapport export toegevoegd met productversie, build-head, DB/writer/schedulerstatus, stressresultaat en runtime-teststatus.
- [ ] Diagnostics self-test daadwerkelijk uitvoeren op de lokaal gebouwde Preview 2 executable.
- [ ] Exportbestand praktisch controleren.

## 4. Preview 2 build/release-output
**Requirements:** CORE-01, RELEASE-01, CI-01

- [x] `build-local.ps1` produceert `artifacts/eMule-Next-0.2.0-Preview2-x64.exe`.
- [x] `eMule-Next-x64.exe` blijft latest alias.
- [x] Preview 2 build identity wordt apart van protocolversie gegenereerd.
- [x] Preview 2 final-state gate controleert de uiteindelijke materialized UI/productcode pas na de oude bewezen gates.
- [x] Release-layout verifier `verify-preview2-release.ps1` toegevoegd.
- [x] Preview 2 Release x64 build bevestigd op `4294bd9983c3da0286e4e1736b61032fedf1621d`.
- [ ] Nieuwe zichtbare-main-shell head lokaal Release x64 bouwen.
- [ ] SHA-256 van de uiteindelijke release-candidate executable vastleggen.

## 5. Portable Preview 2
**Requirements:** RELEASE-02, SESSION-01

- [x] `package-preview2.ps1` toegevoegd.
- [x] Output: `eMule-Next-0.2.0-Preview2-x64-portable.zip` + SHA-256 manifest.
- [x] Portable package bevat geen user config, intelligence DB, peer history of `.part/.part.met` data.
- [x] Release notes en runtime-testmatrix worden als documentatie meegenomen.
- [ ] Portable ZIP daadwerkelijk genereren na definitief groene Preview 2 UI-build.
- [ ] Clean-unpack/start praktijktest uitvoeren.
- [ ] Bestaande data/config-locatie bij portable gebruik praktisch bevestigen.

## 6. MSI installer
**Requirements:** RELEASE-03, SESSION-01

- [x] WiX MSI-definitie toegevoegd in `installer/preview2/Product.wxs`.
- [x] x64 per-machine installatie naar Program Files.
- [x] Start Menu shortcut standaard.
- [x] Desktop shortcut als expliciete buildvariant (`-DesktopShortcut`).
- [x] `MajorUpgrade` met stabiele UpgradeCode.
- [x] MSI bezit bewust geen AppData/config/intelligence/downloadstate directories.
- [x] `build-preview2-installer.ps1` toegevoegd; vereist lokale WiX CLI.
- [ ] MSI daadwerkelijk bouwen met geïnstalleerde WiX Toolset.
- [ ] Install/start/uninstall praktijktest.
- [ ] Upgrade Preview 1 -> Preview 2 praktijktest.
- [ ] Bevestigen dat uninstall/upgrade user data en incomplete downloads niet verwijdert.

---

# P1 — reeds geïmplementeerde kern, runtimevalidatie open

## Dashboard / Transfers Intelligence 2.0
**Requirements:** INTEL-01, UI-01, PERF-01

- [x] Eén canonical `CEmuleNextTransferInsights` model.
- [x] Bounded source-quality sampling, historische EWMA-rate en schedulerstatus.
- [x] Persistente Dashboard sort/filter/columns en bounded refresh.
- [ ] Runtime kleine/grote downloadqueue.

## Scheduler/history
**Requirements:** INTEL-01, DATA-01, PERF-01

- [x] Async history/decisions/outcomes persistence.
- [x] Action-specifieke cooldowns, anti-flapping en 30/120s outcome-metingen.
- [x] SQLite buiten scheduler/network/UI hotpaths.
- [ ] Analysis / Assist / Automatic met echte downloads vergelijken.

## Known Users 2.0
**Requirements:** PEER-01 t/m PEER-05, SESSION-01, PERF-01

- [x] Current / History / Favorites / Recent, search/sort/persistente state.
- [x] Userhash primair, endpoint-disambiguatie, bounded query-only reads.
- [x] Per-peer refresh en async Delete history met alias/favorite-behoud.
- [ ] Echte peer-runtimecases uitvoeren.

## Search 2.0
**Requirements:** SEARCH-01, PERF-01, UI-03

- [x] Live legacy snapshot + historical model, filters, sorting, saved searches, bulk/context/export/block rules.
- [x] Geen nieuwe network search engine; legacy eD2K/Kad blijft autoritatief.
- [ ] Search 2 en legacy Search parallel in runtime testen.

## Library 2.0
**Requirements:** LIB-01, SESSION-01, PERF-01, UI-03

- [x] History/Favorites/Completed/Missing/Download Later.
- [x] Download again via legacy queue, relink op exacte hash+size, available-again, bulk/context/export.
- [ ] Download-again/relink/missing/available-again runtime testen.

## Database / Recovery / Diagnostics 2.0
**Requirements:** DATA-01, SESSION-01, PERF-01

- [x] Schema v3, quick/full integrity, SQLite online backup, pre-migration backup, restore archive, WAL checkpoint, pruning en writerqueue diagnostics.
- [x] Corrupte intelligence DB blokkeert legacy eMule niet.
- [ ] Echte v2->v3 migration en restore-failure scenario praktijktesten.

## Performance / Stress / Protocol Regression 2.0
**Requirements:** PERF-01, PERF-02, CORE-02, TEST-01

- [x] Release x64 build bevestigd op `3a290ccc0f1c8c0831209d29bfac5aef88dc35f5`.
- [x] Deterministische indexstress + tijdelijke async writerstress aanwezig.
- [x] Statische protocol-contract gate bewaakt legacy Search/DownloadQueue/UploadQueue/A4AF/pause/hash APIs.
- [x] Runtime matrix als afzonderlijk bewijsdocument aanwezig.
- [ ] Stress self-test daadwerkelijk draaien.
- [ ] Volledige live runtime matrix uitvoeren.

---

# P2 — na groene zichtbare Preview 2 shell

## Runtime release-candidate validatie

- [ ] Start Preview 2 en bevestig dat de moderne hoofdsidebar/header direct bij startup zichtbaar zijn.
- [ ] Controleer Settings, Diagnostics, Dashboard en Search vanuit de nieuwe shell.
- [ ] Start Preview 2 met bestaande Preview 1 config/database/downloads.
- [ ] Controleer schema/backups/recovery status in Diagnostics.
- [ ] Voer stress self-test uit.
- [ ] Doorloop de runtime matrix en markeer resultaten in Diagnostics.
- [ ] Exporteer diagnostics rapport als releasebewijs.
- [ ] Genereer portable ZIP en test clean start.
- [ ] Bouw MSI en test clean install, upgrade en uninstall.
- [ ] Pas na bovenstaande runtimebewijzen Preview 2 als release-candidate markeren.
- [ ] Pas na expliciete toestemming `goal-1-5` naar `develop` promoveren.

---

# Beslisregels voor volgende `/goal`-rondes

1. Eerst deze TODO en het projectplan lezen.
2. Build-success is geen runtime/protocol-success; een visueel niet-herkenbare UI telt ook niet als UI-success.
3. Grote tranches samenhangend uitvoeren vóór een nieuwe lokale build.
4. Geen backend-only checkbox als DONE wanneer de gebruiker de functie nog niet kan gebruiken waar UI vereist is.
5. Geen nieuwe SQL in scheduler-, network- of GUI-hotpaths.
6. User identity blijft `userhash`; file identity blijft eD2K hash + size.
7. Automatische schedulerfunctionaliteit blijft opt-in; Analysis only blijft veilige default.
8. Iedere door gebruiker bevestigde succesvolle lokale build wordt bovenaan als bewezen basis vastgelegd.
9. Oude completion gates controleren hun bewezen productlaag; grote nieuwe UI-materialisatie komt daarna en krijgt één eigen final-state gate.
10. Verifiers controleren eindcontracten, geen fragiele toevallige functievolgorde of exacte pixelwaarden.
11. Installer/portable packaging mag user config, intelligence DB en incomplete-downloadstate niet als applicatiebestand bezitten of verwijderen.