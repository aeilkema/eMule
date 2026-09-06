# eMule Next — projectplan en traceability

Dit document is de leidraad voor de modernisering van eMule. Nieuwe wijzigingen op `develop` moeten aan een requirement hieronder gekoppeld kunnen worden. Een backendklasse geldt niet als "klaar" zolang de runtime-koppeling en, waar van toepassing, de gebruikersinterface ontbreken.

De concrete operationele werklijst staat in `docs/EMULE_NEXT_TODO.md`. Het projectplan beschrijft **wat** eMule Next moet worden; de TODO beschrijft **wat we hierna daadwerkelijk uitvoeren**.

## Doel

eMule moderniseren zonder de bewezen eD2K/Kad-protocolkern onnodig te herschrijven. De bestaande netwerkcompatibiliteit blijft leidend; nieuwe functies worden eromheen gebouwd als testbare services met een moderne, responsieve interface.

## Hoofdrequirements

| ID | Requirement | Acceptatiecriterium | Status |
|---|---|---|---|
| CORE-01 | Windows 10/11 x64 moderne build | Schone Release x64 build in lokale Build Tools; artifact wordt gepubliceerd | Release x64 groen op `goal-1-5` head `250f87f70029bd6cacb4cd10000206c50e7a442f`; Known Users 2.0 is de volgende buildtranche |
| CORE-02 | Oude eMule-protocollen compatibel houden | eD2K/Kad, bestaande downloads/uploads en handmatige View Shared Files blijven werken | Doorlopend; volledige regressiematrix vóór Preview 2 |
| PERF-01 | Interface mag niet blokkeren door nieuwe functies | Databasewrites, history-reads en automatische shared-file verwerking gebeuren buiten zware legacy GUI-inserts | Ver gevorderd: scheduler/history/telemetry async, Search/Library/Known Users achtergrondwerk; Known Users 2.0 gebruikt bounded query-only reads en async history-delete; runtime-stresstest blijft nodig |
| PERF-02 | Snellere lookups | Client- en downloadindex vervangen lineaire scans waar veilig, met compatibiliteitsfallback | Actief; hardening/stale-entry tests nog nodig |
| PEER-01 | Persistente known users | Peer hash, naam, endpoints, first/last seen worden historisch opgeslagen | Implementatie gereed in Known Users 2.0; first/last seen, endpoint, alias/favorite en live/history-status zichtbaar; lokale build/runtimevalidatie volgt |
| PEER-02 | Automatisch gedeelde bestanden inventariseren | Alleen normale eMule View Shared Files-functionaliteit gebruiken; privacy/denial respecteren; throttling/cooldown | Implementatie gereed: bestaande scanner-state wordt zichtbaar gemaakt en per-peer refresh respecteert denied/failure-cooldowns; echte peer-runtimevalidatie volgt |
| PEER-03 | Eén geconsolideerde Known users-weergave | Permanente tab met users boven en bekende bestanden van geselecteerde user onder; geen automatische tab per peer | Known Users 2.0 implementatie gereed met search, Current/History/Favorites/Recent, sortering, persistente viewstate en selected-peer detail/files |
| PEER-04 | Oude/herstelde user-tabs herkennen | Herstelde View Shared Files-resultaten worden bij reconnect aan dezelfde peer gekoppeld en geïmporteerd; geen dubbele automatische aanvraag/tab | Userhash blijft primaire match; endpoint-disambiguatie voor dubbele namen en deterministische duplicate-username gate aanwezig; echte restored-tab runtime-test blijft open |
| PEER-05 | Peer↔file historie | Vastleggen wanneer een bestand bij een peer is gezien, inclusief first/last seen | Implementatie gereed; file first/last seen en current-vs-history state zichtbaar; per-peer intelligence-history kan gecontroleerd worden verwijderd |
| SEARCH-01 | Search 2 / historische zoekfunctie | Zoeken in actuele + historische filekennis, filters, blockregels, saved searches | Actief; async/background basis en begrenzing aanwezig; live+historisch samenvoegen en UX blijven open |
| LIB-01 | File Library | Historie van gevonden/gedownloade bestanden, favorites, download later en herstelmogelijkheden | Actief; views/background load/filtering aanwezig; recovery/download-again/session-state nog open |
| INTEL-01 | Download intelligence | Historische bronnen/peers en downloadervaring gebruiken om downloads slimmer te hervatten/prioriteren zonder protocolbreuk | Hoofdlaag bouwbaar bevestigd op `250f87f70029bd6cacb4cd10000206c50e7a442f`: canonical transfer insights, Dashboard/Transfers Intelligence 2.0, persistent history/decisions/outcomes, stale cleanup, action-specific cooldowns, 30/120s outcome-metingen en force/reset APIs; runtimevalidatie blijft open |
| UI-01 | Moderne hoofdstructuur | Duidelijke views: Dashboard, Search, Library, Transfers, Settings | Actief: Dashboard Intelligence 2.0/Search/Library/Known Users 2.0/Settings aanwezig; hoofdstructuur en overige Transfers-UX verder moderniseren |
| UI-02 | Dark/light mode | Persistente dark-mode instelling, moderne donkere common controls en uiteindelijk volledige view-consistentie | Actief; resterende dialogs/contextmenus nog uniformeren |
| UI-03 | Schaling en moderne layout | Correcte DPI-scaling, consistente spacing, toolbar/tab/layout zonder oude vaste maatvoering waar mogelijk | In uitvoering: gedeelde `EmuleNextUiMetrics` aanwezig; Dashboard 2.0 en nieuwe Known Users 2.0-layout gebruiken gedeelde metrics; praktijktests op 100–200% en verdere vaste-maten cleanup nog open |
| UI-04 | eMule Next branding | Nieuwe functies herkenbaar maar zonder protocolcompatibiliteit te suggereren die niet bestaat | Actief; Preview-branding aanwezig; Preview 2 productisering later |
| SESSION-01 | Sessiestatus herstellen | Relevante historische/open UI-status wordt na restart herkend zonder dezelfde informatie opnieuw als nieuw te behandelen | Ver gevorderd: Dashboard filter/sort/column-state, scheduler history en Known Users mode/search/sort/column-state persistent; restored-tab runtimegedrag blijft te valideren |
| DATA-01 | Lokale SQLite intelligence database | Migratiebaar schema, async writer, losse read-verbindingen, integrity/backup | Schedulerdeel formeel op schema v2; Known Users 2.0 gebruikt bounded query-only read-service en async gecontroleerde peer-history delete; bredere automatische backup/corruptieherstel blijft P1 |
| CI-01 | Reproduceerbare source bootstrap | Officiële v0.72a source + gepinde dependencies + idempotente overlay/activatie | Actief: activation-stage isolatie en idempotentie bewezen op `250f87f...`; Intelligence- en Known Users 2.0-completion gates + activator-audit aanwezig; nieuwe Known Users-head lokaal nog buildbevestigen |

## Architectuurregels

1. **Netwerkthread/UI-thread niet belasten met database-I/O.** `Record*`-events gaan naar writer/background queues. Zwaardere history-queries draaien in background workers en leveren alleen het resultaat terug aan de UI.
2. **Automatische discovery is geen handmatige Search-tab.** Een automatisch ontvangen shared-file antwoord wordt geparsed en opgeslagen, maar niet file-voor-file in de legacy Search list geïnjecteerd. Een handmatige `View Shared Files` behoudt wel de klassieke tab.
3. **Identiteit is primair de user hash.** Gebruikersnaam is alleen een presentatie-/migratiesignaal. Bij herstelde legacy tabs zonder opgeslagen user hash mag alleen automatisch gekoppeld worden als de match ondubbelzinnig is; bij dubbele namen moet een endpointmatch uitsluitsel geven.
4. **Bestandsidentiteit is primair eD2K hash + size.** Bestandsnamen zijn presentatie-/fallbackdata en mogen geen scheduler/history-correlatie bepalen als een hash beschikbaar is.
5. **Geen agressieve peer scanning.** Alleen peers die de bestaande browse-share capability aankondigen worden gevraagd; concurrency, timeout, success-TTL en failure/denied cooldown blijven actief. Een handmatige per-peer refresh mag een oude success-TTL vernieuwen, maar geen privacy/failure-cooldown omzeilen.
6. **Historie en live status zijn gescheiden.** Een user/file kan historisch bekend zijn zonder nu online te zijn. De UI moet dit zichtbaar onderscheiden.
7. **Idempotente integratie.** `integrate.py` en feature-activatie moeten tweemaal achter elkaar exact dezelfde source tree opleveren.
8. **Buildactivatie mag de echte checkout niet ongemerkt muteren.** Lokale feature-activatie gebeurt via een staging-overlay voordat naar de upstream-buildtree wordt gekopieerd.
9. **Een functie is pas klaar na runtime-test.** Alleen bestanden/classes toevoegen of compileren is niet voldoende.
10. **Automatische download-intelligence blijft opt-in.** `Analysis only` blijft de veilige standaard; legacy protocol- en schedulerbeperkingen blijven autoritatief.
11. **Dashboard, Transfers en Scheduler delen één canonical file-intelligence model.** Nieuwe file-level health/ETA/source-profielen mogen niet opnieuw als losse UI-berekeningen worden geïntroduceerd.
12. **Schedulerinterventies moeten evalueerbaar en stabiel zijn.** Interventies hebben action-specifieke cooldowns, anti-flapping en outcome-metingen; nieuwe automatisering mag niet onbeperkt dezelfde actie blijven herhalen zonder effectmeting.
13. **Known Users-beheer blijft lokaal en hash-gebaseerd.** Alias/favorite/history-acties gebruiken de 16-byte userhash als identiteit; verwijderen van intelligence-history mag lokale alias/favorite-metadata niet onbedoeld wissen.

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
- Search + Current/History/Favorites/Recent filters leveren.
- First/last seen, endpoint, browse-status en file-history zichtbaar maken.
- Per-peer refresh en gecontroleerde lokale history-delete aanbieden.
- Persistente Known Users-viewstate herstellen.
- Implementatie is nu als Known Users 2.0 tranche gereed; lokale build en echte peer-runtimegedrag bepalen of Fase B volledig DONE kan worden.

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
- Deze fase is implementatie-technisch gereed en lokaal Release x64 bouwbaar bevestigd op `250f87f70029bd6cacb4cd10000206c50e7a442f`; runtimevalidatie bepaalt of hij volledig DONE kan worden.

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

De nieuwe `goal-1-5` Known Users 2.0 build moet aantonen dat:

1. de Release x64-build volledig slaagt inclusief `verify-known-users2.py`, de activator-audit en de algemene integratieverifier;
2. de echte repository-overlay schoon blijft na `build-local.ps1`;
3. de permanente Known Users-tab opent zonder UI-freeze en background user/file refresh blijft werken;
4. Search en Current / History / Favorites / Recent 7d correct filteren;
5. sortering, kolombreedtes, actieve mode en zoektekst na heropenen/restart worden hersteld;
6. first/last seen, endpoint, alias, favorite en browse-status correct zichtbaar zijn;
7. selected-peer files first/last seen en Current/History state tonen;
8. per-peer Refresh alleen de geselecteerde peer gebruikt en denied/timeout/error-cooldowns niet omzeilt;
9. success/denied/timeout/unsupported/error en resterende TTL/cooldown begrijpelijk zichtbaar worden;
10. Delete history asynchroon werkt, de peer-history verdwijnt en lokale alias/favorite behouden blijven;
11. restored View Shared Files-data bij reconnect op userhash wordt hergebruikt zonder dubbele automatische aanvraag/tab;
12. twee peers met dezelfde username maar verschillende hashes/endpoints afzonderlijk blijven in storage, UI en restored-tab matching.

Na een geslaagde build wordt de Known Users 2.0-head bovenaan in `docs/EMULE_NEXT_TODO.md` als nieuwe bewezen buildbasis vastgelegd. Na de echte runtimechecks kan Fase B volledig DONE worden verklaard en kan de volgende `/goal`-tranche naar Search 2.0 verschuiven.
