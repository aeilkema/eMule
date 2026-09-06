# eMule Next — projectplan en traceability

Dit document beschrijft productarchitectuur, requirements en acceptatiecriteria. Operationele status staat in `docs/EMULE_NEXT_TODO.md`; echte runtime/protocolcases in `docs/EMULE_NEXT_RUNTIME_TEST_MATRIX.md`.

## Productdoel

eMule Next moderniseert eMule zonder de bewezen upstream eMule v0.72a eD2K/Kad/search/download/upload/hashing-kern onnodig te herschrijven. Nieuwe functionaliteit wordt eromheen gebouwd als bounded services, persistente intelligence en moderne Windows-workspaces.

Preview 2 is de eerste tranche die als één Windows-product moet aanvoelen: één primaire shell, moderne Search/Library/Known Users, begrijpelijke Settings, technische Diagnostics, reproduceerbare artifacts en een expliciet runtime acceptance-pad.

## Bewezen basis

- Werkbranch: `goal-1-5`.
- Laatst door gebruiker lokaal gebouwd én visueel bevestigd: `5049c3a69a1b14911daad6bfa5e9d173d2e9554a`.
- Op die head is de nieuwe Preview 2 hoofdsidebar/header daadwerkelijk zichtbaar bij startup.
- `4294bd9983c3da0286e4e1736b61032fedf1621d` blijft regressiereferentie: compile groen maar UI-acceptatie fout omdat de klassieke shell nog dominant was.
- De huidige UX-completionlaag na `5049c3a...` is geïmplementeerd en statisch gehard, maar nog niet lokaal build/runtime bewezen.

## Hoofdrequirements

| ID | Requirement | Acceptatiecriterium | Status |
|---|---|---|---|
| CORE-01 | Windows 10/11 x64 | Clean staged Release x64 build; artifact gepubliceerd | basis bewezen; huidige UX head build open |
| CORE-02 | Protocolcompatibiliteit | eD2K/Kad/search/download/upload/A4AF/hash/View Shared Files blijven upstream-authoritatief | statische contractgates aanwezig; live matrix open |
| PERF-01 | Responsieve UI/runtime | Geen zware DB/filesystemtaken in GUI/network/scheduler hotpaths | architectuur aanwezig |
| PERF-02 | Bounded lookups | ClientIndex/DownloadIndex/writer queue bounded en stressbaar | 10k/5k/10k self-test aanwezig; runtime-run open |
| PEER-01 | Persistente Known Users | userhash/endpoints/first-last seen beschikbaar | gebouwd; runtime open |
| PEER-02 | Veilige peer knowledge | normale shared-file capability, denied/failure cooldown respecteren | gebouwd; runtime open |
| PEER-03 | Known Users workspace | één gebruikers-/filekennisworkspace | gebouwd; primaire nav-promotie geïmplementeerd |
| PEER-04 | Deduplicatie | userhash primair; endpoint alleen disambiguatie | gates aanwezig; runtime open |
| PEER-05 | Peer↔file historie | first/last seen/current/history | gebouwd; runtime open |
| SEARCH-01 | Search 2 / legacy Search | Search 2 is primaire workspace; legacy eD2K/Kad search blijft autoritatief via expliciete Network search-brug; geen tweede netwerkengine | geïmplementeerd; build/runtime open |
| LIB-01 | Library 2 | history/favorites/completed/missing/download later/relink/download-again | gebouwd; primaire nav-promotie geïmplementeerd |
| INTEL-01 | Transfer intelligence | analyse/advies/optionele automation zonder protocolbreuk | gebouwd; Analysis only default |
| DATA-01 | Intelligence DB | schema migration, async writer, backup/integrity/recovery | schema v3/DB2 gebouwd; failure runtime open |
| UI-01 | Moderne productstructuur | bij startup direct zichtbare moderne shell | bewezen op `5049c3a...` |
| UI-02 | System/Light/Dark | één centrale appearance-keuze | gebouwd; volledige runtime matrix open |
| UI-03 | DPI/layout | 100–200%, resize, consistente controls | toolkit aanwezig; runtime matrix open |
| UI-04 | Branding | Next-versie gescheiden van v0.72a protocolcore | `0.2.0 Preview 2` |
| UI-05 | Single coherent application shell | primaire workspaces bereikbaar vanuit hoofdnav zonder verborgen Search-subnav als noodzakelijke eindroute | Search2/Library/Known Users/Settings/Diagnostics directe routing geïmplementeerd; build open |
| UX-01 | Progressive complexity | dagelijkse acties direct; technische/rare acties beschikbaar maar niet dominant | Settings/Diagnostics-scheiding, Dashboard More en classic settings bridge geïmplementeerd |
| SESSION-01 | State/upgrade behoud | config/DB/downloadstate/viewstate behouden | architectuur aanwezig; upgradepraktijktest open |
| CI-01 | Reproduceerbare materialization | clean overlay, oude gates eerst, late Preview2 final-state gates | bewezen patroon; UX-gate + Search compile-order gate toegevoegd |
| TEST-01 | Eerlijk runtimebewijs | static gate vervangt nooit netwerk/runtimetest | runtime matrix + Diagnostics status aanwezig |
| SUPPORT-01 | Diagnoseerbaarheid | health, stress, maintenance, export en veilige supportbundle | report + safe support-bundle script aanwezig; runtime open |
| RELEASE-01 | Artifact identity | vaste exe/manifest/version | gebouwd |
| RELEASE-02 | Portable | ZIP zonder user state + SHA256 | script gereed; run open |
| RELEASE-03 | MSI | x64, MajorUpgrade, shortcuts, user data niet bezeten | WiX/script gereed; run open |
| RELEASE-04 | RC finalization | één commando voor releasecheck/portable/optionele MSI/hashmanifest | `finalize-preview2-rc.ps1` geïmplementeerd |

## Architectuurregels

1. **Protocolkern autoritatief.** Geen tweede eD2K/Kad/search/download/uploadengine.
2. **Geen SQLite in hotpaths.** Writes via queue; queries/maintenance via bounded workers/query-only verbindingen.
3. **User identity = 16-byte userhash.** Username is presentatie; endpoint alleen disambiguatie.
4. **File identity = eD2K hash + size.** Filename is geen canonieke sleutel.
5. **Automatic peer discovery is geen Search-tab.** Resultaten worden opgeslagen zonder legacy UI-tabspam.
6. **Privacy/cooldown leidend.** Handmatig refresh mag success-TTL vernieuwen, niet denied/failure cooldown omzeilen.
7. **Analysis only default.** Assist/Automatic altijd expliciete keuze.
8. **Bounded intelligence.** Queues, history, telemetry en resultsets hebben harde limieten.
9. **Failure containment.** Intelligence failure mag legacy eMule core niet blokkeren.
10. **Settings ≠ Diagnostics.** Productkeuzes in Settings; status/maintenance/stress/recovery in Diagnostics.
11. **Progressive complexity.** Technische defaults en specialistische acties blijven bereikbaar, maar domineren de dagelijkse UI niet.
12. **MFC/Win32 productlaag.** Geen Chromium/WebView/zware UI-runtime.
13. **Shell is router, geen backend.** Hoofdnav stuurt bestaande `SetActiveDialog`, TransferWnd en Search-host.
14. **Late Preview2 materialization.** Bestaande featuregates eerst; product/UI-laag daarna; eigen final-state gates.
15. **Checkout blijft schoon.** Activatie alleen in clean stage, content-aware sync naar upstream buildtree.
16. **Build/UI/runtime afzonderlijk bewijs.** Compile groen is niet automatisch UI- of protocol-pass.
17. **Installer/portable bezitten geen user state.** Geen config/intelligence DB/peer history/incomplete downloads verwijderen.
18. **Supportbundle privacy-bounded.** Alleen Diagnostics-report/build/public docs; geen ruwe DB of willekeurige userlogmappen.
19. **Legacy Search blijft netwerkautoriteit.** Search 2 presenteert kennis/historie; `Network search...` opent de bestaande eD2K/Kad Search-parameters en resulttabs.
20. **Generated compile-contracten zijn expliciet.** Late activators mogen niet afhankelijk zijn van toevallige PCH/include-volgorde; final-state gates controleren kritieke include/order-contracten.

## Preview 2 UI-architectuur

### Hoofd-shell

De hoofd-shell bestaat uit:

- owner-drawn verticale hoofdsidebar;
- productheader + actuele sectietitel;
- live connection/transferstatus via bestaande eMule refreshpaden;
- Connect/Disconnect via bestaande commandroute;
- content rechts van sidebar en onder header;
- klassieke toolbar technisch aanwezig maar niet primaire chrome.

Primaire navigation:

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

Settings en Diagnostics worden bewust niet als startup-last-view bewaard; normale werkruimtes wel.

### Search

De hoofdsidebar **Search** opent `Search 2` als moderne standaardworkspace. Search 2 combineert de bestaande bounded historische/intelligence-resultaten met de reeds aanwezige live legacy-resultaatsnapshot; het start zelf geen nieuwe eD2K/Kad netwerkengine.

Naast de moderne Search-knop staat **Network search...**. Die actie:

1. activeert de bestaande `CSearchDlg`;
2. herstelt de legacy Search-selector/resulttabs via `ShowLegacySearchWorkspace()`;
3. opent de bestaande Search-parameters via `OpenParametersWnd()`;
4. laat eD2K server/global/Kad routing volledig aan upstream code.

De late Search-activator dwingt daarnaast compile-safe include-order af: `SearchResultsWnd.h` vóór `SearchDlg.h`, zodat de bridge niet toevallig afhankelijk is van PCH side effects.

### Search-host routing

De permanente Next-workspaces blijven technisch in `CSearchResultsWnd` omdat dit de bewezen host is. Voor de product-UX geldt:

- `ShowNextWorkspace(searchID)` is de smalle publieke router;
- hoofdnav kan Search2/Library/Known Users/Settings/Diagnostics direct tonen;
- interne Next-sidebar wordt bij directe hoofdnav-routes verborgen;
- permanente workspace krijgt volledige contentbreedte;
- `ShowLegacySearchWorkspace()` herstelt echte legacy Search-selector/tabs;
- View Shared Files en handmatige netwerksearchtabs behouden hun klassieke lifecycle.

Hierdoor wordt de Search-host een implementation detail, geen vereiste gebruikersnavigatie.

### Dashboard / Transfers

Dashboard is het dagelijkse overzicht. De primaire zichtbare filters zijn:

- All
- Attention
- Stalled
- No sources
- Active

Primaire acties:

- Open Transfers
- Open Sources
- Pause/Resume
- Refresh
- More...

**More...** houdt de specialistische functies beschikbaar zonder knopwand:

- Rare parts / Low health / Intervention / A4AF filters;
- Priority high / normal;
- Force intelligence analysis;
- Reset selected intelligence history.

De summary toont alleen de dagelijkse toestand: downloads, active, attention, actuele downloadrate, uploads en schedulerstatus. Transfers blijft de autoritatieve detail-/werkweergave voor downloads en sources.

### Settings

Moderne hoofd-Settings:

**Appearance**
- System / Light / Dark
- Smart ETA/Health-presentatie

**Peer knowledge**
- automatische knowledge collection
- bounded concurrency Automatic/1/2/4/8

**Intelligence**
- Analysis / Assist / Automatic
- Conservative / Balanced / Responsive
- Source discovery / A4AF / Rare-parts

**Advanced**
- custom scheduler tuning opt-in
- cooldown / batch / A4AF threshold pas daarna

Daarnaast staat **Classic eMule settings...** in dezelfde Settings-ingang voor upstream Connection, Directories en overige Preferences. Daarmee is er één productingang zonder configfunctionaliteit te dupliceren.

### Diagnostics

Health cards:
- Database
- Writer queue
- Scheduler
- Performance

Maintenance:
- integrity
- backup
- restore
- prune
- checkpoint
- backupfolder
- stress self-test

Runtime validation:
- persistente Not tested/PASS/FAIL/reset per testgroep
- exporteerbaar support report
- veilige support-bundle helper buiten de GUI, zonder user state.

## Performance / stress

Self-test gebruikt echte productdatastructuren maar disposable data:

- ClientIndex: 10.000
- DownloadIndex: 5.000
- async DB writer: 10.000 events op tijdelijke database

Pass vereist queued=0, processed=expected, dropped=0, errors=0. Live eD2K/Kad gedrag blijft aparte runtime matrix.

## Release-architectuur

### Build

`build-local.ps1` publiceert:

- `artifacts/eMule-Next-0.2.0-Preview2-x64.exe`
- `artifacts/eMule-Next-x64.exe`

### Portable

`package-preview2.ps1` publiceert:

- `eMule-Next-0.2.0-Preview2-x64-portable.zip`
- SHA256 manifest
- release notes/runtime matrix
- veilige support-bundle helper

Geen config, DB, peerhistory of `.part/.part.met`.

### Support

`create-preview2-support-bundle.ps1 -DiagnosticsReport <file>` maakt een privacy-bounded ZIP met:

- geëxporteerd Diagnostics-report;
- build/head/hash/systemmetadata;
- publieke release notes/runtime matrix.

Expliciet uitgesloten: intelligence DB, preferences/config, known.met/peerhistory, incomplete downloads, willekeurige logfolders.

### MSI

`build-preview2-installer.ps1` + WiX:

- x64 Program Files;
- Start Menu;
- optionele Desktop shortcut;
- MajorUpgrade;
- geen AppData/config/intelligence/downloadstate ownership.

### RC finalizer

`finalize-preview2-rc.ps1`:

1. release-layout verificatie;
2. portable package;
3. optionele MSI (`-BuildMsi`);
4. executable/ZIP/MSI SHA256;
5. RC manifest met Git head;
6. expliciete waarschuwing dat artifact-creatie geen runtime acceptance vervangt.

## Fasen

### A — Stabiele buildbasis
**Gereed/bewezen.**

### B — Peer knowledge
**Implementatie/build gereed; live runtime open.**

### C — Search/Library
**Kernimplementatie/build gereed; Preview2 Search2-primary UX geïmplementeerd; nieuwe build/runtime open.**

### D — Transfers/Scheduler intelligence
**Implementatie/build gereed; Dashboard progressive UX geïmplementeerd; nieuwe build/runtime open.**

### E — Database/recovery/performance
**Implementatie/build gereed; failure/stress/live runtime deels open.**

### F — Preview 2 shell/productisering
- inner ModernUi: build bewezen;
- zichtbare hoofd-shell: build + zichtbaarheid bewezen op `5049c3a...`;
- primaire Search2/Library/Known Users/Settings/Diagnostics routes: geïmplementeerd, nieuwe build open;
- legacy Network search bridge: geïmplementeerd + compile-order gate, nieuwe build/runtime open;
- Dashboard progressive complexity: geïmplementeerd, nieuwe build/runtime open;
- live headerstatus: geïmplementeerd, nieuwe build/runtime open;
- safe support bundle + RC finalizer: scripts gereed, execution open.

### G — Release Candidate acceptance
Nog open; geen nieuwe featuretranche voordat onderstaande kernruntime is uitgevoerd.

## Release Candidate acceptancepad

1. Build huidige `goal-1-5` UX-completion head met `build-local.ps1 -KeepActivationStage`.
2. Startup: moderne shell direct zichtbaar.
3. Alle 13 hoofdnav-routes testen.
4. Search → Search 2 → Network search... → legacy Search parameters/resulttabs testen.
5. View Shared Files naast directe Library/Known Users routes testen.
6. Dashboard primary filters/actions + More... testen.
7. Settings → Classic eMule settings bridge.
8. Live header connection/rates.
9. Diagnostics self-test PASS.
10. System/Light/Dark en DPI 100/125/150/175/200 + resize.
11. Preview1→Preview2 config/DB/downloadstate behoud.
12. Disposable DB corruption/restore/recovery.
13. eD2K server connect/search/download/reconnect.
14. Kad bootstrap/search/source lookup/restart.
15. upload/queue, pause/resume/restart/hash/completion, A4AF/rare-parts.
16. View Shared Files accepted/denied/cooldown/background knowledge.
17. Library relink/download-again/missing/available-again.
18. Known Users userhash/duplicate names/alias/favorite/delete-history.
19. Diagnostics report + safe support bundle.
20. Portable clean-unpack/start.
21. MSI clean install / Preview1 upgrade / uninstall; user state behouden.
22. `finalize-preview2-rc.ps1`; hashes en Git head vastleggen.
23. Alleen daarna **Preview 2 Release Candidate**.
24. Geen merge `goal-1-5` → `develop` zonder expliciete toestemming.
