import { action, connectSocket, icon, loadState, loadVoices, setConfig, store, toast } from "./core.js";
import live from "./pages/live.js";
import voices from "./pages/voices.js";
import reading from "./pages/reading.js";
import alerts from "./pages/alerts.js";
import commands from "./pages/commands.js";
import dynamics from "./pages/dynamics.js";
import overlays from "./pages/overlays.js";
import clips from "./pages/clips.js";
import guide from "./pages/guide.js";
import settings from "./pages/settings.js";

const PAGES = [live, voices, reading, alerts, commands, dynamics, overlays, clips, settings, guide];
const SECTIONS = { live: "Directo", voices: "Voz", alerts: "Interacción", overlays: "Stream", settings: "Sistema" };
let current = null;

function renderNav() {
  const nav = document.getElementById("nav");
  nav.innerHTML = PAGES.map((page) => `
    ${SECTIONS[page.id] ? `<div class="nav-section">${SECTIONS[page.id]}</div>` : ""}
    <button class="nav-item" data-page="${page.id}">${icon(page.icon)}<span>${page.label}</span>
      ${page.id === "live" ? '<span class="badge-dot" id="nav-live-dot"></span>' : ""}</button>`).join("");
  nav.addEventListener("click", (event) => {
    const button = event.target.closest("[data-page]");
    if (button) navigate(button.dataset.page);
  });
}

export function navigate(id) {
  const page = PAGES.find((item) => item.id === id) || PAGES[0];
  current?.unmount?.();
  current = page;
  document.querySelectorAll(".nav-item").forEach((el) => el.classList.toggle("active", el.dataset.page === page.id));
  const main = document.getElementById("main");
  main.innerHTML = "";
  main.scrollTop = 0;
  const root = document.createElement("div");
  root.className = "page";
  main.append(root);
  page.render(root);
  history.replaceState(null, "", `#${page.id}`);
}
window.lvsNavigate = navigate;

function renderQuickbar() {
  const tts = store.state.tts;
  const mute = document.getElementById("q-mute");
  mute.innerHTML = icon(tts.muted ? "mute" : "volume");
  mute.classList.toggle("on", tts.muted);
  const pause = document.getElementById("q-pause");
  pause.innerHTML = icon(tts.paused ? "play" : "pause");
  pause.classList.toggle("paused", tts.paused);
}

function renderLiveDot() {
  const dot = document.getElementById("nav-live-dot");
  if (!dot) return;
  const statuses = Object.values(store.state.platforms).map((p) => p.status);
  const status = ["connected", "reconnecting", "connecting", "waiting", "error"].find((s) => statuses.includes(s)) || "";
  dot.className = `badge-dot ${status}`;
}

function setupQuickbar() {
  document.getElementById("q-skip").innerHTML = icon("skip");
  document.getElementById("q-clear").innerHTML = icon("trash");
  document.getElementById("q-clip").innerHTML = icon("scissors");
  document.getElementById("q-mute").onclick = () => action("toggle_mute");
  document.getElementById("q-pause").onclick = () => action("pause");
  document.getElementById("q-skip").onclick = () => action("skip");
  document.getElementById("q-clear").onclick = () => action("clear_queue");
  document.getElementById("q-clip").onclick = async () => {
    const result = await action("clip", { reason: "botón del panel" });
    if (result.ok) toast("Clip guardado en OBS", "success");
  };
  const volume = document.getElementById("q-vol");
  const label = document.getElementById("q-vol-label");
  volume.value = store.state.config.audio.tts_volume;
  label.textContent = `${volume.value}%`;
  volume.oninput = () => {
    label.textContent = `${volume.value}%`;
    setConfig("audio.tts_volume", Number(volume.value));
  };
  renderQuickbar();
}

function onSocket(type, data) {
  const state = store.state;
  if (!state) return;
  switch (type) {
    case "tts.state":
      state.tts = data;
      renderQuickbar();
      break;
    case "platform.status":
      state.platforms[data.platform] = data;
      renderLiveDot();
      break;
    case "stats":
      state.stats = data;
      break;
    case "goals":
      state.goals = data;
      break;
    case "giveaway":
      state.giveaway = data;
      break;
    case "poll":
      state.poll = data;
      break;
    case "event":
      state.recent.push(data);
      if (state.recent.length > 300) state.recent.shift();
      break;
    case "notice":
      toast(data.text, data.level || "info");
      break;
    case "clip":
      toast(data.ok ? `🎬 Clip guardado (${data.reason})` : `Marca guardada: ${data.error || data.reason}`, data.ok ? "success" : "warning");
      break;
    case "voices":
      loadVoices();
      break;
  }
  current?.onEvent?.(type, data);
}

async function boot() {
  document.getElementById("brand-logo").innerHTML = icon("logo");
  try {
    await loadState();
  } catch {
    document.getElementById("main").innerHTML = '<div class="page"><div class="empty">No se pudo conectar con LiveVoice Studio. ¿Está abierto?</div></div>';
    setTimeout(boot, 2000);
    return;
  }
  document.getElementById("version").textContent = `v${store.state.version} · gratis`;
  renderNav();
  setupQuickbar();
  renderLiveDot();
  loadVoices().then(() => current?.onEvent?.("voices.loaded"));
  connectSocket(onSocket);
  const first = store.state.config.general.first_run;
  navigate(first ? "guide" : location.hash.slice(1) || "live");
  if (first) setConfig("general.first_run", false, { immediate: true });
}

boot();
