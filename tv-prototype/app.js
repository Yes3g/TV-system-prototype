const state = {
  db: null,
  activeChannelId: null,
  currentEpisodeId: null,
  searchQuery: "",
  currentMediaId: null,
  usingFallback: false
};

const STORAGE_KEY = "netvision-prototype-state";

const els = {
  screenTitle: document.getElementById("screenTitle"),
  videoPlayer: document.getElementById("videoPlayer"),
  loginSelect: document.getElementById("loginSelect"),
  subtitleSelect: document.getElementById("subtitleSelect"),
  audioSelect: document.getElementById("audioSelect"),
  autoplayToggle: document.getElementById("autoplayToggle"),
  searchInput: document.getElementById("searchInput"),
  searchCount: document.getElementById("searchCount"),
  channelKicker: document.getElementById("channelKicker"),
  programTitle: document.getElementById("programTitle"),
  programDescription: document.getElementById("programDescription"),
  episodeTitle: document.getElementById("episodeTitle"),
  playMode: document.getElementById("playMode"),
  matchScore: document.getElementById("matchScore"),
  subtitleStatus: document.getElementById("subtitleStatus"),
  audioStatus: document.getElementById("audioStatus"),
  clock: document.getElementById("clock"),
  userBadge: document.getElementById("userBadge"),
  channelTitle: document.getElementById("channelTitle"),
  regionStatus: document.getElementById("regionStatus"),
  showCount: document.getElementById("showCount"),
  channelList: document.getElementById("channelList"),
  liveList: document.getElementById("liveList"),
  showGrid: document.getElementById("showGrid"),
  recommendationList: document.getElementById("recommendationList")
};

function pad(value) {
  return String(value).padStart(2, "0");
}

function formatTime(date) {
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function byId(collection, id) {
  return collection.find((item) => item.id === id);
}

function currentUser() {
  return byId(state.db.users, state.db.currentUserId);
}

function currentSettings() {
  const user = currentUser();
  user.settings = user.settings || { subtitles: "off", audio: "original", autoplay: false };
  return user.settings;
}

function loadSavedState() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
  } catch {
    return {};
  }
}

function saveState() {
  const users = {};
  state.db.users.forEach((user) => {
    users[user.id] = { settings: user.settings };
  });
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    currentUserId: state.db.currentUserId,
    activeChannelId: state.activeChannelId,
    users
  }));
}

function applySavedState() {
  const saved = loadSavedState();
  if (saved.currentUserId && byId(state.db.users, saved.currentUserId)) {
    state.db.currentUserId = saved.currentUserId;
  }
  state.db.users.forEach((user) => {
    const savedUser = saved.users && saved.users[user.id];
    if (savedUser && savedUser.settings) {
      user.settings = { ...(user.settings || {}), ...savedUser.settings };
    }
  });
  if (saved.activeChannelId && byId(state.db.channels, saved.activeChannelId)) {
    state.activeChannelId = saved.activeChannelId;
  }
}

function channelPrograms(channelId) {
  return state.db.programs.filter((program) => program.channelId === channelId);
}

function programEpisodes(programId) {
  return state.db.episodes.filter((episode) => episode.programId === programId);
}

function episodeBundle(episodeId) {
  const episode = byId(state.db.episodes, episodeId);
  const program = byId(state.db.programs, episode.programId);
  const channel = byId(state.db.channels, program.channelId);
  const media = byId(state.db.mediaAssets, episode.mediaAssetId);
  return { episode, program, channel, media };
}

function isChannelAvailable(channel) {
  return currentUser().allowedRegions.includes(channel.region);
}

function weekdayKey(date) {
  return ["sun", "mon", "tue", "wed", "thu", "fri", "sat"][date.getDay()];
}

function minutesOfDay(value) {
  const [hours, minutes] = value.split(":").map(Number);
  return hours * 60 + minutes;
}

function isScheduleLive(item, now = new Date()) {
  const currentMinutes = now.getHours() * 60 + now.getMinutes();
  return item.days.includes(weekdayKey(now)) &&
    currentMinutes >= minutesOfDay(item.start) &&
    currentMinutes < minutesOfDay(item.end);
}

function scoreProgram(program) {
  const user = currentUser();
  const favoriteBoost = user.favoriteProgramIds.includes(program.id) ? 0.3 : 0;
  const genreScore = program.genreIds.reduce((sum, genreId) => {
    return sum + (user.genreWeights[genreId] || 0.1);
  }, 0) / Math.max(1, program.genreIds.length);
  return Math.min(1, genreScore + favoriteBoost);
}

function playEpisode(episodeId, mode = "on demand") {
  state.currentEpisodeId = episodeId;
  const { episode, program, channel, media } = episodeBundle(episodeId);
  const score = Math.round(scoreProgram(program) * 100);
  state.currentMediaId = media.id;
  state.usingFallback = false;

  document.documentElement.style.setProperty("--accent", channel.accent);
  els.screenTitle.textContent = channel.name;
  els.channelKicker.textContent = `${channel.shortName} · ${program.format}`;
  els.programTitle.textContent = program.title;
  els.programDescription.textContent = episode.description;
  els.episodeTitle.textContent = episode.title;
  els.playMode.textContent = mode;
  els.matchScore.textContent = `${score}%`;

  if (els.videoPlayer.getAttribute("src") !== media.src) {
    els.videoPlayer.poster = media.poster;
    els.videoPlayer.src = media.src;
    installSubtitleTracks(media);
  }
  applyPlayerSettings();
  if (currentSettings().autoplay) {
    els.videoPlayer.play().catch(() => {});
  }

  render();
}

function handleMediaError() {
  if (!state.currentEpisodeId || state.usingFallback) return;
  const { media } = episodeBundle(state.currentEpisodeId);
  if (!media.fallbackSrc) return;
  state.usingFallback = true;
  els.videoPlayer.src = media.fallbackSrc;
  els.programDescription.textContent = `${els.programDescription.textContent} Local media file is missing, so NetVision is using a sample fallback.`;
}

function installSubtitleTracks(media) {
  els.videoPlayer.querySelectorAll("track").forEach((track) => track.remove());
  (media.subtitleTracks || []).forEach((track) => {
    const node = document.createElement("track");
    node.kind = "subtitles";
    node.label = track.label;
    node.srclang = track.srclang;
    node.src = track.src;
    els.videoPlayer.appendChild(node);
  });
}

function applyPlayerSettings() {
  const settings = currentSettings();
  els.subtitleSelect.value = settings.subtitles || "off";
  els.audioSelect.value = settings.audio || "original";
  els.autoplayToggle.checked = Boolean(settings.autoplay);
  els.subtitleStatus.textContent = settings.subtitles === "off" ? "Off" : settings.subtitles.toUpperCase();
  els.audioStatus.textContent = settings.audio === "cz-dub" ? "Czech dub" : "Original";

  Array.from(els.videoPlayer.textTracks || []).forEach((track) => {
    track.mode = track.language === settings.subtitles ? "showing" : "disabled";
  });
}

function matchesSearch(text) {
  if (!state.searchQuery) return true;
  return text.toLowerCase().includes(state.searchQuery);
}

function renderChannels() {
  els.channelList.innerHTML = "";

  state.db.channels
    .filter((channel) => matchesSearch(`${channel.name} ${channel.shortName} ${channel.description}`))
    .forEach((channel) => {
    const user = currentUser();
    const available = isChannelAvailable(channel);
    const favorite = user.favoriteChannelIds.includes(channel.id);
    const button = document.createElement("button");
    button.type = "button";
    button.disabled = !available;
    button.className = `channel-button${channel.id === state.activeChannelId ? " is-active" : ""}`;
    button.style.setProperty("--accent", channel.accent);
    button.innerHTML = `
      <span class="swatch"></span>
      <span>
        <span class="channel-name">${channel.name}</span>
        <span class="channel-tagline">${favorite ? "Favorite" : channel.region}${available ? "" : " · unavailable"}</span>
      </span>
    `;
    button.addEventListener("click", () => {
      state.activeChannelId = channel.id;
      saveState();
      const firstEpisode = firstPlayableEpisode(channel.id);
      if (firstEpisode) playEpisode(firstEpisode.id);
      render();
    });
    els.channelList.appendChild(button);
    });
}

function firstPlayableEpisode(channelId) {
  const programs = channelPrograms(channelId);
  for (const program of programs) {
    const episode = programEpisodes(program.id)[0];
    if (episode) return episode;
  }
  return null;
}

function renderLiveBlocks() {
  const liveItems = state.db.scheduleItems.filter((item) => {
    const { episode, program } = episodeBundle(item.episodeId);
    return item.channelId === state.activeChannelId &&
      matchesSearch(`${program.title} ${episode.title} ${episode.description} ${item.block}`);
  });
  els.liveList.innerHTML = "";

  if (!liveItems.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No scheduled livestream blocks for this channel.";
    els.liveList.appendChild(empty);
    return;
  }

  liveItems.forEach((item) => {
    const { episode, program } = episodeBundle(item.episodeId);
    const live = isScheduleLive(item);
    const button = document.createElement("button");
    button.type = "button";
    button.className = `live-card${live ? " is-live" : ""}`;
    button.innerHTML = `
      <span>${item.start}-${item.end}</span>
      <strong>${program.title}</strong>
      <small>${live ? "Live now" : item.block}</small>
    `;
    button.addEventListener("click", () => playEpisode(episode.id, live ? "live stream" : "scheduled stream"));
    els.liveList.appendChild(button);
  });
}

function renderShows() {
  const programs = channelPrograms(state.activeChannelId);
  els.showGrid.innerHTML = "";
  let rendered = 0;

  programs.forEach((program) => {
    const episodes = programEpisodes(program.id);
    episodes.forEach((episode) => {
      if (!matchesSearch(`${program.title} ${program.description} ${episode.title} ${episode.description}`)) return;
      const media = byId(state.db.mediaAssets, episode.mediaAssetId);
      const thumbStyle = media.poster ? `style="background-image: url('${media.poster}')"` : "";
      const card = document.createElement("button");
      card.type = "button";
      card.className = `show-card${episode.id === state.currentEpisodeId ? " is-playing" : ""}`;
      card.innerHTML = `
        <span class="thumb${media.poster ? "" : " no-poster"}" ${thumbStyle}>${media.poster ? "" : "NV"}</span>
        <span class="show-copy">
          <strong>${episode.title}</strong>
          <small>${program.title} · S${episode.season} E${episode.episode}</small>
        </span>
      `;
      card.addEventListener("click", () => playEpisode(episode.id));
      els.showGrid.appendChild(card);
      rendered += 1;
    });
  });
  els.showCount.textContent = `${rendered}`;
}

function renderRecommendations() {
  const rows = state.db.programs
    .filter((program) => isChannelAvailable(byId(state.db.channels, program.channelId)))
    .filter((program) => matchesSearch(`${program.title} ${program.description}`))
    .map((program) => ({ program, score: scoreProgram(program) }))
    .sort((a, b) => b.score - a.score)
    .slice(0, 4);

  els.recommendationList.innerHTML = "";
  rows.forEach(({ program, score }) => {
    const channel = byId(state.db.channels, program.channelId);
    const episode = programEpisodes(program.id)[0];
    const button = document.createElement("button");
    button.type = "button";
    button.className = "recommendation";
    button.innerHTML = `
      <span>
        <strong>${program.title}</strong>
        <small>${channel.shortName} · ${Math.round(score * 100)}% match</small>
      </span>
      <span>›</span>
    `;
    button.addEventListener("click", () => {
      state.activeChannelId = channel.id;
      saveState();
      playEpisode(episode.id);
    });
    els.recommendationList.appendChild(button);
  });
}

function render() {
  if (!state.db) return;

  const user = currentUser();
  const channel = byId(state.db.channels, state.activeChannelId);
  els.clock.textContent = formatTime(new Date());
  els.userBadge.textContent = `${user.name} · ${user.homeRegion}`;
  els.channelTitle.textContent = `${channel.shortName} programs`;
  els.regionStatus.textContent = isChannelAvailable(channel) ? channel.region : "not available";

  renderChannels();
  renderLiveBlocks();
  renderShows();
  renderRecommendations();
  els.searchCount.textContent = state.searchQuery ? "filtered" : "all";
}

function renderLogin() {
  els.loginSelect.innerHTML = "";
  state.db.users.forEach((user) => {
    const option = document.createElement("option");
    option.value = user.id;
    option.textContent = `Log in: ${user.name}`;
    option.selected = user.id === state.db.currentUserId;
    els.loginSelect.appendChild(option);
  });
}

function bindControls() {
  els.videoPlayer.addEventListener("error", handleMediaError);

  els.loginSelect.addEventListener("change", () => {
    state.db.currentUserId = els.loginSelect.value;
    const user = currentUser();
    state.activeChannelId = user.favoriteChannelIds[0] || state.db.channels[0].id;
    saveState();
    const firstEpisode = firstPlayableEpisode(state.activeChannelId);
    if (firstEpisode) playEpisode(firstEpisode.id, "profile");
    render();
  });

  els.searchInput.addEventListener("input", () => {
    state.searchQuery = els.searchInput.value.trim().toLowerCase();
    render();
  });

  els.subtitleSelect.addEventListener("change", () => {
    currentSettings().subtitles = els.subtitleSelect.value;
    saveState();
    applyPlayerSettings();
  });

  els.audioSelect.addEventListener("change", () => {
    currentSettings().audio = els.audioSelect.value;
    saveState();
    playEpisode(state.currentEpisodeId, "on demand");
  });

  els.autoplayToggle.addEventListener("change", () => {
    currentSettings().autoplay = els.autoplayToggle.checked;
    saveState();
    applyPlayerSettings();
  });
}

async function init() {
  if (location.protocol === "file:" && window.NETVISION_DB) {
    state.db = window.NETVISION_DB;
  } else {
    try {
      const response = await fetch("data/db.json");
      state.db = await response.json();
    } catch (error) {
      if (!window.NETVISION_DB) throw error;
      state.db = window.NETVISION_DB;
    }
  }
  applySavedState();
  const user = currentUser();
  state.activeChannelId = state.activeChannelId || user.favoriteChannelIds[0] || state.db.channels[0].id;
  renderLogin();
  bindControls();
  const firstEpisode = firstPlayableEpisode(state.activeChannelId);
  if (firstEpisode) playEpisode(firstEpisode.id, "startup");
  setInterval(render, 15000);
}

init().catch((error) => {
  els.programTitle.textContent = "Could not load NetVision";
  els.programDescription.textContent = error.message;
});
