# eMule Next — projectplan en traceability

Dit document beschrijft de productarchitectuur en acceptatiecriteria voor eMule Next. De operationele status staat in `docs/EMULE_NEXT_TODO.md`; echte runtimecases staan in `docs/EMULE_NEXT_RUNTIME_TEST_MATRIX.md`.

## Productdoel

eMule Next moderniseert eMule zonder de bewezen eD2K/Kad-protocolkern onnodig te herschrijven. De upstream eMule v0.72a netwerk-, download-, upload-, hashing- en searchlogica blijft autoritatief. Nieuwe functionaliteit wordt eromheen gebouwd als bounded services, persistente intelligence en moderne workspaces.

Preview 2 is de eerste producttranche waarin deze technische lagen als één coherent Windows-product worden aangeboden: moderne hoofd-shell, begrijpelijke Settings, expliciete Diagnostics/runtimevalidatie en reproduceerbare portable/MSI-output.

## Hoofdrequirements

| ID | Requirement | Acceptatiecriterium | Huidige status |
|---|---|---|---|
| CORE-01 | Windows 10/11 x64 build | Lokale Release x64 build via geïsoleerde activation-stage; artifact wordt gepubliceerd | Preview 2 build bewezen op `4294bd9983c3da0286e4e1736b61032fedf1621d`; nieuwe zichtbare-main-shell head wacht op build |
| CORE-02 | Legacy protocolcompatibiliteit | eD2K/Kad, bestaande downloads/uploads, A4AF, hashing en View Shared Files blijven werken | Legacy code blijft leidend; statische contractgate aanwezig; volledige live matrix blijft vereist |
| PERF-01 | Responsieve UI/runtime | Geen nieuwe zware DB/filesystemtaken in GUI/network/scheduler hotpaths | Background/query-only/write-queue architectuur aanwezig; Preview 2 shell voegt alleen UI-routing/chrome toe |
| PERF-02 | Bounded snelle lookups | ClientIndex/DownloadIndex bounded en onder stress correct | Deterministische 10k/5k self-test + tijdelijke 10k writerstress geïmplementeerd; runtime-run open |
| PEER-01 | Persistente Known Users | Userhash, endpoints, first/last seen en presentatiegegevens historisch beschikbaar | Known Users 2.0 gebouwd; runtimevalidatie open |
| PEER-02 | Veilige peer knowledge | Alleen bestaande shared-file capability; privacy/denial/cooldown respecteren; geen agressieve scan | Geïmplementeerd; Preview 2 Settings maakt dit als begrijpelijke productoptie zichtbaar |
| PEER-03 | Geconsolideerde Known Users workspace | Eén permanente view met userlijst + geselecteerde filekennis | Gebouwd; Preview 2 moderniseert presentatie/navigation |
| PEER-04 | Restored peer tabs dedupliceren | Userhash primair, endpoint alleen disambiguatie; geen dubbele automatische aanvraag | Statische/deterministische gates aanwezig; runtimecase open |
| PEER-05 | Peer↔file historie | First/last seen en current/history per file | Geïmplementeerd en gebouwd; runtimecase open |
| SEARCH-01 | Search 2 | Live legacy + historische kennis, filters, saved searches, block rules, bulk/export | Producttranche gebouwd; Preview 2 styling/navigation toegevoegd; runtime paralleltest open |
| LIB-01 | Library 2 | History/favorites/completed/missing/download later/relink/download-again | Producttranche gebouwd; Preview 2 styling/navigation toegevoegd; runtime recoverycases open |
| INTEL-01 | Download intelligence | Historische kennis ondersteunt analyse/advies/optionele automatisering zonder protocolbreuk | Dashboard/Transfers/Scheduler intelligence gebouwd; Analysis only blijft default |
| UI-01 | Moderne productstructuur | **Bij startup direct herkenbare Preview 2 hoofd-shell** met moderne hoofdsidebar/header; klassieke toolbar niet meer primaire chrome; Dashboard/Transfers/Search/Library/Known Users/Settings/Diagnostics logisch bereikbaar | Inner-workspace UI compile-bewezen op `4294bd99…`, maar runtime toonde nog klassieke hoofd-shell; nieuwe main-shell materialization geïmplementeerd en wacht op build/runtimebewijs |
| UI-02 | System/Light/Dark | Eén centrale appearance-keuze; geen losse per-view theme-knoppen | Preview 2 Settings centraliseert theme; ModernUi palette wordt ook door hoofdsidebar gebruikt |
| UI-03 | Moderne DPI/layout | 100–200% bruikbaar, consistente spacing/fonts/cards/list styles, geen UI-blocking | ModernUi toolkit + UiMetrics + DPI-aware hoofdsidebar/header; praktische matrix open |
| UI-04 | eMule Next branding | Productversie is duidelijk gescheiden van protocol-coreversie en zichtbaar in window/header/diagnostics | Preview 2 identiteit `0.2.0 Preview 2`; protocolnegotiatie blijft v0.72a core |
| SESSION-01 | Sessiestatus/data behouden | Relevante viewstate, config, DB en incomplete downloads over restart/upgrade behouden | Preview2 main section wordt persistent; bestaande data persistence blijft leidend; upgradepraktijktest open |
| DATA-01 | Lokale intelligence database | Schema migrations, async writer, query-only reads, backup/integrity/recovery | Schema v3 + backup/recovery/maintenance gebouwd op bewezen DB2 basis |
| CI-01 | Reproduceerbare bootstrap/activation | Clean staged materialization, eindgates en optionele determinism check | Bewezen architectuur; Preview 2 wordt bewust pas na oude completion gates gematerialiseerd |
| TEST-01 | Eerlijk runtimebewijs | Statische gates mogen echte netwerk/runtimetests niet vervangen | Runtime matrix bestaat en Preview 2 Diagnostics bewaart PASS/FAIL/Not tested per test-ID |
| SUPPORT-01 | Diagnoseerbaar product | Health, queues, scheduler, stress, maintenance en exporteerbaar rapport | Preview 2 Diagnostics dashboard + export compile-bewezen; praktische runtime open |
| RELEASE-01 | Preview 2 artifact identity | Eén versie/naam voor executable, build identity en release docs | `0.2.0 Preview 2`; `eMule-Next-0.2.0-Preview2-x64.exe` in buildscript |
| RELEASE-02 | Portable distributie | ZIP bevat alleen runtime + docs, geen user data; SHA-256 manifest | `package-preview2.ps1` geïmplementeerd; daadwerkelijke package-test open |
| RELEASE-03 | MSI installatie/upgrade | x64 MSI, MajorUpgrade, Start Menu, optionele Desktop shortcut; user data niet door MSI bezeten | WiX definitie + buildscript geïmplementeerd; install/upgrade/uninstall test open |

## Architectuurregels

1. **Protocolkern blijft autoritatief.** Preview 2 mag geen tweede eD2K/Kad/search/download/uploadengine introduceren.
2. **Geen SQLite in network/scheduler/GUI hotpaths.** Writes lopen via queues; reads/maintenance via workers/query-only verbindingen.
3. **User identity = 16-byte userhash.** Username is presentatie/migratiesignaal; endpoint alleen disambiguatie waar nodig.
4. **File identity = eD2K hash + size.** Filename is geen canonieke correlatiesleutel.
5. **Automatic peer discovery is geen Search-tab.** Automatische share-antwoorden worden opgeslagen zonder ieder resultaat in legacy Search UI te injecteren.
6. **Privacy/cooldown blijft leidend.** Handmatige peer refresh mag success-TTL vernieuwen, maar denied/failure-cooldowns niet omzeilen.
7. **Analysis only blijft veilige default.** Assist/Automatic zijn expliciete gebruikerskeuzes.
8. **Intelligence is bounded.** History/telemetry/queues/resultsets hebben harde limieten en maintenance/pruning.
9. **Failure containment.** Een corrupte/uitgeschakelde intelligence DB mag de legacy eMule netwerkcore niet verhinderen te starten.
10. **Settings en Diagnostics zijn gescheiden.** Settings bevat productkeuzes; Diagnostics bevat runtime-status, maintenance, stress en validatie.
11. **Technische defaults niet onnodig exposen.** History/telemetrycapaciteiten zijn bounded productdefaults; expert scheduler tuning verschijnt alleen na expliciete Advanced-opt-in.
12. **Moderne UI zonder nieuwe zware runtime.** Preview 2 gebruikt MFC/Win32 + gedeelde `CEmuleNextModernUi`; geen WebView/Chromium of externe UI-runtime.
13. **Moderne shell boven legacy routing.** De Preview 2 hoofdsidebar/header sturen de bestaande `SetActiveDialog`, TransferWnd en Search-host. Ze vervangen geen protocol- of transferengine.
14. **Late Preview 2 materialization.** Bestaande bewezen featurecompletion-gates draaien eerst. Preview 2 vervangt daarna de uiteindelijke UI/productbestanden en draait één eigen final-state gate.
15. **Buildactivatie muteert de checkout niet.** Alle materialisatie vindt plaats in clean activation-stage en wordt content-aware naar de upstream buildtree gesynchroniseerd.
16. **Build-success ≠ runtime-success.** Live eD2K/Kad/upload/download/A4AF/restart/DPI én zichtbare UI worden alleen PASS na werkelijke uitvoering.
17. **Installer bezit geen user data.** Config, intelligence DB, peer history en incomplete downloads mogen niet als MSI-applicatiebestanden worden verwijderd bij uninstall/upgrade.

## Preview 2 UI-architectuur

### Hoofd-shell

De eerste Preview 2 build compileerde de moderne workspaces maar liet de klassieke `CemuleDlg`/`CMuleToolbarCtrl` hoofdchrome dominant. Dat voldoet niet aan UI-01.

De definitieve Preview 2 shell bestaat daarom uit:

- een direct zichtbare owner-drawn hoofdsidebar;
- Preview 2 productheader + actuele sectietitel;
- een zichtbare Connect/Disconnect-actie;
- contentgebied rechts van sidebar en onder header;
- de legacy toolbar blijft technisch leven voor command compatibility maar is niet langer de primaire zichtbare navigatie;
- routing blijft naar bestaande child windows en command handlers gaan.

Hoofdsidebar:

- Dashboard
- Transfers
- Search
- Shared Files
- Servers
- Kad
- Messages
- IRC
- Statistics
- Settings

`Dashboard` roept de bestaande eMule Next Dashboard-route aan; `Transfers` keert expliciet terug naar de klassieke downloadlijst. Geen netwerk- of transferlogica wordt gedupliceerd.

### Gedeelde ModernUi-laag

`CEmuleNextModernUi` levert:

- DPI-aware margins/controlhoogtes/navigationbreedte/headerhoogte;
- Window/navigation/card palette bovenop bestaande theme service;
- Segoe UI Variable met Segoe UI fallback;
- moderne ListView/Header/Combo theming;
- reusable owner-draw status cards;
- `CEmuleNextNavList` voor moderne geselecteerde navigatierijen;
- gedeelde success/warning/error/accent kleuren.

### Permanente Next navigation

De legacy Search host blijft bestaan om bewezen netwerksearchtabs niet te breken. Voor permanente eMule Next views blijft daarbinnen een tweede, contextspecifieke sidebar:

- Search
- Library
- Known Users
- Settings
- Diagnostics

Deze subnavigatie is geen vervanging voor de hoofd-shell; het is workspace-navigation binnen Search. Een latere polishronde mag Library/Known Users/Diagnostics direct vanuit de hoofdsidebar bereikbaar maken, mits zonder duplicate routing/logica.

### Settings informatiearchitectuur

**Appearance**
- System / Light / Dark
- Smart ETA/Health indicatoren

**Peer knowledge**
- automatische knowledge collection via normale shared-file capability
- eenvoudige bounded concurrency: Automatic / 1 / 2 / 4 / 8

**Intelligence**
- Analysis only / Assist / Automatic
- Conservative / Balanced / Responsive
- Source discovery / A4AF / Rare-part intelligence

**Advanced**
- `Use custom scheduler tuning`
- pas daarna cooldown / batch / A4AF threshold

Niet meer als normale instellingen:
- history cache enable/capacity
- telemetry enable/capacity
- runtime counters/status
- database maintenance/stress

Doel voor eindproduct: Next-specifieke productkeuzes mogen niet als verborgen tweede settingswereld voelen; verdere integratie met de normale Preferences-ervaring blijft een expliciete UI-taak.

### Diagnostics informatiearchitectuur

Bovenaan health cards:
- Database
- Writer queue
- Smart Scheduler
- Performance self-test

Daaronder maintenance:
- integrity
- backup
- restore
- prune
- checkpoint
- open backupfolder
- stress self-test

Daaronder runtime validation met persistente teststatus en rapportexport.

## Release-architectuur

### Lokale executable

`build-local.ps1` publiceert na een succesvolle Release x64 build:

- `artifacts/eMule-Next-0.2.0-Preview2-x64.exe`
- `artifacts/eMule-Next-x64.exe`

Productversie en build-head zijn metadata; ze veranderen geen protocolversie.

### Portable

`package-preview2.ps1` maakt:

- `eMule-Next-0.2.0-Preview2-x64-portable.zip`
- SHA-256 manifest

De ZIP bevat executable + release/testdocumentatie, geen user state.

### MSI

`build-preview2-installer.ps1` + `installer/preview2/Product.wxs` leveren via WiX:

- x64 per-machine Program Files installatie;
- Start Menu shortcut;
- optionele Desktop shortcut;
- MajorUpgrade;
- geen eigendom over AppData/config/intelligence/downloadstate.

## Fasen en status

### Fase A — stabiele basis
- Windows x64 build, dependency bootstrap, staged activation en determinism-mechanisme: **gereed/bewezen**.

### Fase B — peer knowledge
- Known Users 2.0, share scanner, persistence en deduplicatie: **implementatie/build gereed; runtime open**.

### Fase C — Search en Library
- Search 2.0 en Library 2.0 grote producttranches: **implementatie/build gereed; runtime open**.

### Fase D — Transfers/intelligence
- Dashboard/Transfers/Scheduler canonical intelligence en persistence: **implementatie/build gereed; runtime open**.

### Fase E — data/recovery/performance hardening
- schema v3, backups/recovery/diagnostics, index/writer stress en protocolcontractgate: **build bewezen; runtime self-test/matrix open**.

### Fase F — Preview 2 productisering
- ModernUi toolkit + inner workspace styling: **compile-bewezen op `4294bd99…`**.
- categorized Settings: **compile-bewezen; runtime open**.
- Diagnostics cards/runtime matrix/export: **compile-bewezen; runtime open**.
- contextspecifieke Next workspace sidebar: **compile-bewezen**.
- zichtbare hoofd-shell: **geïmplementeerd na runtime UI-gap; nieuwe build/runtime open**.
- Preview 2 version/artifact naming: **compile-bewezen**.
- portable packaging: **script gereed; package/runtimetest open**.
- MSI: **bron/buildscript gereed; WiX/install/upgrade/uninstall test open**.

## Eerstvolgende acceptatiepad

1. Nieuwe `goal-1-5` head lokaal Release x64 bouwen via `build-local.ps1 -KeepActivationStage`.
2. **Bij startup moet onmiddellijk de nieuwe Preview 2 hoofdsidebar + header zichtbaar zijn.** Als dat niet zo is, is UI-01 niet geslaagd ondanks een groene compile.
3. Dashboard/Transfers/Search/Shared Files/Servers/Kad via hoofdsidebar aanklikken en routing controleren.
4. Settings openen en controleren dat technische diagnostics daar niet teruggekeerd zijn.
5. Diagnostics openen en UI/cards/runtime matrix controleren.
6. Stress self-test uitvoeren en PASS-resultaat vastleggen.
7. System/Light/Dark en DPI 100/125/150/175/200% testen.
8. Preview 1 bestaande config/database/incomplete downloads met Preview 2 starten en behoud/migratie controleren.
9. Runtime matrix doorlopen met echte eD2K/Kad peers/downloads/uploads.
10. Diagnostics rapport exporteren als runtimebewijs.
11. Portable ZIP genereren en clean-unpack/start testen.
12. MSI bouwen met WiX en clean install / Preview1 upgrade / uninstall testen.
13. Alleen na deze runtimebewijzen Preview 2 als release-candidate behandelen.
14. `goal-1-5` nooit zonder expliciete toestemming naar `develop` promoveren.