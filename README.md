## Doporučené spuštění na macOS

Dvojklikem otevřete **NetVision.app** pro tento Mac nebo **NetVision LAN.app** pro telefon/tablet. Obě aplikace spusťte přímo z rozbalené složky; nepřesouvejte je samostatně. Nevyvolávají interaktivní zsh, takže se vyhnou chybě compinit z Terminálu.

LAN aplikace otevře stránku a zobrazí adresu pro Safari na telefonu. Dialog nechte otevřený; tlačítko **Zastavit server** server vypne. Ostatní spouštěče níže jsou alternativní.

# NetVision — kompletní pracovní verze

Multimediální prototyp s webovým rozhraním, Python serverem a SQLite databází. Zahrnuje mobilní rozložení a volitelný přístup přes místní síť. Dřívější samostatné HTML není potřeba.

## Spuštění na počítači
Požadavky: Python 3.10+ se sqlite3, aktuální prohlížeč. Externí Python balíčky nejsou potřeba. Windows 7 není podporovaná cílová platforma.

macOS: spusťte `Start NetVision.command`, nebo ve složce `python3 start_server.py`.
Windows: spusťte `Start NetVision Windows.bat`, nebo `py -3 start_server.py`.
Ponechte server spuštěný. Pokud dvojklik na Macu přeruší vlastní chyba zsh compinit, dokončete dotaz shellu a spusťte `/bin/bash` s cestou ke spouštěči v uvozovkách.

## Telefon a tablet
1. Na Macu spusťte `Start NetVision LAN.command`.
2. Připojte telefon ke stejné Wi-Fi a otevřete vypsanou adresu v Safari, například `http://192.168.1.20:4174/`.
3. Mac i server ponechte zapnutý. Server vypnete Ctrl+C. HTML neotevírejte jako náhled přílohy.

Spouštěč vybere první dostupné rozhraní en0–en2. Jinou adresu lze zadat ručně: `python3 start_server.py --lan 192.168.1.20`. Na Windows použijte `py -3` a vlastní IPv4 adresu z `ipconfig`. Při obsazeném portu přidejte `--port 4180`. Firewall musí umožnit spojení v soukromé síti; hostovská Wi-Fi může zařízení vzájemně oddělovat.

LAN je pro testování v důvěryhodné síti. Připojení uživatelé sdílejí profily, nastavení i historii; výběr profilu není autentizace. Server není určen pro veřejný internet. GitHub Pages tento Python/SQLite backend nespustí.

## Databáze a média
`var/netvision.sqlite3` vznikne při prvním spuštění z `data/db.json`. Balíček neobsahuje provozní databázi. Profily a výchozí historie jsou ukázková seed data. Nastavení a nová historie se ukládají na serveru. Prohlížeč si pamatuje vybraný profil/kanál, pokud to jeho úložiště dovoluje.

Archivní videa nejsou přibalena. Jejich cesty jsou relativní `media/nazev.mp4`. Chybějící video zobrazí chybu; katalog dále funguje. Pro externí demonstrační video vyberte Czech Television 1 a klepněte na přehrávání. Dostupnost externích videí závisí na poskytovateli a internetu.

Vlastní video vložte na serveru do `media/`; záznam případně upravte příkazem `python3 manage.py set-media MEDIA_ID media/video.mp4`. Absolutní `file://` cesty nejsou přenositelné na telefon. Zvuková volba je demonstrační stav. Doporučování používá váhy žánrů a oblíbené pořady, nikoli učený AI model.

## GitHub
Nahrajte obsah této složky. `.gitignore` vynechává databázi, logy, lokální videa a dočasné soubory. Zkontrolujte `git status` před commitem. Licence nebyla zvolena za autora; případnou licenci doplňte podle svého rozhodnutí.

## Testy
`python3 -m unittest discover -s tests -v` a `node tests/regression.cjs`.
Kompletní sada: `python3 tests/verify.py`; browserová část vyžaduje Node, Playwright a Chromium. Cesty lze nastavit pomocí `NODE`, `PLAYWRIGHT_MODULE`, `CHROME_EXECUTABLE`; výstupy pomocí `NETVISION_TEST_ARTIFACTS` (výchozí `test-results/`).

Aktuální výsledky: `docs/AKTUALNI-VERZE.md`. Starší dokumentace/evidence v docs zachycuje předchozí databázovou iteraci; aktuální způsob spuštění popisuje tento README. Údržba a zálohování: `python3 manage.py --help`.
