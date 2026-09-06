# eMule Next — living TODO

Dit bestand is de operationele status voor eMule Next Preview 2.

- **Projectplan / requirements:** `docs/EMULE_NEXT_PROJECT_PLAN.md`
- **Runtime/stress/protocolmatrix:** `docs/EMULE_NEXT_RUNTIME_TEST_MATRIX.md`
- **Preview 2 release notes:** `docs/EMULE_NEXT_PREVIEW2_RELEASE_NOTES.md`
- **Build-gebonden runtime acceptance:** `preview2-runtime-acceptance.ps1`
- Een functie is pas volledig DONE als implementatie, relevante lokale build en vereiste runtimevalidatie zijn uitgevoerd.
- Een compile/static gate is nooit vervanging voor een echte eD2K/Kad/runtimetest.

## Huidige bewezen basis

- Werkbranch: `goal-1-5`.
- Laatst door gebruiker lokaal succesvol **FullRebuild** gebouwde head: `7a8844a7d329fc5a8bd787f62b209763f73fe9a6`.
- Release x64 op die head: **0 compilerwarnings, 0 linkerwarnings, 0 errors**.
- Compiler én linker gebruiken warnings-as-errors; `/WX` is voortaan onderdeel van het Release-contract.
- De moderne Preview 2 hoofdsidebar/header is eerder ook daadwerkelijk visueel bevestigd.
- Complete Settings-shell: 4 eMule Next categorieën + alle 15 originele eMule Preferences-pagina's.
- Theme coverage omvat primaire legacy workspaces en specifieke Messages/Chat dark-modebehandeling.
- Smart Scheduler default blijft **Analysis only**; Automatic blijft expliciete opt-in.
- Legacy eD2K/Kad/search/download/upload-protocolcode blijft autoritatief.
- `develop` blijft onaangeroerd totdat expliciet toestemming voor promotie wordt gegeven.

## Statuslegenda

- `[ ]` runtime/packagebewijs nog open
- `[x]` implementatie + vereiste build/static bewijs bevestigd

---

# P0 — Preview 2 product/build completion

## Shell / navigatie

- [x] Moderne hoofdsidebar/header direct zichtbaar gemaakt.
- [x] Dashboard, Transfers, Search, Library, Shared Files, Known Users, Messages, Servers, Kad, Statistics, Settings, Diagnostics en IRC als primaire routes gematerialiseerd.
- [x] Search-host is implementation detail; directe hoofdnav-routes gebruiken een smalle router.
- [x] Search opent Search 2 als standaardworkspace.
- [x] `Network search...` herstelt de bestaande legacy eD2K/Kad Search-parameters/resulttabs; geen tweede netwerkengine.
- [x] Library en Known Users direct via hoofdsidebar.
- [x] Settings en Diagnostics direct via hoofdsidebar.
- [x] Hoofdnav bewaart normale workspaces; Settings/Diagnostics niet als automatische startup-last-view.

## Settings

- [x] eMule Next: Appearance / Peer knowledge / Intelligence / Advanced.
- [x] Alle 15 originele Preferences-pagina's aanwezig: General, Display, Connection, Proxy, Server, Directories, Files, Notifications, Statistics, IRC, Messages, Security, Scheduler, Web Server, Tweaks.
- [x] Originele pages blijven autoritatief; geen tweede opslagmodel.
- [x] Directe page-routing via bestaande `ShowPreferences(pageID)`.
- [x] Settings-navigatie bruikbaar gemaakt voor kleinere vensters/hoge DPI.

## Theme / UX

- [x] System / Light / Dark centraal.
- [x] Centrale theme-routing over primaire legacy workspaces.
- [x] Messages/Chat krijgt aanvullende RichEdit/list/control dark-modebehandeling.
- [x] Theme Apply werkt over de volledige hoofdwindow-tree.
- [x] Dashboard progressive complexity: primaire filters/actions + `More...` voor specialistische functies.
- [x] Live headerstatus gebruikt bestaande connection/rate-refreshpaden; geen extra pollingtimer.

## Search / Library / Known Users

- [x] Search 2 unified history/live presentation, filters, saved searches, favorites, download later, export en block rules.
- [x] Library history/favorites/completed/missing/download-later/relink/download-again/available-again.
- [x] Known Users userhash-first identity, alias/favorite/history/shared-files kennis.
- [x] Geen SQLite I/O in GUI/network/scheduler hotpaths.

## Diagnostics / recovery / performance

- [x] Database integrity, backup, restore, prune, checkpoint en backupfolderacties.
- [x] Bounded self-test: ClientIndex 10.000, DownloadIndex 5.000, writer queue 10.000.
- [x] Diagnostics-report en privacy-bounded support-bundle tooling.
- [x] Database schema v3 / recovery / queue diagnostics aanwezig.

## Buildkwaliteit

- [x] Clean isolated activation-stage.
- [x] Repository-preflight vóór stage creation.
- [x] Structurele activation-chain gates; geen fragiele variabele/whitespacechecks.
- [x] Overlay-verifiers eisen uitsluitend overlay-bestanden.
- [x] Shared legacy translation units worden alleen in Preview2-eigen regions gecontroleerd.
- [x] C4191 beperkt tot echte actieve MFC message-map macroblocks; commentaar wordt niet gemuteerd.
- [x] x64 pointer/handle truncaties uit de volledige Release-build opgelost.
- [x] Eigen `CWnd::Create` hiding systematisch gehard.
- [x] Release LTCG expliciet.
- [x] Compiler warnings-as-errors.
- [x] Linker warnings-as-errors.
- [x] FullRebuild op `7a8844a...`: **0 warnings / 0 errors**.

---

# P1 — Runtime acceptance

Alle onderstaande punten worden build-gebonden geregistreerd in `artifacts/preview2-runtime-acceptance.json` via `preview2-runtime-acceptance.ps1`. Het record bevat Git HEAD + SHA256 van de exacte executable; resultaten van een andere binary worden geweigerd.

## Core runtime — vereist vóór RC-finalization

- [ ] `UI-STARTUP` — moderne Preview 2 shell/sidebar/header bij startup.
- [ ] `UI-NAV` — alle 13 primaire routes correct.
- [ ] `UI-SEARCH-BRIDGE` — Search 2 → Network search... → legacy eD2K/Kad Search.
- [ ] `UI-SETTINGS` — 19 categorieën; originele pages openen correct.
- [ ] `UI-HEADER` — connection state/rates live.
- [ ] `UI-DASHBOARD` — primary filters/actions/More.
- [ ] `THEME-DARK` — geen grote witte primary surfaces, inclusief Messages/Chat.
- [ ] `THEME-SWITCH` — Dark → Light → System → Dark zonder restart.
- [ ] `DPI-MATRIX` — 100/125/150/200% + resize.
- [ ] `DIAG-STRESS` — 10k/5k/10k self-test PASS.
- [ ] `DIAG-DB` — integrity/backup/checkpoint PASS.
- [ ] `ED2K` — connect/search/download/pause-resume/reconnect.
- [ ] `KAD` — bootstrap/connect/search/source lookup/restart.
- [ ] `UPLOAD` — upload/queue/history.
- [ ] `INTELLIGENCE` — source intelligence/Smart ETA/A4AF/rare parts/Scheduler Analysis+Assist.
- [ ] `KNOWN-USERS` — userhash/alias/favorite/delete-history/shared-files cooldown.
- [ ] `LIBRARY` — download again/relink/missing/available again.
- [ ] `PERSISTENCE` — restart behoudt downloads/settings/library/metadata/DB.
- [ ] `RECOVERY` — disposable corruption/restore/abnormal-stop recovery.
- [ ] `SUPPORT` — diagnostics report + support bundle, zonder private user state.

`finalize-preview2-rc.ps1` voert verplicht `preview2-runtime-acceptance.ps1 -VerifyCore` uit en weigert RC-artifacts zolang één core-check niet PASS is.

---

# P2 — Package acceptance

Na core runtime PASS:

- [ ] `PORTABLE` — clean unpack/start.
- [ ] `MSI-INSTALL` — clean install + launch.
- [ ] `MSI-UPGRADE` — upgrade behoudt config, intelligence DB en incomplete downloads.
- [ ] `MSI-UNINSTALL` — program files weg, user state behouden.
- [ ] `preview2-runtime-acceptance.ps1 -VerifyAll` volledig PASS.

RC-manifest bevat Git HEAD, EXE/ZIP/MSI-hashes en de hash van het build-gebonden acceptance-record.

---

# Gebruik acceptance-harness

Na een nieuwe bewezen build:

```powershell
cls
cd C:\Projects\eMule
.\preview2-runtime-acceptance.ps1 -Initialize
.\preview2-runtime-acceptance.ps1 -Run
```

Los resultaat vastleggen kan ook:

```powershell
.\preview2-runtime-acceptance.ps1 -Pass UI-STARTUP -Note "Shell direct zichtbaar"
.\preview2-runtime-acceptance.ps1 -Fail THEME-DARK -Note "Wit vlak in Messages"
.\preview2-runtime-acceptance.ps1 -Status
```

Voor RC:

```powershell
.\preview2-runtime-acceptance.ps1 -VerifyCore
.\finalize-preview2-rc.ps1
```

Na portable/MSI-tests:

```powershell
.\preview2-runtime-acceptance.ps1 -VerifyAll
```

---

# Beslisregels voor volgende rondes

1. Build-success, UI-success en protocol/runtime-success blijven afzonderlijk bewijs.
2. Geen tweede eD2K/Kad/search/downloadengine bouwen.
3. Geen SQLite/filesystem/heavy work in GUI/network/scheduler hotpaths.
4. User identity = userhash; file identity = eD2K hash + size.
5. Automatic Scheduler blijft expliciete opt-in.
6. Verifiers controleren eindcontracten, niet toevallige formatting.
7. Overlay-verifiers eisen alleen stage-bestanden; repo-contracten horen in repo-preflight.
8. Shared legacy files alleen scoped controleren voor Preview2-owned code.
9. Packaging/installer bezit of verwijdert geen user config, intelligence DB, peer history of incomplete downloads.
10. Iedere nieuwe Release x64 build blijft onder compiler+linker warnings-as-errors vallen.
11. Een runtime acceptance-record is alleen geldig voor exact dezelfde Git HEAD + executable SHA256.
12. Geen merge `goal-1-5` → `develop` zonder expliciete toestemming.
