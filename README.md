# NetVision SQLite

Lokální prototyp NetVision s relační databází. Jde o novou vývojovou iteraci navazující na původní JSON prototyp. Původní projekt ani bakalářská práce nebyly touto úpravou přepsány.

## Spuštění

Vyžaduje Python 3.10 nebo novější s modulem sqlite3. Aplikace nemá žádné závislosti instalované pomocí pip. ZIP nejprve rozbalte do zapisovatelné složky.

```sh
python3 start_server.py
```

Server automaticky vybere lokální adresu/port a otevře prohlížeč. Nechte terminál otevřený; Ctrl+C server ukončí. Na macOS lze použít `Start NetVision.command`. `NetVision.app` spouští server na pozadí, jeho log je ve `var/server.log`. Chcete-li snadno řídit zastavení serveru, použijte terminálovou variantu. Na Windows lze použít `py -3 start_server.py`; Windows ani iOS nebyly v této iteraci prakticky ověřeny.

Balíček obsahuje čistě importovanou databázi `var/netvision.sqlite3` s původními demonstračními daty. Pokud soubor chybí, na první spuštění vznikne automaticky. Další spuštění zachovávají změny. Proměnná `NETVISION_DB` umožňuje jinou cestu; relativní cesta se vyhodnocuje vůči složce projektu, nikoli pracovnímu adresáři terminálu. `NETVISION_NO_BROWSER=1` potlačí automatické otevření prohlížeče.

Přímé otevření `index.html` ani Live Server databázovou verzi nespustí. Aplikace vyžaduje vlastní Python server. Výchozí vazba je na loopback; služba není vystavena do sítě. Veřejné nasazení není součástí projektu.

## Co se ukládá

- SQLite obsahuje katalog, profily, vztahy, nastavení a historii sledování.
- Nastavení titulků, zvukové volby a autoplay se zapisují přes API. Potvrzení „Settings saved“ znamená potvrzený databázový zápis. Při chybě se zobrazí hlášení a rozhraní se vrátí k posledním potvrzeným hodnotám.
- Vybraný profil a kanál zůstávají v `localStorage` jako stav konkrétního prohlížeče. Nejde o autentizaci.
- Historie ukládá poslední pozici přehrávače, dokončení a čas posledního zápisu pro každou dvojici profil–epizoda. Pozice není součtem skutečně sledovaných sekund. Dokončení odpovídá události `ended`, nevypovídá o zhlédnutí všech částí videa.
- Zápis historie probíhá při skutečném spuštění, přibližně každých 5 sekund přehrávání, při pauze, dokončení a změně profilu/epizody. Samotné načtení stránky historii nevytváří.
- Při náhlém ukončení nebo ztrátě spojení může poslední neodeslaný úsek chybět. Přesun stránky do pozadí vyvolá doplňkový pokus o zápis, nikoli záruku doručení.
- Automatické pokračování z uložené pozice ani doporučování podle historie tato verze nezavádí.

`data/db.json` slouží výhradně jako výchozí importní soubor; `data/db.js` je zachován pouze jako historický podklad. Ani jeden soubor není veřejně poskytován ani načítán rozhraním.

## Starší nastavení prohlížeče

Pokud ve stejném webovém originu existuje původní klíč `netvision-prototype-state`, zobrazí se tlačítko pro jednorázový import. Import vyžaduje potvrzení. Profily změněné v databázi se přeskočí; původní hodnoty je nepřepíšou. Úspěch se označí v databázi, takže další prohlížeč nemůže import automaticky opakovat. Změna hostitele nebo portu znamená jiný origin; staré nastavení odtud prohlížeč automaticky zpřístupnit nemůže.

## Videa

Součástí původního seed souboru je 16 absolutních `file://` cest do autorova Downloads a 4 vzdálené HTTPS adresy. Lokální videa nejsou přibalena. Databázový import tyto údaje zachovává; nedokládá jejich dostupnost. Při neplatné lokální cestě rozhraní zobrazí vysvětlení. Vzdálená média vyžadují dostupnou síť a jejich poskytovatele.

Chcete-li zpřístupnit vlastní oprávněně užívané video:

1. Umístěte jej do složky `media/` v projektu, například `media/film.mp4`.
2. Zjistěte ID příslušného média v původním katalogu.
3. Nastavte HTTP cestu do databáze:

```sh
python3 manage.py set-media media-service-mbrs media/film.mp4
```

4. Obnovte stránku. Soubor se poskytuje přes HTTP s podporou rozsahových požadavků pro posun videa. Není nutné vystavovat Downloads ani ukládat video jako databázový BLOB.

## Záloha, obnova a reset

```sh
python3 manage.py check
python3 manage.py backup /cesta/k/netvision-zaloha.sqlite3
```

Záloha používá SQLite backup API. Existující cílovou zálohu nepřepisuje. Zálohujte zvlášť také vlastní média; databáze obsahuje pouze odkazy.

Před obnovou nebo resetem zastavte všechny instance serveru pracující s touto databází. Tyto operace jsou určeny pro údržbu mimo provoz, nikoli pro souběh s otevřeným serverem.

```sh
python3 manage.py restore /cesta/k/netvision-zaloha.sqlite3 --yes
python3 manage.py reset --yes
```

Obě operace nejprve vytvoří časově označenou zálohu existující databáze. Bez `--yes` se nic nenahrazuje. Obnova ověřuje verzi, integritu a cizí klíče. Reset založí novou databázi z původního JSON; odstraní tak dosavadní změny z aktivní databáze. Při chybě nevynucujte smazání databáze; přečtěte hlášení a použijte ověřenou zálohu.

## Vývoj a testy

Z kořene projektu:

```sh
python3 -m unittest discover -s tests -v
node tests/regression.cjs
```

První příkaz zahrnuje databázi, API a údržbu. HTTP testy potřebují možnost otevřít lokální port. Regresní test porovnává doporučování, regiony, vazby epizod, pořadí výchozího obsahu a vysílací časy s výsledky původního kódu.

Volitelné testy skutečného prohlížeče vyžadují Node, Playwright a Chromium/Chrome (pouze vývojové nástroje, nikoli závislosti aplikace):

```sh
python3 -m tests.run_browser
```

Podle prostředí lze nastavit `NODE`, `PLAYWRIGHT_MODULE`, `CHROME_EXECUTABLE` a `NETVISION_TEST_ARTIFACTS`. Test používá dočasnou databázi a vytváří vlastní krátké WebM video, které po skončení odstraní. Nečte osobní videa. Snímky zachycují testovací data, nikoli původní multimediální obsah.

## Dokumentace

- [API a datová vrstva](docs/API.md)
- [Datový model a ERD](docs/ERD.md)
- [Nová vývojová iterace pro bakalářskou práci](docs/ITERACE_DATABAZE.md)
- [Výsledky ověření](docs/OVERENI.md)
- [Přehled změn](docs/ZMENY.md)

Známá omezení původního prototypu zůstávají: zvuková volba mění nastavení a popisek, nikoli skutečnou zvukovou stopu; časové označení pořadu není živý přenos; doporučení jsou pravidlová. Vysílací plán stále používá místní čas prohlížeče a původní logiku bez intervalů přes půlnoc. Levé navigační ikony zůstávají demonstrační. SQLite a lokální API samy o sobě nepředstavují produkční zabezpečení ani škálovatelnou televizní službu.
