# Zavedení relační databáze do prototypu NetVision

Tento záznam popisuje novou vývojovou iteraci dokončenou 13. 10. 2026. Navazuje na původní prototyp s JSON a nepřisuzuje databázovou implementaci dřívějším etapám případové studie. Je připraven jako podklad pro následnou aktualizaci bakalářské práce; dosavadní DOCX nebyl změněn.

## Důvod úpravy

Původní NetVision ukládal katalog a demonstrační profily do souboru JSON. Vazby mezi kanály, pořady, epizodami, médii, žánry a uživatelskými preferencemi byly reprezentovány identifikátory bez databázově vynucené referenční integrity. Nastavení se uchovávalo v prohlížeči a předvyplněná historie sledování se za běhu neaktualizovala.

Připomínka vedoucího poukazovala na to, že rozsah těchto vztahů odůvodňuje databázovou implementaci. Nová iterace proto zavedla SQLite, které zachovává lokální charakter prototypu a umožňuje vyjádřit vztahy, kontrolovat jejich konzistenci a provádět trvalé transakční zápisy. Volba nebyla podložena výkonnostním porovnáním databázových systémů; odpovídala rozsahu lokální aplikace a dostupnému Python serveru.

## Návrh a realizace

Architektura byla změněna na prohlížeč, HTTP API v Pythonu a relační databázi SQLite. Původní server poskytující statické soubory byl rozšířen o načítání katalogu, správu nastavení profilů a ukládání historie. JavaScript nadále zajišťuje vykreslení, vyhledávání, výpočet doporučení a časové označování programu. JSON se používá pro přenos odpovědí API, již však není provozním úložištěm.

Vzniklo 20 aplikačních tabulek. Vztahy M:N byly rozloženy do spojovacích tabulek. Klíče, kontroly hodnot a triggery chrání například soulad kanálu plánu s kanálem příslušného pořadu. Zobrazovaný region uživatele zůstal oddělen od kódů regionální dostupnosti. Pořadí původních kolekcí bylo zachováno, protože ovlivňuje výchozí výběr obsahu a řazení položek se stejným skóre.

Zdrojový kód a testy byly vytvořeny pomocí Codexu na základě uživatelem schváleného zadání této nové iterace. Automatické ověření proběhlo v oddělené pracovní kopii. Tento záznam nepředstavuje doklad samostatného uživatelského testování autorem práce ani opakování původního externího testování.

## Migrace a ukládání změn

Import původního souboru je transakční. Jeho ověření rekonstruuje původní strukturu z databáze a porovnává hodnoty, vazby, pořadí i nepovinné údaje. Převedeny byly 2 profily, 4 kanály, 10 pořadů, 23 epizod, 20 médií, 7 žánrů, 3 položky plánu a 2 původní záznamy historie. Další spuštění data nepřepisuje. Schéma má vlastní verzi a existující neznámá databáze se automaticky neresetuje.

Nastavení profilu se ukládá přes API s kontrolou revize. Při souběžné změně se zastaralý požadavek odmítne. Historie obsahuje poslední pozici videa, příznak dokončení a čas pro dvojici uživatel–epizoda. Zápis se váže na skutečné přehrávání a události přehrávače. Zpožděné zápisy jsou rozlišeny tokenem přehrávací relace a rostoucím pořadovým číslem. Samotný výběr epizody historii nevytváří.

## Ověření a omezení

Prošlo 18 testovacích metod pro databázi, API, údržbu a spuštění. Samostatná regresní kontrola potvrdila shodu vybraných původních funkcí. Ve skutečném Chrome proběhlo 15 kontrol včetně přehrávání vlastního testovacího videa, změn profilů a persistence po restartu. Podrobný rozsah a omezení jsou uvedeny v `OVERENI.md`.

Výsledkem je skutečná databázová implementace používaná aplikací. Ověření neprokazuje vyšší výkon, úsporu vývojového času ani připravenost k produkčnímu provozu. Výběr profilu stále nenahrazuje autentizaci a doporučování zůstává pravidlové. Zaznamenaná pozice není měřením celkové doby sledování. Původní soukromá videa nebyla součástí balíčku; databázová migrace proto sama neodstranila jejich nepřenositelné cesty. Přehrávání v testu používalo vlastní vytvořené médium.

## Ukázky skutečně implementovaného kódu

Následující výřezy jsou převzaty ze zdrojových souborů této iterace. Nejde o rekonstrukci historických verzí.

### Spojovací tabulka pořadů a žánrů

```sql
CREATE TABLE program_genres (program_id TEXT NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
 genre_id TEXT NOT NULL REFERENCES genres(id), position INTEGER NOT NULL, PRIMARY KEY(program_id,genre_id), UNIQUE(program_id,position));
```

Zdroj: vlastní zpracování, `netvision/schema.sql`, databázová iterace NetVision.

### Transakce se zpětným vrácením při chybě

```python
@contextmanager
def transaction(db):
    db.execute('BEGIN IMMEDIATE')
    try:
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
```

Zdroj: vlastní zpracování, `netvision/database.py`, databázová iterace NetVision.

### Zápis nastavení přes API s revizí

```javascript
        const saved = await api(`/api/users/${encodeURIComponent(user.id)}/settings`, "PATCH", {
          revision: user.settingsRevision, settings: changes
        });
        user.settings = saved.settings;
        user.settingsRevision = saved.revision;
        refresh(user.id);
```

Zdroj: vlastní zpracování, `persistence.js`, databázová iterace NetVision.
