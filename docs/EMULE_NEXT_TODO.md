# eMule Next — living TODO

Dit bestand is de operationele werklijst voor eMule Next.

- **Projectplan / requirements:** `docs/EMULE_NEXT_PROJECT_PLAN.md`
- **Runtime/stress/protocolmatrix:** `docs/EMULE_NEXT_RUNTIME_TEST_MATRIX.md`
- **Preview 2 release notes:** `docs/EMULE_NEXT_PREVIEW2_RELEASE_NOTES.md`
- Een functie is pas volledig DONE als implementatie, relevante lokale build en vereiste runtimevalidatie zijn uitgevoerd.
- Een compile/static gate is nooit vervanging voor een echte eD2K/Kad/runtimetest.

## Huidige bewezen basis

- Werkbranch: `goal-1-5`
- Laatst door gebruiker lokaal succesvol gebouwde én visueel bevestigde head: `5049c3a69a1b14911daad6bfa5e9d173d2e9554a`.
- Op die head: Release x64 build geslaagd en de nieuwe Preview 2 hoofdsidebar/header is bij startup daadwerkelijk zichtbaar.
- Vorige head `4294bd9983c3da0286e4e1736b61032fedf1621d` compileerde wel maar faalde UI-acceptatie omdat de klassieke hoofd-shell nog dominant zichtbaar was. Dit blijft als regressiereferentie gedocumenteerd.
- Database / Recovery / Diagnostics 2.0: build bevestigd; failure-mode runtimecases blijven open.
- Performance / Stress / Protocol Regression 2.0: build bevestigd; daadwerkelijke Diagnostics-self-test en live netwerk-runtime matrix blijven open.
- Search 2.0, Library 2.0 en Known Users 2.0: implementatie + lokale builds bevestigd; runtimecases blijven open.
- Smart Scheduler default: **Analysis only**.
- Legacy eD2K/Kad/search/download/upload-protocolcode blijft autoritatief.

## Statuslegenda

- `[ ]` nog doen / nog niet bewezen
- `[~]` implementatie aanwezig maar nieuwe lokale build of runtimevalidatie voor deze tranche open
- `[x]` implementatie en relevante statische/buildstap bevestigd; eventuele runtimevalidatie staat apart vermeld

---

# P0 — Preview 2 UX Completion & Release Candidate

## 1. Single coherent application shell
**Requirements:** UI-01, UI-05, UX-01, SESSION-01

- [x] Direct zichtbare Preview 2 hoofdsidebar/header op `5049c3a...` runtime bevestigd.
- [x] Klassieke toolbar blijft technisch beschikbaar voor command compatibility maar is niet langer primaire chrome.
- [~] Library naar primaire hoofdsidebar promoveren zonder duplicatie van Library-logica.
- [~] Known Users naar primaire hoofdsidebar promoveren zonder duplicatie van peerlogica.
- [~] Moderne Settings naar primaire hoofdsidebar routeren in plaats van direct de klassieke Preferences-sheet te openen.
- [~] Diagnostics naar primaire hoofdsidebar promoveren.
- [~] Search-host krijgt één smalle publieke router voor permanente Next-workspaces; legacy handmatige Search/View Shared Files tabs blijven autoritatief.
- [~] Interne Next-sidebar wordt bij directe hoofdnav-routes verborgen; permanente workspace krijgt volledige contentbreedte.
- [~] Hoofdnav bewaart alleen gewone werkruimtes voor startup; Settings/Diagnostics worden niet automatisch als startupscherm vastgezet.
- [ ] Nieuwe UX-completion head lokaal Release x64 bouwen.
- [ ] Runtime hoofdnav testen: Dashboard / Transfers / Search / Library / Shared Files / Known Users / Messages / Servers / Kad / Statistics / Settings / Diagnostics / IRC.

## 2. Header/status
**Requirements:** UI-01, UI-03, UX-01

- [x] Preview 2 productheader en sectietitel zichtbaar op bewezen shell-build.
- [~] Live headerstatus toegevoegd bovenop bestaande eMule refreshpaden: connection state + actuele transfer rate; geen extra pollingtimer.
- [~] Connect/Disconnect-actie blijft rechtstreeks de bestaande `OnBnClickedConnect`-route gebruiken.
- [ ] Runtime controleren dat headerstatus tijdens connect/disconnect en actieve transfers bijwerkt.
- [ ] Narrow-window gedrag controleren zodat status/header niet overlappen.

## 3. Settings als één ingang
**Requirements:** UI-05, UX-01, UI-02, INTEL-01, PEER-02

- [x] Next Settings opgesplitst in Appearance / Peer knowledge / Intelligence / Advanced.
- [x] Analysis only blijft default en Automatic blijft expliciete opt-in.
- [x] History/telemetry capacities zijn interne bounded defaults, niet normale gebruikerscontrols.
- [x] Diagnostics/DB/stresscontrols zitten niet in Settings.
- [~] Hoofdsidebar `Settings` opent nu de moderne Settings-workspace.
- [~] `Classic eMule settings...` toegevoegd binnen dezelfde Settings-ingang voor Connection, Directories en overige upstream Preferences.
- [ ] Runtime controleren dat classic Preferences correct opent en terugkeer naar moderne shell geen layout/routing verstoort.
- [ ] Bestaande Preview 1 profielwaarden inlezen/opslaan testen.

## 4. Dashboard / Transfers UX
**Requirements:** UI-01, UX-01, INTEL-01, PERF-01

- [x] Canonical `CEmuleNextTransferInsights` model en Dashboard Intelligence 2.0 gebouwd.
- [x] Dashboard is via de hoofdsidebar het primaire overzicht.
- [x] Transfers blijft de autoritatieve werkweergave voor downloads/sources.
- [~] Dashboard progressive complexity geïmplementeerd: primaire filters `All / Attention / Stalled / No sources / Active` blijven zichtbaar.
- [~] Primaire Dashboard-acties `Open Transfers / Open Sources / Pause-Resume / Refresh / More...` blijven zichtbaar.
- [~] Rare/Low health/Intervention/A4AF filters en priority/force/reset acties blijven bereikbaar via `More...` in plaats van permanente knopwand.
- [~] Dashboard summary verkort naar dagelijkse status (downloads/active/attention/down/uploads/scheduler); refresh-timing en specialistische counters domineren niet meer.
- [ ] Dashboard met kleine, middelgrote en grote downloadqueue runtime testen.
- [ ] Controleren dat Dashboard → Transfers en Dashboard → Sources selectie correct focust.
- [ ] `More...` filter- en actiehandlers runtime controleren; power-userfunctionaliteit moet volledig behouden blijven.

## 5. Search / Library / Known Users UX
**Requirements:** UI-05, UX-01, SEARCH-01, LIB-01, PEER-03

- [~] Hoofdsidebar `Search` opent Search 2 als moderne standaardworkspace.
- [~] Search 2 krijgt `Network search...` naast de zoekbalk; deze route opent de bestaande legacy eD2K/Kad Search-parameters/resulttabs en bouwt geen tweede netwerkengine.
- [~] Library en Known Users rechtstreeks vanuit hoofdsidebar bereikbaar via Search-host router.
- [~] Interne Next-sidebar niet langer nodig voor normale hoofdnav-route.
- [x] Search 2/Library/Known Users gebruiken gedeelde ModernUi list/header styling.
- [x] Legacy Search blijft de netwerksearchengine; Search 2 introduceert geen tweede eD2K/Kad searchengine.
- [ ] Hoofdnav Search → Search 2 → Network search... → legacy Search parameters/resulttabs runtime testen.
- [ ] View Shared Files tab testen terwijl Library/Known Users via hoofdsidebar gebruikt worden.
- [ ] Library Download again/relink/missing/available-again runtime testen.
- [ ] Known Users duplicate-name/userhash/alias/favorite/delete-history runtime testen.

## 6. Diagnostics / support
**Requirements:** DATA-01, PERF-02, TEST-01, SUPPORT-01

- [x] Diagnostics cards voor Database, Writer queue, Scheduler en Performance.
- [x] Background integrity/backup/restore/prune/checkpoint/stressacties.
- [x] Bounded self-test: ClientIndex 10k, DownloadIndex 5k, tijdelijke writerqueue 10k.
- [x] Persistente runtime-testmatrix met Not tested/PASS/FAIL/reset.
- [x] Diagnostics rapport export met version/build/DB/queue/scheduler/self-test/runtimestatus.
- [~] Veilige `create-preview2-support-bundle.ps1` toegevoegd: Diagnostics-report + build/hash + publieke docs; expliciet geen DB/config/peerhistory/.part-data.
- [~] Support helper wordt in portable package meegenomen.
- [ ] Stress self-test werkelijk uitvoeren en PASS vastleggen.
- [ ] Diagnostics report exporteren en support-bundle ZIP praktisch openen/controleren.

## 7. Theme / DPI / responsive polish
**Requirements:** UI-02, UI-03, UX-01

- [x] System/Light/Dark centraal in moderne Settings.
- [x] Segoe UI Variable met Segoe UI fallback.
- [x] Gedeelde ModernUi DPI metrics, cards, navigation en list styling.
- [ ] System/Light/Dark runtime over alle primaire workspaces.
- [ ] DPI 100/125/150/175/200%.
- [ ] Resize/minimum-window matrix.
- [ ] Sidebar/header overlap en owner-draw states bij high-DPI.

## 8. Build / gates
**Requirements:** CORE-01, CI-01, UI-05

- [x] Clean activation-stage + final-state gates blijven basis.
- [~] `activate-preview2-ux-completion.py` toegevoegd na visible-main-shell materialization.
- [~] `activate-preview2-search-ux.py` maakt Search 2 primair en bewaart legacy netwerksearch via een expliciete brug.
- [~] `activate-preview2-header-status.py` toegevoegd zonder backendlogica te dupliceren.
- [~] `activate-preview2-dashboard-ux.py` toegevoegd na bestaande Dashboard materialization; gebruikt alleen bestaande handlers/filters.
- [~] `verify-preview2-ux-completion.py` controleert primaire routes, Search-bridge, live header, Dashboard progressive complexity, Settings/Diagnostics-scheiding en verbiedt backendlogica in shell.
- [~] Preview2 orchestrator voert UX-completion + Search UX + Dashboard UX + live-header + UX-gate als late productlaag uit.
- [~] Release/support privacychecks zijn regelgebonden en vermijden brede multiline wildcard-false-positives.
- [ ] Nieuwe head lokaal Release x64 bouwen.
- [ ] Bij buildfout eerst volledige nieuwe Preview2-laag/gates als één foutgroep nalopen vóór nieuwe buildvraag.

## 9. Portable / MSI / RC artifacts
**Requirements:** RELEASE-01, RELEASE-02, RELEASE-03, SUPPORT-01

- [x] Preview2 executable naam en latest alias aanwezig.
- [x] Portable script + SHA256 manifest aanwezig.
- [x] WiX MSI + MajorUpgrade + Start Menu + optionele Desktop shortcut aanwezig.
- [~] Portable package bevat nu ook alleen de veilige support-bundle helper; nog steeds geen user state.
- [~] `finalize-preview2-rc.ps1` toegevoegd: release-layoutcheck → portable → optionele MSI → RC hashmanifest.
- [ ] Definitieve UX-build executable SHA256 vastleggen.
- [ ] `finalize-preview2-rc.ps1` uitvoeren na runtime acceptance.
- [ ] Portable clean-unpack/start test.
- [ ] MSI clean install / Preview1 upgrade / uninstall test.
- [ ] Bevestigen dat user config, intelligence DB en incomplete downloads behouden blijven.

---

# P1 — bewezen kern, runtimevalidatie open

## Smart Scheduler/history
- [x] Async decisions/outcomes/history persistence.
- [x] Cooldowns, anti-flapping, bounded outcome-metingen.
- [x] Geen SQLite in scheduler/network/UI hotpaths.
- [ ] Analysis / Assist / Automatic met echte downloads vergelijken.

## Database / Recovery
- [x] Schema v3, integrity, online backup, pre-migration backup, archive-before-restore, WAL checkpoint, pruning.
- [x] Intelligence failure blokkeert legacy core niet.
- [ ] Echte v2→v3 migration.
- [ ] Restore success/failure op disposable kopie.
- [ ] Abnormale process-stop + WAL recovery.

## Protocol/runtime
- [x] Statische contractgate voor legacy Search/DownloadQueue/UploadQueue/A4AF/pause/hash.
- [ ] eD2K server connect/search/download/reconnect.
- [ ] Kad bootstrap/search/source lookup/restart.
- [ ] Upload/queue/history.
- [ ] Pause/resume/restart/.part.met/hash/completion.
- [ ] A4AF en rare-parts.
- [ ] View Shared Files accepted/denied/cooldown/background knowledge.

---

# P2 — Preview 2 release-candidate acceptance

1. [ ] Build nieuwe UX-completion head met `build-local.ps1 -KeepActivationStage`.
2. [ ] Startup: moderne hoofdsidebar/header direct zichtbaar.
3. [ ] Alle primaire hoofdnav-routes doorlopen.
4. [ ] Search → Search 2 → Network search... bridge testen.
5. [ ] Settings → Classic eMule settings bridge testen.
6. [ ] Live header connection/rates testen.
7. [ ] Dashboard primary/More UX controleren.
8. [ ] Diagnostics self-test PASS.
9. [ ] Light/Dark/System + DPI 100–200% + resize.
10. [ ] Preview1 config/database/downloadstate upgrade behouden.
11. [ ] Disposable corruption/recoverytest.
12. [ ] Volledige live eD2K/Kad/upload/download/A4AF/shared-files matrix.
13. [ ] Diagnostics report + support bundle.
14. [ ] Portable clean-unpack/start.
15. [ ] MSI install/upgrade/uninstall.
16. [ ] `finalize-preview2-rc.ps1` en definitieve hashes.
17. [ ] Alleen daarna status **Preview 2 Release Candidate**.
18. [ ] `goal-1-5` nooit zonder expliciete toestemming naar `develop` promoveren.

---

# Beslisregels voor volgende `/goal`-rondes

1. Eerst TODO en projectplan lezen.
2. Build-success, UI-success en protocol/runtime-success zijn drie afzonderlijke bewijzen.
3. Een primaire functie hoort in de primaire shell; geen verborgen Search-tab als eindnavigatie.
4. Progressive complexity: dagelijkse acties direct, specialistische acties beschikbaar maar niet dominant.
5. Geen tweede netwerk/search/downloadengine bouwen voor UI-gemak.
6. Geen nieuwe SQLite/filesystem/heavy work in GUI/network/scheduler hotpaths.
7. User identity blijft userhash; file identity blijft eD2K hash + size.
8. Automatic scheduler blijft opt-in; Analysis only veilige default.
9. Verifiers controleren eindcontracten, geen toevallige pixelwaarden of fragiele tekstvolgorde.
10. Packaging/installer bezit of verwijdert geen user config, intelligence DB, peer history of incomplete downloads.
11. Iedere door gebruiker bevestigde build/runtimebevinding wordt meteen hier als bewezen basis vastgelegd.
