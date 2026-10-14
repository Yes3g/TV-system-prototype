CREATE TABLE metadata (key TEXT PRIMARY KEY NOT NULL, value TEXT NOT NULL);
CREATE TABLE regions (id TEXT PRIMARY KEY NOT NULL);
CREATE TABLE users (id TEXT PRIMARY KEY NOT NULL, name TEXT NOT NULL, home_region TEXT NOT NULL, position INTEGER NOT NULL UNIQUE);
CREATE TABLE settings (user_id TEXT PRIMARY KEY NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 subtitles TEXT NOT NULL CHECK(subtitles IN ('off','en','cs')), audio TEXT NOT NULL CHECK(audio IN ('original','cz-dub')),
 autoplay INTEGER NOT NULL CHECK(autoplay IN (0,1)), revision INTEGER NOT NULL DEFAULT 0 CHECK(revision>=0));
CREATE TABLE genres (id TEXT PRIMARY KEY NOT NULL, name TEXT NOT NULL, position INTEGER NOT NULL UNIQUE);
CREATE TABLE channels (id TEXT PRIMARY KEY NOT NULL, name TEXT NOT NULL, short_name TEXT NOT NULL, region TEXT NOT NULL REFERENCES regions(id),
 accent TEXT NOT NULL, description TEXT NOT NULL, position INTEGER NOT NULL UNIQUE);
CREATE TABLE media_assets (id TEXT PRIMARY KEY NOT NULL, kind TEXT NOT NULL, src TEXT NOT NULL, poster TEXT NOT NULL,
 duration_seconds REAL NOT NULL CHECK(duration_seconds>=0), source_note TEXT, position INTEGER NOT NULL UNIQUE);
CREATE TABLE media_audio_options (media_id TEXT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
 option TEXT NOT NULL, position INTEGER NOT NULL, PRIMARY KEY(media_id,option), UNIQUE(media_id,position));
CREATE TABLE subtitle_tracks (media_id TEXT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
 position INTEGER NOT NULL, label TEXT NOT NULL, srclang TEXT NOT NULL, src TEXT NOT NULL, PRIMARY KEY(media_id,position));
CREATE TABLE programs (id TEXT PRIMARY KEY NOT NULL, channel_id TEXT NOT NULL REFERENCES channels(id), title TEXT NOT NULL,
 format TEXT NOT NULL, description TEXT NOT NULL, availability TEXT, position INTEGER NOT NULL UNIQUE);
CREATE TABLE program_genres (program_id TEXT NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
 genre_id TEXT NOT NULL REFERENCES genres(id), position INTEGER NOT NULL, PRIMARY KEY(program_id,genre_id), UNIQUE(program_id,position));
CREATE TABLE episodes (id TEXT PRIMARY KEY NOT NULL, program_id TEXT NOT NULL REFERENCES programs(id), title TEXT NOT NULL,
 season INTEGER NOT NULL CHECK(season>=0), episode INTEGER NOT NULL CHECK(episode>=0), media_asset_id TEXT NOT NULL REFERENCES media_assets(id),
 duration_minutes REAL NOT NULL CHECK(duration_minutes>=0), description TEXT NOT NULL, position INTEGER NOT NULL UNIQUE);
CREATE TABLE allowed_regions (user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, region_id TEXT NOT NULL REFERENCES regions(id),
 position INTEGER NOT NULL, PRIMARY KEY(user_id,region_id), UNIQUE(user_id,position));
CREATE TABLE favorite_channels (user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, channel_id TEXT NOT NULL REFERENCES channels(id),
 position INTEGER NOT NULL, PRIMARY KEY(user_id,channel_id), UNIQUE(user_id,position));
CREATE TABLE favorite_programs (user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, program_id TEXT NOT NULL REFERENCES programs(id),
 position INTEGER NOT NULL, PRIMARY KEY(user_id,program_id), UNIQUE(user_id,position));
CREATE TABLE genre_weights (user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, genre_id TEXT NOT NULL REFERENCES genres(id),
 weight REAL NOT NULL CHECK(weight>=0 AND weight<=1), position INTEGER NOT NULL, PRIMARY KEY(user_id,genre_id), UNIQUE(user_id,position));
CREATE TABLE schedule_items (id TEXT PRIMARY KEY NOT NULL, channel_id TEXT NOT NULL REFERENCES channels(id), episode_id TEXT NOT NULL REFERENCES episodes(id),
 block TEXT NOT NULL, start TEXT NOT NULL CHECK(length(start)=5 AND start GLOB '[0-2][0-9]:[0-5][0-9]' AND substr(start,1,2)<'24'),
 end TEXT NOT NULL CHECK(length(end)=5 AND end GLOB '[0-2][0-9]:[0-5][0-9]' AND substr(end,1,2)<'24'), mode TEXT NOT NULL, position INTEGER NOT NULL UNIQUE);
CREATE TABLE schedule_days (schedule_id TEXT NOT NULL REFERENCES schedule_items(id) ON DELETE CASCADE,
 day TEXT NOT NULL CHECK(day IN ('mon','tue','wed','thu','fri','sat','sun')), position INTEGER NOT NULL,
 PRIMARY KEY(schedule_id,day), UNIQUE(schedule_id,position));
CREATE TABLE watch_history (user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, episode_id TEXT NOT NULL REFERENCES episodes(id),
 watched_seconds REAL NOT NULL CHECK(watched_seconds>=0), completed INTEGER NOT NULL CHECK(completed IN (0,1)), last_watched_at TEXT NOT NULL,
 position INTEGER NOT NULL UNIQUE, PRIMARY KEY(user_id,episode_id));
CREATE TABLE playback_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, token TEXT NOT NULL UNIQUE,
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, episode_id TEXT NOT NULL REFERENCES episodes(id), last_seq INTEGER NOT NULL DEFAULT 0);
CREATE INDEX sessions_pair ON playback_sessions(user_id,episode_id,id);
CREATE INDEX programs_channel ON programs(channel_id);
CREATE INDEX episodes_program ON episodes(program_id);
CREATE INDEX episodes_media ON episodes(media_asset_id);
CREATE INDEX schedule_channel ON schedule_items(channel_id);
CREATE INDEX schedule_episode ON schedule_items(episode_id);
CREATE INDEX history_episode ON watch_history(episode_id);
CREATE TRIGGER schedule_insert BEFORE INSERT ON schedule_items BEGIN
 SELECT CASE WHEN NEW.channel_id != (SELECT p.channel_id FROM episodes e JOIN programs p ON p.id=e.program_id WHERE e.id=NEW.episode_id)
 THEN RAISE(ABORT,'schedule channel mismatch') END; END;
CREATE TRIGGER schedule_update BEFORE UPDATE ON schedule_items BEGIN
 SELECT CASE WHEN NEW.channel_id != (SELECT p.channel_id FROM episodes e JOIN programs p ON p.id=e.program_id WHERE e.id=NEW.episode_id)
 THEN RAISE(ABORT,'schedule channel mismatch') END; END;
CREATE TRIGGER episode_channel_update BEFORE UPDATE OF program_id ON episodes BEGIN
 SELECT CASE WHEN EXISTS(SELECT 1 FROM schedule_items s JOIN programs p ON p.id=NEW.program_id WHERE s.episode_id=OLD.id AND s.channel_id!=p.channel_id)
 THEN RAISE(ABORT,'scheduled episode channel mismatch') END; END;
CREATE TRIGGER program_channel_update BEFORE UPDATE OF channel_id ON programs BEGIN
 SELECT CASE WHEN EXISTS(SELECT 1 FROM schedule_items s JOIN episodes e ON e.id=s.episode_id WHERE e.program_id=OLD.id AND s.channel_id!=NEW.channel_id)
 THEN RAISE(ABORT,'scheduled program channel mismatch') END; END;
