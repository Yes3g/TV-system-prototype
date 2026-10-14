# API a datová vrstva

Prohlížeč používá stejný origin jako Python server. SQLite čte a mění pouze backend. JSON v odpovědích je přenosový formát, nikoli druhé provozní úložiště. Databázová spojení jsou samostatná pro požadavek, s `foreign_keys=ON`, čekáním na zámek 5 s a explicitními transakcemi. Zápisy používají `BEGIN IMMEDIATE`, parametrizované hodnoty a automatický rollback při chybě.

## Rozhraní

| Metoda a cesta | Význam |
|---|---|
| GET `/api/health` | Identifikátor aplikace `netvision-sqlite-v1` a instance odvozená od složky projektu. |
| GET `/api/bootstrap` | Konzistentní snímek katalogu, profilů a historie, revize nastavení, stav jednorázového importu a token pro zápis. |
| GET `/api/users/{id}/settings` | `{settings: {subtitles, audio, autoplay}, revision}`. |
| PATCH `/api/users/{id}/settings` | Částečná změna: `{revision: 0, settings: {subtitles: "cs"}}`. Vrací potvrzené hodnoty a novou revizi. |
| GET `/api/users/{id}/history` | Historie profilu seřazená podle času posledního zápisu sestupně. |
| POST `/api/playback-sessions` | `{userId, episodeId}` → HTTP 201 a `{token}`. Samotné založení relace ještě nezapisuje historii. |
| PUT `/api/playback-sessions/{token}` | `{sequence: 1, watchedSeconds: 12.5, completed: false}` → potvrzení a čas zápisu UTC. |
| POST `/api/legacy-settings` | `{users: {"user-1": {settings: {subtitles: "cs"}}}}` → seznam `applied` a `skipped`. |

Zápisy vyžadují `Content-Type: application/json` a hlavičku `X-NetVision-Token` s hodnotou `apiToken` z bootstrapu. Token se mění při restartu serveru; otevřenou stránku pak obnovte. Je to ochrana lokálního rozhraní proti cizím webovým originům, nikoli uživatelská autentizace. CORS není povolen; kontrolují se `Host` a případný `Origin`. Tělo má limit 64 KiB.

Povolená nastavení: titulky `off`, `en`, `cs`; zvuk `original`, `cz-dub`; autoplay skutečný JSON boolean. ID musí existovat. Neznámé atributy zápisů se odmítají. API neumožňuje obecné SQL dotazy ani správu celého katalogu.

Chyby jsou JSON `{error: "…"}`. Používané stavy: 400 neplatná data, 403 odmítnutý host/origin/token, 404 neexistující profil nebo cesta, 405 nepovolená metoda u obsluhovaných cest, 409 konflikt revize/relace nebo opakovaný import, 413 velikost těla, 415 typ těla, 503 problém databáze. Nepodporované kombinace metod a ostatních API cest mohou vrátit 404.

## Souběh a význam historie

Nastavení používá optimistickou kontrolu revize. Dva zápisy stejné revize nemohou oba uspět. Frontend řadí změny každého profilu do fronty; po konfliktu načte aktuální stav, zruší staré čekající požadavky a vyzve k opakování změny. Odpověď starého profilu neaplikuje do přehrávače nového profilu.

Historie má primární klíč `(user_id, episode_id)`. `watched_seconds` znamená poslední pozici přehrávače, může tedy po zpětném posunu klesnout. `completed` popisuje stav posledního hlášeného přehrávání, nikoli historický součet ani trvalý důkaz zhlédnutí. Čas při zápisu určuje server v UTC; importované původní časové řetězce se zachovají.

Každé nové přehrávání dvojice dostane serverový token. Novější relace zneplatní předchozí token pro stejnou dvojici. V rámci relace musí `sequence` růst. Opožděné nebo duplicitní zápisy se odmítnou stavem 409. Při souběhu oken stejné dvojice vítězí nověji zahájená serverová relace. Toto pravidlo neporovnává neověřitelné hodiny jednotlivých klientů. Frontend řadí vytvoření relací i zápisy do společné fronty a zachovává identitu původní dvojice při přepnutí.

## Schéma a import

Autoritativní schéma je `netvision/schema.sql`, verze je `PRAGMA user_version=1`. Inicializace nové databáze provede DDL, import, kontrolu cizích klíčů a úplné porovnání rekonstruovaných dat s původním JSON v jedné transakci. Neúplný import se vrátí zpět. Sloupce `position` zachovávají pořadí kolekcí a spojovacích záznamů. Nepovinné `availability` a `sourceNote` se zachovávají jako nepovinné hodnoty.

Existující verze 1 s příznakem dokončené inicializace se znovu neimportuje. Neznámá verze ani neoznačené existující tabulky se nepřepisují. Opravy databáze se neprovádějí automatickým resetem.

Při budoucí změně schématu přidejte explicitní přechod z verze 1 na novou verzi: předem SQLite záloha, transakční DDL/DML, kontrola zachování dat a cizích klíčů, až poté zvýšení `user_version`. Test musí začínat reálnou databází předchozí verze. Tato dodávka obsahuje pouze první relační verzi a import z JSON; netvrdí, že obsahuje budoucí migrace, které ještě nebyly potřeba.

## Statické soubory

Veřejný seznam tvoří HTML, CSS, aplikační skripty a podporované soubory v `captions/` a `media/`. Adresářové výpisy, průchody `..`, symbolické odkazy, zdrojové Python soubory, importní JSON/JS, SQLite soubory a zálohy se neposkytují. Média podporují jeden HTTP byte range; vícenásobné rozsahy nejsou podporovány.
