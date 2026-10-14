# Ověření databázové iterace

Datum ověření: 13. 10. 2026. Prostředí: macOS, Python 3.12.14, Chrome 155.0.8059.40 řízený prostřednictvím Playwright. Provozní kód nepoužívá Playwright ani jiné externí Python balíčky.

## Provedené automatické kontroly

| Oblast | Výsledek |
|---|---|
| Databáze, API, údržba a spouštění | 18 testovacích metod unittest prošlo. |
| Zákaz NULL v textových primárních klíčích | Ověřen v závěrečné sadě testů. |
| Regrese původní logiky | Prošlo porovnání skóre pro oba profily, dostupnosti všech kanálů, vazeb 23 epizod, první epizody kanálů a hranic vysílacího plánu. |
| Skutečný prohlížeč | Prošlo 13 kontrol běžící aplikace a 2 kontroly po restartu serveru a novém spuštění prohlížeče. |
| Import | Úplná rekonstrukce odpovídá původnímu JSON včetně nepovinných atributů a pořadí. |
| Integrita | Neplatné cizí klíče, rozpor kanálu vysílacího plánu, neplatné hodnoty a NULL klíče byly odmítnuty. |
| Transakce | Vadný import se vrátil zpět; následný import platných dat uspěl. |
| Souběh | Ze dvou současných změn stejné revize uspěla právě jedna; zastaralé sekvence a starý token historie byly odmítnuty. |
| Záloha a obnova | Ověřen reset s povinným potvrzením, automatická záloha, obnova původního nastavení a odmítnutí chybějící zálohy. |
| HTTP | Ověřeno blokování neveřejných souborů, symlinků, cizího originu, špatného tokenu a poskytování byte range videa. |
| Spouštění | Reálný spouštěč založil databázi a poskytl API i z jiného pracovního adresáře; rozpoznání odmítlo jinou aplikaci a jinou kopii NetVision. |

## Co proběhlo v prohlížeči

- Načtení katalogu přes API bez původního `db.js`.
- Otevření stránky bez vytvoření nové historie sledování.
- Změna titulků, zápis do SQLite a obnova po načtení stránky.
- Oddělení profilů a rychlá série změn nastavení.
- Skutečné přehrání vlastního testovacího WebM, pauza a ověření uložené pozice.
- Přepnutí profilu během přehrávání se zápisem k původnímu profilu.
- Změna epizody, uložení původního postupu a dokončení nové epizody.
- Opožděná odpověď nastavení bez přepsání rozhraní jiného profilu.
- Funkční filtrování vyhledávání.
- Simulovaná chyba zápisu s viditelným hlášením a návratem k potvrzenému nastavení.
- Potvrzený jednorázový import starších nastavení s přeskočením již změněných profilů.
- Kontrola horizontálního přetečení při šířce 390 px a absence nezachycených JavaScript výjimek.
- Ukončení testovacího serveru a prohlížeče, opětovné spuštění a kontrola persistence nastavení a historie.

Testovací video bylo vygenerováno jako jednoduchý barevný obrazec. V dočasné testovací databázi na něj byla přesměrována média; původní seed ani dodaná databáze tyto testovací cesty neobsahují. Test nepotřeboval soukromé videosoubory ani dostupnost externích video serverů.

Snímky desktopu, mobilního viewportu a ovládacích prvků byly vizuálně zkontrolovány. Jde o kontrolu v desktopovém Chrome s úzkým viewportem, nikoli test skutečného iOS zařízení.

Při prvním běhu kontroly rychlých změn nebyla správně synchronizována asynchronní podmínka testu. Test byl opraven na skutečné opakované čekání na databázovou hodnotu a závěrečný běh prošel. Původní problém testu není vykazován jako prokázaná chyba aplikace.

## Neověřené oblasti a omezení

- Windows, Safari/iOS a macOS spouštěč otevřený dvojklikem nebyly prakticky ověřeny. Terminálový Python spouštěč ověřen byl.
- Nebylo ověřeno přehrání 16 chybějících původních lokálních videí ani trvalá dostupnost čtyř externích zdrojů.
- Nebyl proveden zátěžový test ani benchmark JSON proti SQLite. Nelze tvrdit zvýšení výkonu nebo produktivity.
- Periodické ukládání používá interval přibližně 5 sekund; prohlížečový test přímo ověřil události spuštění, pauzy, přepnutí a dokončení. Náhlé ukončení procesu nebo zařízení nezaručuje uložení posledního neodeslaného úseku.
- Přehrávání není autentizovaná služba a regionální filtr není autorizace.

Testy jsou součástí `tests/`. Strojově čitelný seznam prohlížečových kontrol je v `docs/evidence/`. Postup spuštění je v README.
