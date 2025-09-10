// Backend/server.js
const express = require("express");
const cors = require("cors");

const app = express();
app.use(cors());
app.use(express.json());

// --- MOCK DATA (zatím bez DB) ---
let channels = [
  { id: 1, key: "ct", name: "Česká televize", description: "Veřejnoprávní TV" },
  { id: 2, key: "prima", name: "Prima", description: "Komerční TV" },
  { id: 3, key: "nova", name: "Nova", description: "Komerční TV" },
  { id: 4, key: "cn", name: "Cartoon Network", description: "Animovaný program" },
  { id: 5, key: "discovery", name: "Discovery", description: "Dokumenty" }
];

let shows = [
  // VOD (on-demand) – hratelné kdykoliv
  { id: 101, channelId: 1, title: "Události", genre: "News" },
  { id: 102, channelId: 1, title: "168 hodin", genre: "News Magazine" },
  { id: 201, channelId: 2, title: "Show Jana Krause", genre: "Talk Show" },
  { id: 301, channelId: 3, title: "Ulice", genre: "Drama" },
  { id: 401, channelId: 4, title: "Gumball", genre: "Animation" },
  { id: 501, channelId: 5, title: "MythBusters", genre: "Documentary" }
];

// Livestream konfigurace per kanál (volitelné)
let channelLivestreams = {
  // klíč kanálu -> seznam typů, které umí
  ct:    [{ type: "news",  label: "News Livestream" }, { type: "sports", label: "Sports Livestream" }],
  prima: [{ type: "news",  label: "News Livestream" }],
  nova:  [{ type: "news",  label: "News Livestream" }, { type: "fun",    label: "Fun Livestream" }],
  cn:    [{ type: "fun",   label: "Fun Livestream" }],
  discovery: [] // žádný livestream = volitelné, může být prázdné
};

// Běžící livestream (globální mock stav)
let livestream = {
  isLive: false,
  channelId: null,
  type: null, // "news" | "sports" | "fun"
  startedAt: null,
  streamUrl: "sample-video.mp4"
};

// --- ROUTES ---
app.get("/api/channels", (_req, res) => res.json(channels));
app.get("/api/channels/:id/shows", (req, res) => {
  const id = Number(req.params.id);
  res.json(shows.filter(s => s.channelId === id));
});

// Livestream definice pro vybraný kanál (podle jeho "key")
app.get("/api/channels/:id/livestreams", (req, res) => {
  const id = Number(req.params.id);
  const ch = channels.find(c => c.id === id);
  if (!ch) return res.status(404).json({ error: "Channel not found" });
  const defs = channelLivestreams[ch.key] || [];
  res.json(defs);
});

// Aktuální stav
app.get("/api/livestream/status", (_req, res) => res.json(livestream));

// Spuštění livestreamu daného kanálu a typu
app.post("/api/livestream/start", (req, res) => {
  const { channelId, type } = req.body || {};
  if (!channelId || !type) {
    return res.status(400).json({ error: "channelId and type are required" });
  }
  const ch = channels.find(c => c.id === Number(channelId));
  if (!ch) return res.status(404).json({ error: "Channel not found" });

  const defs = channelLivestreams[ch.key] || [];
  if (!defs.some(d => d.type === type)) {
    return res.status(400).json({ error: "This channel does not provide the requested livestream type" });
  }

  livestream.isLive = true;
  livestream.channelId = Number(channelId);
  livestream.type = type;
  livestream.startedAt = new Date().toISOString();
  return res.json(livestream);
});

app.post("/api/livestream/stop", (_req, res) => {
  livestream.isLive = false;
  livestream.channelId = null;
  livestream.type = null;
  livestream.startedAt = null;
  return res.json(livestream);
});

// Healthcheck
app.get("/api/health", (_req, res) => res.json({ ok: true }));

const PORT = process.env.PORT || 4000;
app.listen(PORT, () => console.log(`Backend running on http://localhost:${PORT}`));