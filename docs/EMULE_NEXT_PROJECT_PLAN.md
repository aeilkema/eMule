# eMule Next — projectplan en traceability

Dit document is de leidraad voor de modernisering van eMule. Nieuwe wijzigingen op `develop` moeten aan een requirement hieronder gekoppeld kunnen worden. Een backendklasse geldt niet als "klaar" zolang de runtime-koppeling en, waar van toepassing, de gebruikersinterface ontbreken.

De concrete operationele werklijst staat in `docs/EMULE_NEXT_TODO.md`. De praktische runtime/stress/protocoltests staan in `docs/EMULE_NEXT_RUNTIME_TEST_MATRIX.md`.

## Doel

eMule moderniseren zonder de bewezen eD2K/Kad-protocolkern onnodig te herschrijven. De bestaande netwerkcompatibiliteit blijft leidend; nieuwe functies worden eromheen gebouwd als testbare services met een moderne, responsieve interface.

## Hoofdrequirements

| ID | Requirement | Acceptatiecriterium | Status |
|---|---|---|---|
| CORE-01 | Windows 10/11 x64 moderne build | Schone lokale Release x64 build met geïsoleerde activation-stage | Groen t/m DB/Recovery/Diagnostics 2.0 op `57b468ffcbb2934007d664e98b9b44cb50e673a2`; huidige Perf2-tranche wacht op buildbevestiging |
| CORE-02 | Oude eMule-protocollen compatibel houden | eD2K/Kad, downloads/uploads, hashing, pause/resume/restart en handmatige View Shared Files blijven werken | Legacy contract-gate aanwezig; echte runtime-regressiematrix blijft verplicht vóór Preview 2 |
| PERF-01 | Interface mag niet blokkeren door nieuwe functies | Databasewrites, history reads, recovery en zware tests buiten GUI/network hotpaths | Ver gevorderd: async writer/readers/workers; Diagnostics maintenance + stress via background worker; runtime schaaltest blijft open |
| PERF-02 | Snellere lookups | ClientIndex/DownloadIndex vervangen veilige lineaire scans met fallback en blijven consistent onder load | Indexen aanwezig; deterministische 10k/5k stress self-test toegevoegd; runtime self-test wacht op build |
| PEER-01 | Persistente known users | Peer hash, naam, endpoints, first/last seen historisch opgeslagen | Known Users 2.0 gebouwd; runtimevalidatie open |
| PEER-02 | Automatisch gedeelde bestanden inventariseren | Alleen normale View Shared Files-capability gebruiken; privacy/cooldown respecteren | Implementatie gebouwd; echte peer-runtimevalidatie open |
| PEER-03 | Eén geconsolideerde Known Users-weergave | Permanente view zonder automatische tab per peer | Implementatie gebouwd; runtimevalidatie open |
| PEER-04 | Oude/herstelde user-tabs herkennen | Restored share-data hash-gebaseerd hergebruiken zonder dubbele automatische aanvraag/tab | Deterministische duplicate-name gate aanwezig; runtime restored-tab test open |
| PEER-05 | Peer↔file historie | First/last seen en current/history per peer-file | Implementatie gebouwd; runtimevalidatie open |
| SEARCH-01 | Search 2 / historische zoekfunctie | Live + historische kennis, filters, saved searches, blockrules, bulk/export | Grote Search 2-tranche gebouwd op `af6f0070ad63d7f383cd8e9d84881b370ed9bf65`; runtimevalidatie open |
| LIB-01 | File Library | Historie, favorites, download later, download again, missing/relink en recovery | Library 2.0 implementatie gebouwd; runtimevalidatie open |
| INTEL-01 | Download intelligence | Historie gebruiken zonder protocolbreuk; automatische acties opt-in en meetbaar | Intelligence 2.0 gebouwd; 30/120s outcomes aanwezig; runtime Analysis/Assist/Automatic open |
| UI-01 | Moderne hoofdstructuur | Duidelijke permanente Next-workspaces inclusief Diagnostics | UI / Navigation Modernization 2.0 gebouwd; Diagnostics toegevoegd; runtime polish open |
| UI-02 | Dark/light mode | Persistente theme en leesbare Next controls | Next-lijsten/views grotendeels geharmoniseerd; resterende legacy dialogs/contextmenus open |
| UI-03 | Schaling en moderne layout | DPI-aware spacing/layout 100–200% | Gedeelde metrics en workspace-layout gebouwd; praktische DPI-matrix open |
| UI-04 | eMule Next branding | Preview-identiteit zonder protocolclaims | Preview-branding actief; Preview 2 productisering later |
| SESSION-01 | Sessiestatus herstellen | Relevante view/filter/sort/workspace state over restart behouden | Dashboard/Known Users/Search/Library/workspace state grotendeels persistent; runtimerestarttests open |
| DATA-01 | Lokale SQLite intelligence database | Migratiebaar schema, async writer, read-isolatie, backup/integrity/recovery | Totaal schema v3; pre-migration backup, 24h/5-retentie, restore, integrity, pruning en writerqueue diagnostics gebouwd op `57b468ff…`; runtime recoverytests open |
| CI-01 | Reproduceerbare source bootstrap | Gepinde source + idempotente activation-stage + completion gates | Activation-stage/audit/completion gates actief; nieuwe tranches krijgen final-state gates vóór MSBuild |

## Architectuurregels

1. **Geen database-I/O in network/UI/scheduler hotpaths.** Writes gaan naar queues; reads/maintenance/stress draaien in workers.
2. **Automatische discovery is geen handmatige Search-tab.** Automatische share-antwoorden worden verwerkt/opgeslagen zonder per-peer legacy tab; handmatige View Shared Files blijft klassiek.
3. **User identity is primair 16-byte userhash.** Naam is presentatie/migratiesignaal; endpoint alleen disambiguatie.
4. **Bestandsidentiteit is primair eD2K hash + size.** Bestandsnaam mag geen history/scheduler identiteit bepalen.
5. **Geen agressieve peer scanning.** Capability, concurrency, timeout, success-TTL en failure/denied cooldown blijven autoritatief.
6. **Historie en live status blijven gescheiden.**
7. **Integratie/activatie is idempotent en werkt in een staging-overlay.**
8. **Een build-success is geen runtime/protocol-success.** Static gates mogen echte eD2K/Kad/upload/downloadtests niet vervangen.
9. **Automatic blijft opt-in; Analysis only is de veilige default.**
10. **Dashboard, Transfers en Scheduler delen één canonical transfer-intelligence model.**
11. **Schedulerinterventies zijn bounded, cooled-down en meetbaar.**
12. **Alias/favorite/history-acties blijven hash-gebaseerd en verwijderen geen lokale metadata onbedoeld.**
13. **Recovery vernietigt nooit automatisch de enige corrupte databasekopie.** Restore valideert eerst en archiveert de huidige DB.
14. **Stress/self-tests mogen productie-netwerk en productie-database niet beïnvloeden.** De indextest is in-memory; writerqueue-stress gebruikt een tijdelijke disposable database.

## Uitvoeringsvolgorde

### Fase A — stabiele buildbasis
- Windows x64 build groen houden.
- Source/dependencies/activation-stage reproduceerbaar houden.
- Completion gates op de uiteindelijke materialized tree laten draaien.

### Fase B — peer knowledge en sessieherstel
- Known Users 2.0, automatic share storage, hash-based restore/deduplicatie.
- Implementatie/build gereed; runtime peer-matrix open.

### Fase C — Search 2 + Library 2
- Live/historical searchmodel, filters, saved searches, blockrules, bulk/export.
- Library history/favorites/download later/download again/relink/available-again.
- Implementatie/build gereed; runtimecases open.

### Fase D — Transfers / intelligence
- Canonical insights, scheduler persistence, bounded interventions en outcome-metingen.
- Implementatie/build gereed; runtimemodevergelijking open.

### Fase E — UI / navigation
- Gedeelde workspace styling/DPI, keyboard, persistent workspace, Diagnostics.
- Implementatie/build gereed; DPI/resize praktijktest open.

### Fase F — database/recovery hardening
- Schema v3, backup/integrity/restore/pruning/writerqueue diagnostics.
- Implementatie/build gereed op `57b468ffcbb2934007d664e98b9b44cb50e673a2`; runtime migration/recoverytests open.

### Fase G — performance / stress / protocol regression
- Deterministische ClientIndex/DownloadIndex stress.
- Tijdelijke echte async writerqueue-stress.
- Static legacy protocol-contract gate.
- Praktische runtime matrix voor server/Kad/upload/download/peer-share/scheduler/hash/UI-DPI.
- Implementatie in huidige `/goal`; lokale Release x64 build en runtime self-test nog bevestigen.

### Fase H — Preview 2 productisering
- Branding/versioning/release notes.
- Portable ZIP en installer.
- Preview 1 -> Preview 2 upgrade en clean install.
- Definitieve runtime-regressiematrix sluiten.

## Eerstvolgende acceptatietest

Na een succesvolle build van de huidige Performance / Stress / Protocol Regression 2.0-tranche:

1. open **Diagnostics**;
2. voer **Run stress self-test** uit;
3. verwacht PASS voor 10.000 ClientIndex + 5.000 DownloadIndex entries;
4. verwacht PASS voor 10.000 events door de tijdelijke async writerdatabase;
5. verwacht `queued=0`, `processed=10000`, `dropped=0`, `errors=0` voor die tijdelijke writer-self-test;
6. controleer dat de UI tijdens de test responsief blijft;
7. voer daarna de echte netwerk/runtimecases uit `docs/EMULE_NEXT_RUNTIME_TEST_MATRIX.md` uit; die blijven afzonderlijke acceptatie-eisen.

`goal-1-5` wordt niet naar `develop` gemerged zonder expliciete toestemming.
