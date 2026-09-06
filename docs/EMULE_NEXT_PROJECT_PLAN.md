# eMule Next — projectplan en traceability

Dit document beschrijft de Preview 2 productarchitectuur, requirements en releasecriteria. Operationele status staat in `docs/EMULE_NEXT_TODO.md`; live protocolcases in `docs/EMULE_NEXT_RUNTIME_TEST_MATRIX.md`.

## Productdoel

eMule Next moderniseert eMule zonder de upstream eMule v0.72a eD2K/Kad/search/download/upload/hashing-kern te vervangen. Nieuwe functionaliteit wordt eromheen gebouwd als bounded services, persistente intelligence en moderne Windows-workspaces.

Preview 2 moet als één Windows-product functioneren: één primaire shell, moderne Search/Library/Known Users, complete Settings, technische Diagnostics, consistente Light/Dark/System theming, reproduceerbare artifacts en aantoonbare runtime acceptance.

## Bewezen basis

- Werkbranch: `goal-1-5`.
- Door gebruiker lokaal succesvol uitgevoerde Release x64 **FullRebuild** op `7a8844a7d329fc5a8bd787f62b209763f73fe9a6`.
- Die FullRebuild eindigde met **0 compilerwarnings, 0 linkerwarnings en 0 errors**.
- Release compiler en linker gebruiken warnings-as-errors; zero-warning is daarmee een blijvend buildcontract.
- De moderne Preview 2 hoofdsidebar/header is eerder daadwerkelijk visueel bevestigd.
- Latere commits na `7a8844a...` wijzigen release/acceptance tooling en documentatie; een uiteindelijke RC-build moet opnieuw aan dezelfde FullRebuild-/acceptancecontracten voldoen.

## Hoofdrequirements

| ID | Requirement | Acceptatiecriterium | Status |
|---|---|---|---|
| CORE-01 | Windows 10/11 x64 | Clean staged Release x64 build, 0 warnings/0 errors | bewezen; blijft gate |
| CORE-02 | Protocolcompatibiliteit | upstream eD2K/Kad/search/download/upload/A4AF/hash/View Shared Files autoritatief | statische gates gereed; live acceptance vereist |
| PERF-01 | Responsieve UI/runtime | geen zware DB/filesystemtaken in GUI/network/scheduler hotpaths | geïmplementeerd/gated |
| PERF-02 | Bounded lookups | ClientIndex 10k, DownloadIndex 5k, writer queue 10k | self-test aanwezig; runtime PASS vereist |
| PEER-01 | Persistente Known Users | userhash/endpoints/first-last seen | gebouwd; runtime acceptance vereist |
| PEER-02 | Veilige peer knowledge | bestaande shared-files capability + denied/failure cooldown | gebouwd; runtime acceptance vereist |
| SEARCH-01 | Search 2 / legacy Search | Search 2 primair; Network search gebruikt bestaande legacy engine | gebouwd; runtime acceptance vereist |
| LIB-01 | Library 2 | history/favorites/completed/missing/download later/relink/download-again | gebouwd; runtime acceptance vereist |
| INTEL-01 | Transfer intelligence | analyse/advies/optionele automation zonder protocolbreuk | gebouwd; Analysis only default |
| DATA-01 | Intelligence DB | async writer, schema v3, backup/integrity/recovery | gebouwd; failure runtime vereist |
| UI-01 | Moderne productstructuur | moderne shell direct zichtbaar | implementatie/build bewezen; runtime record vereist |
| UI-02 | System/Light/Dark | alle primaire workspaces volgen centraal theme | gebouwd; runtime record vereist |
| UI-03 | DPI/layout | 100/125/150/200% + resize bruikbaar | toolkit gebouwd; runtime record vereist |
| UI-04 | Branding | Next-versie gescheiden van protocolcore | `0.2.0 Preview 2` |
| UI-05 | Single coherent shell | alle primaire workspaces via hoofdnav | gebouwd |
| UX-01 | Progressive complexity | dagelijkse acties direct, specialistische acties via More/Advanced | gebouwd |
| SESSION-01 | State/upgrade behoud | config/DB/downloadstate/viewstate behouden | runtime/package acceptance vereist |
| CI-01 | Reproduceerbare materialization | clean overlay + structural final-state gates | gebouwd/bewezen |
| TEST-01 | Eerlijk runtimebewijs | static/build gates vervangen nooit runtime | build-bound acceptance harness aanwezig |
| SUPPORT-01 | Diagnoseerbaarheid | Diagnostics + export + privacy-bounded support bundle | gebouwd; runtime acceptance vereist |
| RELEASE-01 | Artifact identity | vaste exe/version/hash | gebouwd |
| RELEASE-02 | Portable | ZIP zonder user state | script gereed; package acceptance vereist |
| RELEASE-03 | MSI | x64, MajorUpgrade, shortcuts, user data niet bezeten | script/WiX gereed; package acceptance vereist |
| RELEASE-04 | RC finalization | RC alleen na exacte build-bound core runtime PASS | hard gate aanwezig |

## Architectuurregels

1. **Protocolkern autoritatief.** Geen tweede eD2K/Kad/search/download/uploadengine.
2. **Geen SQLite in hotpaths.** Writes via queue; queries/maintenance via bounded workers.
3. **User identity = 16-byte userhash.** Username is presentatie.
4. **File identity = eD2K hash + size.** Filename is geen canonieke sleutel.
5. **Automatic peer discovery is geen Search-tab.** Kennis wordt opgeslagen zonder tabspam.
6. **Privacy/cooldown leidend.** Handmatige refresh omzeilt geen denied/failure cooldown.
7. **Analysis only default.** Assist/Automatic zijn expliciete keuzes.
8. **Bounded intelligence.** Queues/history/telemetry/resultsets hebben harde limieten.
9. **Failure containment.** Intelligence failure blokkeert legacy core niet.
10. **Settings ≠ Diagnostics.** Productkeuzes in Settings; status/maintenance/stress/recovery in Diagnostics.
11. **Progressive complexity.** Specialistische functies blijven beschikbaar maar domineren de UI niet.
12. **MFC/Win32 productlaag.** Geen zware browser/UI-runtime.
13. **Shell is router, geen backend.** Hoofdnav gebruikt bestaande autoritatieve windows/handlers.
14. **Late Preview2 materialization.** Featuregates eerst; productlaag daarna; final-state gates als laatste.
15. **Checkout blijft schoon.** Activatie alleen in clean stage; content-aware sync naar buildtree.
16. **Build/UI/runtime afzonderlijk bewijs.** Compile groen is geen protocol-pass.
17. **Installer/portable bezitten geen user state.** Geen config/DB/peerhistory/incomplete downloads verwijderen.
18. **Supportbundle privacy-bounded.** Geen intelligence DB/preferences/known.met/.part-data.
19. **Legacy Search blijft netwerkautoriteit.** `Network search...` opent de bestaande eD2K/Kad Search.
20. **Zero-warning Release.** Compiler én linker warnings zijn errors.
21. **MFC warning scopes zijn lokaal.** C4191 wordt alleen rond echte actieve MFC message maps afgeschermd.
22. **x64-safe handles/pointers.** Geen pointer/handle→32-bit truncatie in Release.
23. **Build-bound runtimebewijs.** Acceptance is alleen geldig voor dezelfde Git HEAD + executable SHA256.

## Preview 2 UI

### Primaire navigatie

1. Dashboard
2. Transfers
3. Search
4. Library
5. Shared Files
6. Known Users
7. Messages
8. Servers
9. Kad
10. Statistics
11. Settings
12. Diagnostics
13. IRC

Search opent Search 2. `Network search...` herstelt de bestaande legacy Search-selector/parameters/resulttabs. Library, Known Users, Settings en Diagnostics zijn rechtstreeks vanuit de hoofdnav bereikbaar.

### Settings

De moderne Settings-shell bevat 19 categorieën:

**eMule Next**
- Appearance
- Peer knowledge
- Intelligence
- Advanced

**Originele eMule Preferences**
- General
- Display
- Connection
- Proxy
- Server
- Directories
- Files
- Notifications
- Statistics
- IRC
- Messages
- Security
- Scheduler
- Web Server
- Tweaks

De 15 originele pagina's blijven autoritatief en worden direct via bestaande page-ID routing geopend. Er is geen tweede opslagmodel.

### Theme

- System / Light / Dark centraal.
- Theme Apply loopt over de hoofdwindow-tree.
- Legacy primary workspaces worden bij navigatie opnieuw gethemed.
- Messages/Chat krijgt extra RichEdit/list/control behandeling om systeemwitte vlakken in Dark mode te voorkomen.

### Dashboard

Primaire filters: All / Attention / Stalled / No sources / Active.

Primaire acties: Open Transfers / Open Sources / Pause-Resume / Refresh / More...

`More...` bevat rare-parts/low-health/intervention/A4AF filters, priority, force analysis en reset intelligence history.

## Diagnostics / performance

Diagnostics bevat integrity, backup, restore, prune, checkpoint, backupfolder en stress self-test.

Self-test:
- ClientIndex 10.000
- DownloadIndex 5.000
- async writer 10.000 events

PASS vereist queued=0, processed=expected, dropped=0, errors=0.

## Buildkwaliteit

Release x64 gebruikt:

- clean activation overlay;
- repository preflight vóór stage creation;
- structurele activation-chain gates;
- scoped final-state verifiers;
- expliciete LTCG;
- compiler warnings-as-errors;
- linker warnings-as-errors;
- systematische CWnd Create-hiding hardening;
- x64 pointer/handle-safe conversions;
- lokale MFC C4191 scopes uitsluitend rond actieve message maps.

Een FullRebuild is de acceptatietest voor zero-warning status.

## Build-bound runtime acceptance

`preview2-runtime-acceptance.ps1` beheert `artifacts/preview2-runtime-acceptance.json`.

Het record bevat:

- productversie;
- Git HEAD;
- SHA256 van de exact geteste EXE;
- PASS/FAIL/NOT_TESTED per check;
- notities en timestamps.

Als HEAD of EXE-hash afwijkt, wordt het record geweigerd en moet voor de nieuwe build een nieuw record worden geïnitialiseerd.

### Core runtime checks

- startup/shell
- alle hoofdnav-routes
- Search2 → Network search bridge
- complete Settings/page-routing
- live header
- Dashboard primary/More
- Dark theme + theme switching
- DPI/resize
- Diagnostics stress + DB maintenance
- eD2K
- Kad
- upload/queue
- intelligence/scheduler
- Known Users
- Library
- persistence/restart
- recovery
- support bundle

Alle core checks moeten PASS zijn vóór `finalize-preview2-rc.ps1` verdergaat.

### Package checks

Na RC-artifactcreatie:

- portable clean-unpack/start
- MSI clean install
- MSI upgrade/user-state behoud
- MSI uninstall/user-state behoud

`preview2-runtime-acceptance.ps1 -VerifyAll` is het laatste package-ready criterium.

## Release-architectuur

### Build

`build-local.ps1` publiceert:

- `artifacts/eMule-Next-0.2.0-Preview2-x64.exe`
- `artifacts/eMule-Next-x64.exe`

### Portable

`package-preview2.ps1` maakt de portable ZIP en SHA256 zonder config, intelligence DB, peerhistory of `.part/.part.met`.

### Support

`create-preview2-support-bundle.ps1` maakt een privacy-bounded bundle met Diagnostics-report/build/public docs en zonder user state.

### MSI

WiX installer:

- x64 Program Files;
- Start Menu;
- optionele Desktop shortcut;
- MajorUpgrade;
- geen ownership van AppData/config/intelligence/downloadstate.

### RC finalizer

`finalize-preview2-rc.ps1`:

1. verifieert build-bound **core runtime acceptance**;
2. verifieert release-layout en built EXE;
3. maakt portable package;
4. maakt optioneel MSI;
5. schrijft RC manifest met Git HEAD;
6. schrijft SHA256 voor EXE/ZIP/MSI en acceptance-record;
7. vermeldt dat package acceptance nog apart met `-VerifyAll` moet slagen.

## Release Candidate acceptancepad

1. FullRebuild huidige `goal-1-5` met 0 warnings/0 errors.
2. `preview2-runtime-acceptance.ps1 -Initialize`.
3. Core runtimechecks uitvoeren en registreren.
4. `preview2-runtime-acceptance.ps1 -VerifyCore` moet PASS zijn.
5. `finalize-preview2-rc.ps1` uitvoeren; optioneel `-BuildMsi`.
6. Portable/MSI checks uitvoeren en registreren.
7. `preview2-runtime-acceptance.ps1 -VerifyAll` moet PASS zijn.
8. Alleen daarna is de artifactset **Preview 2 Release Candidate / package-ready**.
9. Geen merge `goal-1-5` → `develop` zonder expliciete toestemming.
