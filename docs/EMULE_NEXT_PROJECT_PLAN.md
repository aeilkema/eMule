# eMule Next — projectplan en traceability

Dit document is de leidraad voor de modernisering van eMule. Nieuwe wijzigingen op `develop` moeten aan een requirement hieronder gekoppeld kunnen worden. Een backendklasse geldt niet als "klaar" zolang de runtime-koppeling en, waar van toepassing, de gebruikersinterface ontbreken.

De concrete operationele werklijst staat in `docs/EMULE_NEXT_TODO.md`. Het projectplan beschrijft **wat** eMule Next moet worden; de TODO beschrijft **wat we hierna daadwerkelijk uitvoeren**.

## Doel

eMule moderniseren zonder de bewezen eD2K/Kad-protocolkern onnodig te herschrijven. De bestaande netwerkcompatibiliteit blijft leidend; nieuwe functies worden eromheen gebouwd als testbare services met een moderne, responsieve interface.

## Hoofdrequirements

| ID | Requirement | Acceptatiecriterium | Status |
|---|---|---|---|
| CORE-01 | Windows 10/11 x64 moderne build | Schone Release x64 build in lokale Build Tools; artifact wordt gepubliceerd | Groen op huidige `goal-1-5`-build; doorlopend bewaken |
| CORE-02 | Oude eMule-protocollen compatibel houden | eD2K/Kad, bestaande downloads/uploads en handmatige View Shared Files blijven werken | Doorlopend; volledige regressiematrix vóór Preview 2 |
| PERF-01 | Interface mag niet blokkeren door nieuwe functies | Databasewrites, history-reads en automatische shared-file verwerking gebeuren buiten zware legacy GUI-inserts | Ver gevorderd: scheduler/history/telemetry async, Search/Library/Known Users achtergrondwerk; verdere UI-stresstest nodig |
| PERF-02 | Snellere lookups | Client- en downloadindex vervangen lineaire scans waar veilig, met compatibiliteitsfallback | Actief; hardening/stale-entry tests nog nodig |
| PEER-01 | Persistente known users | Peer hash, naam, endpoints, first/last seen worden historisch opgeslagen | Actief en functioneel; UI-detailuitbreiding nog nodig |
| PEER-02 | Automatisch gedeelde bestanden inventariseren | Alleen normale eMule View Shared Files-functionaliteit gebruiken; privacy/denial respecteren; throttling/cooldown | Actief / runtime-verfijning |
| PEER-03 | Eén geconsolideerde Known users-weergave | Permanente tab met users boven en bekende bestanden van geselecteerde user onder; geen automatische tab per peer | Actief; background refresh en begrenzing aanwezig; UX/filtering uitbreiden |
| PEER-04 | Oude/herstelde user-tabs herkennen | Herstelde View Shared Files-resultaten worden bij reconnect aan dezelfde peer gekoppeld en geïmporteerd; geen dubbele automatische aanvraag/tab | In uitvoering; runtime-deduplicatietest nog open |
| PEER-05 | Peer↔file historie | Vastleggen wanneer een bestand bij een peer is gezien, inclusief first/last seen | Actief; verdere UI-weergave nog nodig |
| SEARCH-01 | Search 2 / historische zoekfunctie | Zoeken in actuele + historische filekennis, filters, blockregels, saved searches | Actief; async/background basis en begrenzing aanwezig; live+historisch samenvoegen en UX blijven open |
| LIB-01 | File Library | Historie van gevonden/gedownloade bestanden, favorites, download later en herstelmogelijkheden | Actief; views/background load/filtering aanwezig; recovery/download-again/session-state nog open |
| INTEL-01 | Download intelligence | Historische bronnen/peers en downloadervaring gebruiken om downloads slimmer te hervatten/prioriteren zonder protocolbreuk | Sterk gevorderd: runtime scheduler, persisted history/telemetry, bounded source quality en Dashboard-koppeling aanwezig; result evaluation en verdere Transfers-integratie nog open |
| UI-01 | Moderne hoofdstructuur | Duidelijke views: Dashboard, Search, Library, Transfers, Settings | Actief: Dashboard/Search/Library/Known Users/Settings aanwezig; Transfers en hoofdstructuur verder moderniseren |
| UI-02 | Dark/light mode | Persistente dark-mode instelling, moderne donkere common controls en uiteindelijk volledige view-consistentie | Actief; resterende dialogs/contextmenus nog uniformeren |
| UI-03 | Schaling en moderne layout | Correcte DPI-scaling, consistente spacing, toolbar/tab/layout zonder oude vaste maatvoering waar mogelijk | In uitvoering: gedeelde `EmuleNextUiMetrics` aanwezig; praktijktests op 100–200% en verdere vaste-maten cleanup nog open |
| UI-04 | eMule Next branding | Nieuwe functies herkenbaar maar zonder protocolcompatibiliteit te suggereren die niet bestaat | Actief; Preview-branding aanwezig; Preview 2 productisering later |
| SESSION-01 | Sessiestatus herstellen | Relevante historische/open UI-status wordt na restart herkend zonder dezelfde informatie opnieuw als nieuw te behandelen | In uitvoering; persistent scheduler history aanwezig, view-state en restored-tab gedrag nog verder afronden |
| DATA-01 | Lokale SQLite intelligence database | Migratiebaar schema, async writer, losse read-verbindingen, integrity/backup | Actief: async writer plus scheduler history/telemetry workers aanwezig; formele schema-migratie, backup en corruptieherstel nog open |
| CI-01 | Reproduceerbare source bootstrap | Officiële v0.72a source + gepinde dependencies + idempotente overlay/activatie | Actief en lokaal groen; activation-stage isolatie toegevoegd, verdere idempotence/runtime-validatie doorlopend |

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
- Historische peer/source-informatie zichtbaar maken zonder huidige downloadlogica onveilig te vervangen.
- Persistente scheduler/history-data gebruiken zonder SQLite in scheduler/UI hot paths.
- Transfers view moderniseren en dezelfde canonical transfer-insight builder gebruiken als Dashboard/Scheduler.
- Resultaat van schedulerinterventies meten zodat intelligence zichzelf kan evalueren.

### Fase E — volledige UI-modernisering
- Dashboard verder afwerken als operationele cockpit.
- Moderne navigatie voor Search / Known users / Library / Transfers / Settings.
- Dark/light mode over alle schermen en dialogs.
- DPI/scaling, spacing, iconografie en eMule Next branding.
- View-state, kolommen, filters en sorteringen waar nuttig over sessies herstellen.

### Fase F — hardening en Preview 2
- Formele database schema-migraties, backup en integrity/recovery.
- Performance/stresstests op grote queues, shares en databases.
- Volledige eD2K/Kad/upload/A4AF/rare-part/restart regressiematrix.
- Portable/installer/upgrade-tests en Preview 2 release notes.

## Huidige eerstvolgende acceptatietest

Na de succesvolle lokale `goal-1-5` build moet de runtime-smoketest aantonen dat:

1. automatisch gevonden shared files **geen nieuwe user-searchtab** meer openen;
2. grote shared-file lijsten de interface niet meer blokkeren door legacy list-inserts;
3. `Known users` als permanente view aanwezig is en users + files uit de SQLite-history toont;
4. een herstelde user-tab bij reconnect wordt herkend/geïmporteerd en niet meteen opnieuw automatisch wordt geopend;
5. dark mode actief kan zijn en de instelling wordt onthouden;
6. Search 2 missing/favorites/saved-search/block-functionaliteit bruikbaar blijft en background-acties geen zichtbare UI-freeze veroorzaken;
7. Library filtering bij snel typen niet meer de volledige list-control op iedere toetsaanslag herbouwt;
8. Dashboard/Scheduler historische rate, scheduler state en persisted diagnostics tonen zonder UI-stalls;
9. Analysis only geen netwerk/schedulerkeuzes verandert;
10. Automatic-mode alleen begrensde, feature-gated interventies uitvoert en legacy protocolrestricties respecteert.

Daarna volgen de P0-taken uit `docs/EMULE_NEXT_TODO.md`; het project valt niet terug op alleen backend-stubs.