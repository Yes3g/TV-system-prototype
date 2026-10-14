# Relační model NetVision SQLite

Diagram vychází z implementovaného schématu `netvision/schema.sql`. Úplný diagram všech atributů a klíčů je v [schema.mmd](schema.mmd), ve formátu Mermaid `erDiagram`. Přehledové SVG diagramy zobrazují klíče a jsou rozděleny podle oblastí pro čitelnost:

- [Katalog a média](01-obsah.svg)
- [Profily a preference](02-profily.svg)
- [Vysílací plán](03-prehravani.svg)
- [Historie a přehrávací relace](04-historie.svg)

Zdroj: vlastní zpracování podle implementované SQLite databáze této vývojové iterace. SVG diagramy jsou přehledy klíčů, nikoli úplný seznam atributů. Entity opakované v několika obrázcích označují stejné tabulky. Vazby přes hranice oblastí jsou kompletně uvedeny v `schema.mmd` a v SQL.

## Legenda a význam

PK označuje primární klíč, FK cizí klíč. Více atributů označených PK v jedné tabulce tvoří společně složený klíč. Vztah 1 → 0..N znamená, že potomek má právě jednoho rodiče, zatímco rodič může mít nula až více potomků. U `settings` je vztah k `users` 1 → 0..1 na úrovni databázových omezení; import a aplikace vytvářejí právě jeden záznam nastavení pro každý profil. Samotný cizí klíč však existenci nastavení pro každého rodiče nevynucuje.

`channels.region` odkazuje do tabulky `regions`. Naproti tomu `users.home_region` je zobrazovaný text, nikoli tentýž číselník. Například „Prague“ zůstává textem, zatímco `prague` je kód regionální dostupnosti.

Vztahy M:N jsou rozloženy do `program_genres`, `favorite_channels`, `favorite_programs`, `genre_weights` a `allowed_regions`. Číselné váhy a pořadí jsou vlastní atributy vztahů. `subtitle_tracks`, `media_audio_options` a `schedule_days` reprezentují opakované položky jako samostatné záznamy.

`watch_history` je souhrn pro dvojici profil–epizoda, nikoli protokol každé jednotlivé návštěvy. `playback_sessions` je pomocná tabulka pro odmítání zastaralých zápisů; aplikace udržuje nejnovější relaci pro dvojici. `metadata` ukládá výchozí profil a příznaky dokončeného importu, nemá cizí klíče. Hodnota výchozího profilu se při importu explicitně ověřuje.

## Integrita a odstranění

Cizí klíče jsou aktivní na každém spojení. Odstranění uživatele odstraňuje jeho nastavení, preference, historii a relace (`CASCADE`). Odstranění pořadu odstraňuje přiřazené žánry, ale existující epizody jeho odstranění blokují. Odstranění média blokují odkazující epizody; titulkové stopy a zvukové možnosti se jinak odstraní s médiem. Odstranění epizody blokuje existující plán nebo historie. Katalog se veřejným API nemaže.

Triggery kontrolují, že kanál plánu odpovídá kanálu pořadu příslušné epizody. Kontrola platí i při změně pořadu epizody nebo kanálu pořadu. Rozsahy vah, boolean hodnoty a formát hodin jsou omezeny pomocí `CHECK`. Sloupce `position` zachovávají původní pořadí, které ovlivňuje první epizodu, první oblíbený kanál a stabilní řazení doporučení.
