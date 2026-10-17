# Pracovní verze 17. 10. 2026

Kompletní SQLite aplikace s responzivním rozhraním a volitelným režimem LAN. Výchozí spuštění nadále používá loopback. `--lan IP` váže server na zadanou soukromou IPv4 adresu a přidává pouze tuto adresu do kontroly Host. Kontrola Origin a tokenu pro zápis zůstala zachována. LAN spuštění nepřepisuje stavový soubor místního spouštěče.

Mobilní stavové údaje a ovládání jsou ve dvou sloupcích. Výchozí HTML vysvětluje nutnost serveru i při neprovedení skriptů; po inicializaci vysvětlení zmizí. Databázová verze již ošetřuje odmítnutí zápisu localStorage. Na Windows se schema i seed čtou explicitně jako UTF-8.

Balíček neobsahuje provozní SQLite databázi, stav spouštěče, soukromá videa ani absolutní uživatelské cesty. Relativní cesty archivních médií odpovídají složce media. Původní nepoužívaný data/db.js byl odstraněn. Data/db.json zůstává zdrojem pro novou databázi; existující databáze se automaticky nepřepisuje.

## Ověření
- Původních 18 Python testů prošlo na macOS/Python 3.12.
- Regresní test doporučování, regionů, vazeb a vysílacího plánu prošel.
- Prošlo 15 browserových kontrol v Chrome včetně zápisu skutečného přehrávání testovacího média, obnovy po restartu, chyb zápisu a mobilního rozložení.
- Nový test LAN Host/Origin prošel: nepovolená adresa 403, povolená adresa 200, cizí Origin a jiná IP 403.
- Mobilní snímek ovládání vizuálně zkontrolován.

Přístup přes skutečnou Wi-Fi, fyzický iPhone/iPad a Windows nebyly v této iteraci otestovány. Browserové přehrávání používalo generované testovací video, nikoli externí archivní soubory. Starší evidence v docs/evidence je historická a nepředstavuje nové ověření mobilního Safari.

## Oprava spouštění Finderem
Přidána NetVision LAN.app, která nepoužívá interaktivní Terminál. Dialog zobrazuje adresu a umožňuje zastavit vlastní server. Tři jednotkové testy ověřily zastavení vlastního procesu, zachování existujícího serveru a hlášení nedostupné sítě. Spuštění přes Finder nebylo automaticky ověřeno.
