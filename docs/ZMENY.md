# Přehled změn proti dodanému JSON prototypu

| Soubor | Změna |
|---|---|
| `netvision/schema.sql` | Relační schéma, klíče, indexy, kontroly a triggery. |
| `netvision/database.py` | Inicializace, verze, import a transakce. |
| `netvision/repository.py` | Rekonstrukce katalogu a řízené zápisy nastavení a historie. |
| `netvision/server.py` | HTTP API, kontrola požadavků a veřejných souborů, HTTP rozsahy videa. |
| `start_server.py` | Spouštění SQLite verze, rozpoznání vlastní instance a chybová hlášení. |
| `manage.py` | Kontrola, záloha, obnova, reset a explicitní přiřazení lokálního média. |
| `persistence.js` | Volání API, fronty zápisů, import starých nastavení a události historie. |
| `app.js` | Napojení rozhraní na API a oddělení lokálního výběru od dat profilu. |
| `index.html` | Načtení nové persistence a stavová zpráva s tlačítkem importu. |
| `styles.css` | Styl malé stavové zprávy; původní rozložení zachováno. |
| `Start NetVision.command`, `NetVision.app/Contents/MacOS/NetVision` | Odstranění přímého otevření bez serveru. |
| `tests/` | Databázové, API, údržbové, spouštěcí, regresní a prohlížečové kontroly. |
| `docs/`, `README.md`, `media/README.md` | Popis API, schéma, ERD, ověření a záznam nové iterace. |

Původní `data/db.json`, `data/db.js`, titulky a soubor `NetVision.app/Contents/Info.plist` jsou zachované. Původní soubory JSON/JS nejsou poskytovány přes HTTP ani používány jako náhradní provozní úložiště. Výpočet doporučení, filtrování a základní logika vysílacího plánu nebyly nahrazeny novými algoritmy. Porovnání adres média nyní normalizuje relativní HTTP cestu, aby opakovaný výběr stejného média zbytečně znovu nenačítal video.

Kontrolní součty původních souborů jsou v `docs/evidence/original-sha256.json`. Původní balíček mimo tuto pracovní kopii zůstal beze změny. Nová databáze není zpětně vydávána za součást původních šesti vývojových etap popsaných v bakalářské práci.
