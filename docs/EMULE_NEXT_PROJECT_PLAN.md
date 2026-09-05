# eMule Next — projectplan en traceability

Dit document is de leidraad voor de modernisering van eMule. Nieuwe wijzigingen op `develop` moeten aan een requirement hieronder gekoppeld kunnen worden. Een backendklasse geldt niet als "klaar" zolang de runtime-koppeling en, waar van toepassing, de gebruikersinterface ontbreken.

## Doel

eMule moderniseren zonder de bewezen eD2K/Kad-protocolkern onnodig te herschrijven. De bestaande netwerkcompatibiliteit blijft leidend; nieuwe functies worden eromheen gebouwd als testbare services met een moderne, responsieve interface.

## Hoofdrequirements

| ID | Requirement | Acceptatiecriterium | Status |
|---|---|---|---|
| CORE-01 | Windows 10/11 x64 moderne build | Schone Release x64 build in lokale Build Tools en GitHub Actions; artifact wordt gepubliceerd | Groen; lokaal en GitHub Actions bewezen, doorlopend bewaken |
| CORE-02 | Oude eMule-protocollen compatibel houden | eD2K/Kad, bestaande downloads/uploads en handmatige View Shared Files blijven werken | Doorlopend |
| PERF-01 | Interface mag niet blokkeren door nieuwe functies | Databasewrites, history-reads en automatische shared-file verwerking gebeuren buiten zware legacy GUI-inserts | In uitvoering |
| PERF-02 | Snellere lookups | Client- en downloadindex vervangen lineaire scans waar veilig, met compatibiliteitsfallback | Actief |
| PEER-01 | Persistente known users | Peer hash, naam, endpoints, first/last seen worden historisch opgeslagen | Actief |
| PEER-02 | Automatisch gedeelde bestanden inventariseren | Alleen normale eMule View Shared Files-functionaliteit gebruiken; privacy/denial respecteren; throttling/cooldown | Actief / verfijning |
| PEER-03 | Eén geconsolideerde Known users-weergave | Permanente tab met users boven en bekende bestanden van geselecteerde user onder; geen automatische tab per peer | Actief; runtime-test verder uitvoeren |
| PEER-04 | Oude/herstelde user-tabs herkennen | Herstelde View Shared Files-resultaten worden bij reconnect aan dezelfde peer gekoppeld en geïmporteerd; geen dubbele automatische aanvraag/tab | In uitvoering |
| PEER-05 | Peer↔file historie | Vastleggen wanneer een bestand bij een peer is gezien, inclusief first/last seen | Actief |
| SEARCH-01 | Search 2 / historische zoekfunctie | Zoeken in actuele + historische filekennis, filters, blockregels, saved searches | UI actief; missing-filter, saved searches, favorites en block-acties geïntegreerd |
| LIB-01 | File Library | Historie van gevonden/gedownloade bestanden, favorites, download later en herstelmogelijkheden | UI actief; verdere UX en herstelacties in uitvoering |
| INTEL-01 | Download intelligence | Historische bronnen/peers en downloadervaring gebruiken om downloads slimmer te hervatten/prioriteren zonder protocolbreuk | Backend aanwezig; runtime/UI verder integreren |
| UI-01 | Moderne hoofdstructuur | Duidelijke views: Dashboard, Search, Library, Transfers, Settings | Gedeeltelijk actief; Search/Library/Settings bestaan, Dashboard en Transfers volgen |
| UI-02 | Dark/light mode | Persistente dark-mode instelling, moderne donkere common controls en uiteindelijk volledige view-consistentie | Actief; instelling en common-control theming aanwezig |
| UI-03 | Schaling en moderne layout | Correcte DPI-scaling, consistente spacing, toolbar/tab/layout zonder oude vaste maatvoering waar mogelijk | Gepland |
| UI-04 | eMule Next branding | Nieuwe functies herkenbaar maar zonder protocolcompatibiliteit te suggereren die niet bestaat | Actief; Preview-branding aanwezig, hoofdvenster verder moderniseren |
| SESSION-01 | Sessiestatus herstellen | Relevante historische/open UI-status wordt na restart herkend zonder dezelfde informatie opnieuw als nieuw te behandelen | In uitvoering |
| DATA-01 | Lokale SQLite intelligence database | Migratiebaar schema, async writer, losse read-verbindingen, integrity/backup | Actief |
| CI-01 | Reproduceerbare source bootstrap | Officiële v0.72a source + gepinde dependencies + idempotente overlay/activatie | Actief en groen; idempotence-check en Windows build blijven verplicht |

## Architectuurregels

1. **Netwerkthread/UI-thread niet belasten met database-I/O.** `Record*`-events gaan naar de writer queue. Zwaardere history-queries draaien in background workers en leveren alleen het resultaat terug aan de UI.
2. **Automatische discovery is geen handmatige Search-tab.** Een automatisch ontvangen shared-file antwoord wordt geparsed en opgeslagen, maar niet file-voor-file in de legacy Search list geïnjecteerd. Een handmatige `View Shared Files` behoudt wel de klassieke tab.
3. **Identiteit is primair de user hash.** Gebruikersnaam is alleen een presentatie-/migratiesignaal. Bij herstelde legacy tabs zonder opgeslagen user hash mag alleen automatisch gekoppeld worden als de match ondubbelzinnig is; bij dubbele namen moet een endpointmatch uitsluitsel geven.
4. **Geen agressieve peer scanning.** Alleen peers die de bestaande browse-share capability aankondigen worden gevraagd; concurrency, timeout, success-TTL en failure/denied cooldown blijven actief.
5. **Historie en live status zijn gescheiden.** Een user/file kan historisch bekend zijn zonder nu online te zijn. De UI moet dit zichtbaar onderscheiden.
6. **Idempotente integratie.** `integrate.py` en feature-activatie moeten tweemaal achter elkaar exact dezelfde source tree opleveren.
7. **Een functie is pas klaar na runtime-test.** Alleen bestanden/classes toevoegen of compileren is niet voldoende.

## Uitvoeringsvolgorde

### Fase A — stabiele basis
- Windows x64 build groen houden.
- Gepinde dependencies en source bootstrap behouden.
- ClientIndex/DownloadIndex en SQLite writer stabiel houden.

### Fase B — peer knowledge en sessieherstel
- Automatische share-antwoorden loskoppelen van legacy Search UI.
- Restored user-tabs importeren en dedupliceren.
- Permanente **Known users** view leveren.
- Background refresh zonder UI-freeze.
- First/last seen en file-history zichtbaar maken.

### Fase C — moderne Search en Library
- `Search2Service` koppelen aan nieuwe Search UI.
- Historische resultaten, missing-only, favorites, previously-downloaded en blockregels zichtbaar maken.
- Saved searches vanuit de UI opslaan, laden en verwijderen.
- `FileLibraryService` koppelen aan Library UI met favorites/download later/herstel.
- Search en Library visueel als moderne eMule Next-workspaces uitwerken.

### Fase D — Transfers en intelligence
- `DownloadIntelligence` aan echte download lifecycle koppelen.
- Historische peer/source-informatie zichtbaar maken zonder huidige downloadlogica onveilig te vervangen.
- Transfers view moderniseren.

### Fase E — volledige UI-modernisering
- Dashboard.
- Moderne navigatie voor Search / Known users / Library / Transfers / Settings.
- Dark/light mode over alle schermen en dialogs.
- DPI/scaling, spacing, iconografie en eMule Next branding.

## Huidige eerstvolgende acceptatietest

De huidige Preview-build moet aantonen dat:

1. automatisch gevonden shared files **geen nieuwe user-searchtab** meer openen;
2. grote shared-file lijsten de interface niet meer blokkeren door legacy list-inserts;
3. `Known users` als permanente view aanwezig is en users + files uit de SQLite-history toont;
4. een herstelde user-tab bij reconnect wordt herkend/geïmporteerd en niet meteen opnieuw automatisch wordt geopend;
5. dark mode actief kan zijn en de instelling wordt onthouden;
6. Search 2 een `Missing only`-filter en werkende saved searches heeft;
7. de Release x64 lokale build en GitHub build groen blijven.

Daarna gaat de uitvoering door met File Library UX, download-intelligence in de echte lifecycle en de moderne hoofdstructuur; er wordt niet teruggevallen op alleen backend-stubs.
