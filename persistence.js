/* SQLite persistence through the local API. No silent JSON/localStorage fallback. */
const NetVisionStore = (() => {
  let apiToken = "";
  const queues = new Map();
  function notify(message, error = false) {
    const el = document.getElementById("persistenceStatus");
    el.textContent = message;
    el.dataset.error = String(error);
  }
  async function api(path, method = "GET", body) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 12000);
    let response;
    try { response = await fetch(path, {
      signal: controller.signal,
      method, headers: body === undefined ? {} : {
        "Content-Type": "application/json", "X-NetVision-Token": apiToken
      }, body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store"
    }); } finally { clearTimeout(timeout); }
    const data = await response.json();
    if (!response.ok) {
      const error = new Error(data.error || `HTTP ${response.status}`);
      error.status = response.status;
      throw error;
    }
    return data;
  }
  async function bootstrap() {
    const data = await api("/api/bootstrap");
    apiToken = data.apiToken;
    delete data.apiToken;
    return data;
  }
  function queue(key, task) {
    const next = (queues.get(key) || Promise.resolve()).catch(() => {}).then(task);
    queues.set(key, next);
    return next;
  }
  const generations = new Map();
  function changeSettings(user, changes, refresh) {
    const generation = generations.get(user.id) || 0;
    // Intent is queued per profile; only confirmed settings reach the UI.
    return queue(`settings:${user.id}`, async () => {
      if ((generations.get(user.id) || 0) !== generation) return;
      notify("Saving settings…");
      try {
        const saved = await api(`/api/users/${encodeURIComponent(user.id)}/settings`, "PATCH", {
          revision: user.settingsRevision, settings: changes
        });
        user.settings = saved.settings;
        user.settingsRevision = saved.revision;
        refresh(user.id);
        notify("Settings saved.");
      } catch (error) {
        generations.set(user.id, generation + 1);
        try {
          const current = await api(`/api/users/${encodeURIComponent(user.id)}/settings`);
          user.settings = current.settings;
          user.settingsRevision = current.revision;
        } catch (_) { /* Keep last confirmed values, never mark the failed change saved. */ }
        refresh(user.id);
        notify(`Settings were not confirmed saved. ${error.message}`, true);
      }
    });
  }
  function setupLegacyImport(data, refresh) {
    const button = document.getElementById("importLegacy");
    let old;
    try { old = JSON.parse(localStorage.getItem("netvision-prototype-state")); } catch (_) {}
    if (data.legacyImportDone || !old?.users) return;
    button.hidden = false;
    button.addEventListener("click", async () => {
      if (!confirm("Import settings from this browser once? Profiles already changed in the database will be skipped.")) return;
      button.disabled = true;
      try {
        const result = await api("/api/legacy-settings", "POST", {users: old.users});
        const latest = await bootstrap();
        latest.users.forEach(source => {
          const target = data.users.find(u => u.id === source.id);
          if (target) { target.settings = source.settings; target.settingsRevision = source.settingsRevision; }
        });
        try { localStorage.removeItem("netvision-prototype-state"); } catch (_) {}
        data.legacyImportDone = true;
        button.hidden = true;
        refresh();
        notify(`Imported ${result.applied.length} profiles; skipped ${result.skipped.length}.`);
      } catch (error) {
        notify(`Import failed: ${error.message}`, true);
        button.disabled = false;
      }
    });
  }
  function trackPlayer(video) {
    let context = null;
    const pending = new Set();
    function submit(c, position, completed) {
      if (!c?.played || c.failed || !Number.isFinite(position)) return;
      const signature = `${position}:${completed}`;
      if (c.lastQueued === signature) return;
      c.lastQueued = signature;
      const sequence = ++c.sequence;
      const work = queue("history", async () => {
        if (c.failed) return;
        try {
          if (!c.token) {
            const session = await api("/api/playback-sessions", "POST", {userId: c.userId, episodeId: c.episodeId});
            c.token = session.token;
          }
          await api(`/api/playback-sessions/${encodeURIComponent(c.token)}`, "PUT", {
            sequence, watchedSeconds: position, completed
          });
        } catch (error) {
          if (error.status === 409) c.failed = true;
          c.lastQueued = null; // a later event may retry a transient failure
          notify(`Playback progress was not saved. ${error.message}`, true);
        }
      });
      pending.add(work);
      work.finally(() => pending.delete(work));
    }
    function flush() {
      if (context) submit(context, video.currentTime, video.ended);
    }
    video.addEventListener("playing", () => {
      if (!context || video.paused) return;
      context.played = true;
      context.lastTick = Date.now();
      flush();
    });
    video.addEventListener("timeupdate", () => {
      if (!context?.played || video.paused || Date.now() - context.lastTick < 5000) return;
      context.lastTick = Date.now();
      flush();
    });
    video.addEventListener("pause", flush);
    video.addEventListener("ended", flush);
    document.addEventListener("visibilitychange", () => { if (document.hidden) flush(); });
    window.addEventListener("pagehide", flush); // best effort; periodic writes are primary
    return {
      select(userId, episodeId) {
        if (context?.userId === userId && context?.episodeId === episodeId) return;
        flush();
        video.pause();
        context = {userId, episodeId, sequence: 0, played: false, lastTick: 0, token: null, failed: false};
      },
      flush, idle: () => Promise.all([...pending])
    };
  }
  return {api, bootstrap, changeSettings, setupLegacyImport, trackPlayer, notify};
})();
