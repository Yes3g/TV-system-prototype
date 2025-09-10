// Interface/app.js
const API = "http://localhost:4000/api";

const els = {
  refreshBtn: document.getElementById("refreshBtn"),
  channels: document.getElementById("channels"),
  programsTitle: document.getElementById("programsTitle"),
  // Livestream oblast
  livestreamButtons: document.getElementById("livestreamButtons"),
  liveStatus: document.getElementById("liveStatus"),
  liveVideo: document.getElementById("liveVideo"),
  stopLiveBtn: document.getElementById("stopLiveBtn"),
  // VOD oblast
  shows: document.getElementById("shows")
};

let selectedChannel = null;

// --- utils
async function getJSON(url, opts) {
  const res = await fetch(url, opts);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// --- render: channels left
function renderChannels(list) {
  els.channels.innerHTML = "";
  list.forEach(c => {
    const row = document.createElement("div");
    row.className = "channel-item";
    row.innerHTML = `
      <div class="channel-logo">${(c.key || c.name).slice(0,2).toUpperCase()}</div>
      <div>
        <div class="channel-name">${c.name}</div>
        <div class="channel-desc">${c.description || ""}</div>
      </div>
      <div><span class="badge">open</span></div>
    `;
    row.addEventListener("click", () => openChannel(c));
    els.channels.appendChild(row);
  });
}

// --- render: livestream buttons (optional per channel)
function renderLivestreamDefs(defs) {
  els.livestreamButtons.innerHTML = "";
  if (!defs || !defs.length) {
    els.livestreamButtons.innerHTML = `<span class="channel-desc">No livestreams for this channel.</span>`;
    return;
  }
  defs.forEach(d => {
    const btn = document.createElement("button");
    btn.className = "live-btn";
    btn.textContent = d.label || d.type;
    btn.addEventListener("click", () => startLive(selectedChannel.id, d.type));
    els.livestreamButtons.appendChild(btn);
  });
}

// --- render: vod grid
function renderShows(list) {
  els.shows.innerHTML = "";
  if (!list.length) {
    els.shows.innerHTML = `<div class="channel-desc">Žádné pořady</div>`;
    return;
  }
  list.forEach(s => {
    const card = document.createElement("div");
    card.className = "vod-card";
    card.innerHTML = `
      <div class="vod-thumb"></div>
      <div class="vod-title">${s.title}</div>
      <div class="vod-genre">${s.genre || "—"}</div>
    `;
    els.shows.appendChild(card);
  });
}

// --- render: live status + player
function renderLiveStatus(state) {
  const { isLive, channelId, startedAt, type, streamUrl } = state;
  if (!isLive) {
    els.liveStatus.textContent = "Livestream je vypnutý";
    els.liveVideo.querySelector("source").src = "";
    els.liveVideo.load();
    return;
  }
  els.liveStatus.textContent = `LIVE na kanálu #${channelId} [${type}] (od ${new Date(startedAt).toLocaleString()})`;
  const source = els.liveVideo.querySelector("source");
  source.src = streamUrl || "";
  els.liveVideo.load();
}

// --- flows
async function openChannel(channel) {
  selectedChannel = channel;
  els.programsTitle.textContent = `${channel.name} – Programs`;

  const [defs, vod] = await Promise.all([
    getJSON(`${API}/channels/${channel.id}/livestreams`),
    getJSON(`${API}/channels/${channel.id}/shows`)
  ]);

  renderLivestreamDefs(defs);
  renderShows(vod);

  // aktualizovat live status (globální)
  const live = await getJSON(`${API}/livestream/status`);
  renderLiveStatus(live);
}

async function startLive(channelId, type) {
  const live = await getJSON(`${API}/livestream/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ channelId, type })
  });
  renderLiveStatus(live);
}

async function stopLive() {
  const live = await getJSON(`${API}/livestream/stop`, { method: "POST" });
  renderLiveStatus(live);
}

// --- events
els.refreshBtn.addEventListener("click", init);
els.stopLiveBtn.addEventListener("click", stopLive);

// --- init
async function init() {
  const channels = await getJSON(`${API}/channels`);
  renderChannels(channels);

  // defaultně otevřeme první kanál (pohodlné pro demo)
  if (channels[0]) openChannel(channels[0]);
}
init().catch(console.error);