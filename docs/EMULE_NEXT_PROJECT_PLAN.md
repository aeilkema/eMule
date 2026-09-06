# eMule Next — projectplan en traceability

Dit document is de leidraad voor de modernisering van eMule. Nieuwe wijzigingen op `develop` moeten aan een requirement hieronder gekoppeld kunnen worden. Een backendklasse geldt niet als "klaar" zolang de runtime-koppeling en, waar van toepassing, de gebruikersinterface ontbreken.

De concrete operationele werklijst staat in `docs/EMULE_NEXT_TODO.md`. Het projectplan beschrijft **wat** eMule Next moet worden; de TODO beschrijft **wat we hierna daadwerkelijk uitvoeren**.

## Doel

eMule moderniseren zonder de bewezen eD2K/Kad-protocolkern onnodig te herschrijven. De bestaande netwerkcompatibiliteit blijft leidend; nieuwe functies worden eromheen gebouwd als testbare services met een moderne, responsieve interface.

## Hoofdrequirements

| ID | Requirement | Acceptatiecriterium | Status |
|---|---|---|---|
| CORE-01 | Windows 10/11 x64 moderne build | Schone Release x64 build in lokale Build Tools; artifact wordt gepubliceerd | Groen op vorige `goal-1-5` head; nieuwe Intelligence 2.0/Scheduler-completion head wacht op lokale buildbevestiging |
| CORE-02 | Oude eMule-protocollen compatibel houden | eD2K/Kad, bestaande downloads/uploads en handmatige View Shared Files blijven werken | Doorlopend; volledige regressiematrix vóór Preview 2 |
| PERF-01 | Interface mag niet blokkeren door nieuwe functies | Databasewrites, history-reads en automatische shared-file verwerking gebeuren buiten zware legacy GUI-inserts | Ver gevorderd: scheduler/history/telemetry async, persistent telemetry reader background-only, Search/Library/Known Users achtergrondwerk; runtime-stresstest blijft nodig |
| PERF-02 | Snellere lookups | Client- en downloadindex vervangen lineaire scans waar veilig, met compatibiliteitsfallback | Actief; hardening/stale-entry tests nog nodig |
| PEER-01 | Persistente known users | Peer hash, naam, endpoints, first/last seen worden historisch opgeslagen | Actief en functioneel; UI-detailuitbreiding nog nodig |
| PEER-02 | Automatisch gedeelde bestanden inventariseren | Alleen normale eMule View Shared Files-functionaliteit gebruiken; privacy/denial respecteren; throttling/cooldown | Actief / runtime-verfijning |
| PEER-03 | Eén geconsolideerde Known users-weergave | Permanente tab met users boven en bekende bestanden van geselecteerde user onder; geen automatische tab per peer | Actief; background refresh en begrenzing aanwezig; UX/filtering uitbreiden |
| PEER-04 | Oude/herstelde user-tabs herkennen | Herstelde View Shared Files-resultaten worden bij reconnect aan dezelfde peer gekoppeld en geïmporteerd; geen dubbele automatische aanvraag/tab | In uitvoering; runtime-deduplicatietest nog open |
| PEER-05 | Peer↔file historie | Vastleggen wanneer een bestand bij een peer is gezien, inclusief first/last seen | Actief; verdere UI-weergave nog nodig |
| SEARCH-01 | Search 2 / historische zoekfunctie | Zoeken in actuele + historische filekennis, filters, blockregels, saved searches | Actief; async/background basis en begrenzing aanwezig; live+historisch samenvoegen en UX blijven open |
| LIB-01 | File Library | Historie van gevonden/gedownloade bestanden, favorites, download later en herstelmogelijkheden | Actief; views/background load/filtering aanwezig; recovery/download-again/session-state nog open |
| INTEL-01 | Download intelligence | Historische bronnen/peers en downloadervaring gebruiken om downloads slimmer te hervatten/prioriteren zonder protocolbreuk | Implementatie hoofdlaag gereed op `goal-1-5`: canonical transfer insights, Dashboard/Transfers Intelligence 2.0, persistent history/decisions/outcomes, stale cleanup, action-specific cooldowns, 30/120s outcome-metingen en force/reset APIs; lokale build/runtimevalidatie nog nodig |
| UI-01 | Moderne hoofdstructuur | Duidelijke views: Dashboard, Search, Library, Transfers, Settings | Actief: Dashboard Intelligence 2.0/Search/Library/Known Users/Settings aanwezig; hoofdstructuur en overige Transfers-UX verder moderniseren |
| UI-02 | Dark/light mode | Persistente dark-mode instelling, moderne donkere common controls en uiteindelijk volledige view-consistentie | Actief; resterende dialogs/contextmenus nog uniformeren |
| UI-03 | Schaling en moderne layout | Correcte DPI-scaling, consistente spacing, toolbar/tab/layout zonder oude vaste maatvoering waar mogelijk | In uitvoering: gedeelde `EmuleNextUiMetrics` aanwezig; Dashboard 2.0 gebruikt gedeelde metrics; praktijktests op 100–200% en verdere vaste-maten cleanup nog open |
| UI-04 | eMule Next branding | Nieuwe functies herkenbaar maar zonder protocolcompatibiliteit te suggereren die niet bestaat | Actief; Preview-branding aanwezig; Preview 2 productisering later |
| SESSION-01 | Sessiestatus herstellen | Relevante historische/open UI-status wordt na restart herkend zonder dezelfde informatie opnieuw als nieuw te behandelen | In uitvoering; Dashboard filter/sort/column-state persistent, scheduler history persistent; overige view-state en restored-tab gedrag nog verder afronden |
| DATA-01 | Lokale SQLite intelligence database | Migratiebaar schema, async writer, losse read-verbindingen, integrity/backup | Schedulerdeel formeel op schema v2 met additive upgradepad, async history/decision/outcome persistence, query-only telemetry reader en integrity/backup-smoketest; bredere automatische backup/corruptieherstel blijft P1 |
| CI-01 | Reproduceerbare source bootstrap | Officiële v0.72a source + gepinde dependencies + idempotente overlay/activatie | Actief: activation-stage isolatie, idempotente materialized Dashboard guard en completion gate aanwezig; nieuwe head lokaal nog buildbevestigen |

## Architectuurregels

1. **Netwerkthread/UI-thread niet belasten met database-I/O.** `Record*`-events gaan naar writer/background queues. Zwaardere history-queries draaien in background workers en leveren alleen het resultaat terug aan de UI.
2. **Automatische discovery is geen handmatige Search-tab.** Een automatisch ontvangen shared-file antwoord wordt geparsed en opgeslagen, maar niet file-voor-file in de legacy Search list geïnjecteerd. Een handmatige `View Shared Files` behoudt wel de klassieke tab.
3. **Identiteit is primair de user hash.** Gebruikersnaam is alleen een presentatie-/migratiesignaal. Bij herstelde legacy tabs zonder opgeslagen user hash mag alleen automatisch gekoppeld worden als de match ondubbelzinnig is; bij dubbele namen moet een endpointmatch uitsluitsel geven.
4. **Bestandsidentiteit is primair eD2K hash + size.** Bestandsnamen zijn presentatie-/fallbackdata en mogen geen scheduler/history-correlatie bepalen als een hash beschikbaar is.
5. **Geen agressieve peer scanning.** Alleen peers die de bestaande browse-share capability aankondigen worden gevraagd; concurrency, timeout, success-TTL en failure/denied cooldown blijven actief.
6. **Historie en live status zijn gescheiden.** Een user/file kan historisch bekend zijn zonder nu online te zijn. De UI moet dit zichtbaar onderscheiden.
7. **Idempotente integratie.** `integrate.py` en feature-activatie moeten tweemaal achter elkaar exact dezelfde source tree opleveren.
8. **Buildactivatie mag de echte checkout niet ongemerkt muteren.** Lokale feature-activatie gebeurt via een staging-overlay voordat naar de upstream-buildtree wordt gekopieerd.
9. **Een functie is pas klaar na runtime-test.** Alleen bestanden/classes toevoegen of compileren is niet voldoende.
10. **Automatische download-intelligence blijft opt-in.** `Analysis only` blijft de veilige standaard; legacy protocol- en schedulerbeperkingen blijven autoritatief.
11. **Dashboard, Transfers en Scheduler delen één canonical file-intelligence model.** Nieuwe file-level health/ETA/source-profielen mogen niet opnieuw als losse UI-berekeningen worden geïntroduceerd.
12. **Schedulerinterventies moeten evalueerbaar en stabiel zijn.** Interventies hebben action-specifieke cooldowns, anti-flapping en outcome-metingen; nieuwe automatisering mag niet onbeperkt dezelfde actie blijven herhalen zonder effectmeting.

## Uitvoeringsvolgorde

### Fase A — stabiele basis
- Windows x64 build groen houden.
- Gepinde dependencies en source bootstrap behouden.
- ClientIndex/DownloadIndex en SQLite writer stabiel houden.
- Buildactivatie geïsoleerd en reproduceerbaar houden.

### Fase B — peer knowledge en sessieherstel
- Automatische share-antwoorden loskoppelen van legacy Search UI.
- Restored user-tabs importeren en dedupliceren.
- Permanente **Known users** view leveren.
- Background refresh zonder UI-freeze.
- First/last seen en file-history zichtbaar maken.
- Runtime-gedrag bij dubbele namen/endpoints en denied/timeout valideren.

### Fase C — moderne Search en Library
- `Search2Service` koppelen aan nieuwe Search UI.
- Historische resultaten, missing-only, favorites, previously-downloaded en blockregels zichtbaar maken.
- Saved searches vanuit de UI opslaan, laden en verwijderen zonder database-I/O in herhaalde UI-refreshpaden.
- `FileLibraryService` koppelen aan Library UI met favorites/download later/herstel.
- Search en Library visueel als moderne eMule Next-workspaces uitwerken.
- Live en historische Search-resultaten uiteindelijk in één begrijpelijk model presenteren.

### Fase D — Transfers en intelligence
- `DownloadIntelligence` aan echte download lifecycle koppelen.
- Dashboard, Transfers en Scheduler dezelfde `CEmuleNextTransferInsights` laten gebruiken.
- Persistente scheduler/history-data gebruiken zonder SQLite in scheduler/UI hot paths.
- Schedulerinterventies met baseline + 30 s + 120 s outcomes evalueren.
- Stale snapshots opruimen en discovery/A4AF/rare-part cooldowns van elkaar scheiden.
- Persistente diagnostics via een query-only background reader beschikbaar maken.
- Deze fase is implementatie-technisch grotendeels afgerond op `goal-1-5`; lokale build/runtimevalidatie bepaalt of hij naar DONE kan.

### Fase E — volledige UI-modernisering
- Dashboard verder afwerken als operationele cockpit.
- Moderne navigatie voor Search / Known users / Library / Transfers / Settings.
- Dark/light mode over alle schermen en dialogs.
- DPI/scaling, spacing, iconografie en eMule Next branding.
- View-state, kolommen, filters en sorteringen waar nuttig over sessies herstellen.

### Fase F — hardening en Preview 2
- Formele database schema-migraties verder uitbreiden boven scheduler schema v2.
- Periodieke backup, integrity/recovery en corruptieherstel.
- Performance/stresstests op grote queues, shares en databases.
- Volledige eD2K/Kad/upload/A4AF/rare-part/restart regressiematrix.
- Portable/installer/upgrade-tests en Preview 2 release notes.

## Eerstvolgende acceptatietest

De nieuwe `goal-1-5` Intelligence 2.0 / Scheduler-completion build moet aantonen dat:

1. de Release x64-build volledig slaagt inclusief alle nieuwe completion/verifier gates;
2. de echte repository-overlay schoon blijft na `build-local.ps1`;
3. Dashboard opent en de extra filters Low health / Intervention / A4AF werken;
4. Dashboardkolommen sorteerbaar zijn en widths/sort/filter na heropenen worden hersteld;
5. live speed, historical speed, source quality/profile, last intervention en last useful source zichtbaar zijn;
6. Force analysis en Reset intelligence voor één download werken zonder crash/UI-freeze;
7. Transfers dezelfde file-level intelligence toont als Dashboard en geen oude duplicate signal-builder gebruikt;
8. Analysis only geen netwerk/schedulerkeuzes verandert;
9. Automatic-mode action-specifieke cooldown/anti-flapping respecteert;
10. applied interventions na 30 s en 120 s outcome-data opleveren;
11. persistent decisions/outcomes na restart teruggelezen kunnen worden;
12. schema-v2 upgrade op een bestaande Preview-database start zonder fout en integrity/backup intact blijft.

Na deze test worden de twee eerste intelligence-hoofdblokken in `docs/EMULE_NEXT_TODO.md` definitief DONE verklaard en kan de volgende `/goal`-ronde naar Known Users 2.0 verschuiven.
