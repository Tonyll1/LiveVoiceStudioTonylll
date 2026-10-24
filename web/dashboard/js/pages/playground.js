import { action, bindForm, esc, getConfig, icon, store, switchHtml, toast, PLATFORM_LABEL } from "../core.js";

const KINDS = [
  ["chat", "💬 Mensaje"], ["follow", "💜 Follow"], ["gift", "🎁 Regalo"], ["sub", "⭐ Suscripción"],
  ["bits", "💎 Bits"], ["raid", "🚀 Raid"], ["share", "🔁 Compartir"], ["like", "❤️ Likes"], ["join", "👋 Entrada"],
];
const SCREENS = [
  ["all", "Todo en uno"], ["alerts", "Alertas"], ["chat", "Chat"], ["tts", "Subtítulos"], ["goal?goal=likes", "Meta"],
  ["events", "Actividad"], ["leaderboard", "Top regalos"], ["giveaway", "Sorteo"], ["poll", "Encuesta"], ["command", "Comandos"],
];
const CHAT_TESTS = ["!dado", "!moneda", "!voz ardilla", "!voz gringo", "!voz normal", "!bola ¿ganaré hoy?", "!amor Ana", "!puntos", "!top", "!voces"];
const SAMPLE_ENGINES = [
  ["edge", "Edge (neuronal)"], ["kokoro", "IA Kokoro (offline)"], ["elevenlabs", "IA ElevenLabs"], ["piper", "Piper (offline)"],
  ["sapi", "Windows (offline)"], ["google", "Google"], ["tiktok", "TikTok"],
];

let root, screen = "all", observer;

function sampleVoices() {
  return SAMPLE_ENGINES.map(([engine, label]) => {
    const voices = store.voices.filter((v) => v.engine === engine);
    const spanish = voices.filter((v) => v.language === "es");
    return { engine, label, voices: spanish.length ? spanish : voices };
  });
}

function render(target) {
  root = target;
  const kindOptions = KINDS.map(([id, label]) => `<option value="${id}">${label}</option>`).join("");
  root.innerHTML = `
    <div class="page-head"><div><h1>Campo de pruebas</h1><p>Simula un directo completo sin estar en vivo: eventos, comandos, voces y todos los overlays a la vez.</p></div></div>
    <div class="live-layout" style="grid-template-columns:minmax(0,1fr) 400px">
      <div class="stack">
        <div class="card flush">
          <div class="card-head"><h2>${icon("layers")}Vista del stream</h2>
            <div class="seg" id="screens">${SCREENS.map(([id, label]) => `<button data-screen="${id}" class="${id === screen ? "active" : ""}">${label}</button>`).join("")}</div></div>
          <div id="stage" style="position:relative;aspect-ratio:16/9;overflow:hidden;background:#1a1a24 url('data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2240%22 height=%2240%22><rect width=%2220%22 height=%2220%22 fill=%22%2320202c%22/><rect x=%2220%22 y=%2220%22 width=%2220%22 height=%2220%22 fill=%22%2320202c%22/></svg>')">
            <iframe id="screen" style="position:absolute;left:0;top:0;width:1920px;height:1080px;border:0;transform-origin:0 0"></iframe>
          </div>
          <div class="row small faint" style="padding:10px 14px">Así lo verán tus espectadores en OBS (1920×1080, fondo transparente). Los eventos que mandes aparecen aquí y en Directo.</div>
        </div>
        <div class="card">
          <h2>${icon("voice")}Comparador de voces</h2>
          <p class="sub">Escucha la misma frase con cada motor. Los que dicen “offline” funcionan sin internet.</p>
          <input class="input" id="voice-text" value="¡Hola chat! Gracias por el follow, bienvenidos al directo.">
          <div class="grid g3" style="margin-top:12px" id="voice-grid"></div>
        </div>
      </div>
      <div class="stack">
        <div class="card">
          <h2>${icon("wand")}Crear evento</h2>
          <div class="stack" style="margin-top:12px">
            <div class="grid g2">
              <label class="field"><span>Tipo</span><select class="input" id="ev-kind">${kindOptions}</select></label>
              <label class="field"><span>Plataforma</span><select class="input" id="ev-platform">${Object.entries(PLATFORM_LABEL).map(([id, l]) => `<option value="${id}">${l}</option>`).join("")}</select></label>
            </div>
            <label class="field"><span>Nombre del espectador</span><input class="input" id="ev-user" value="Ana"></label>
            <label class="field" data-for="chat"><span>Mensaje</span><input class="input" id="ev-text" value="¡Hola! Saludos desde México"></label>
            <div class="grid g2" data-for="gift">
              <label class="field"><span>Regalo</span><input class="input" id="ev-gift" value="Rose"></label>
              <label class="field"><span>Valor (💎)</span><input class="input" type="number" id="ev-value" value="5"></label>
            </div>
            <label class="field" data-for="amount"><span>Cantidad</span><input class="input" type="number" id="ev-amount" value="5" min="1"></label>
            <div class="row"><label class="switch"><input type="checkbox" id="ev-mod"><i></i><span>Moderador</span></label>
              <label class="switch"><input type="checkbox" id="ev-sub"><i></i><span>Suscriptor</span></label></div>
            <button class="btn primary block" id="ev-send">${icon("send")}Enviar evento</button>
          </div>
        </div>
        <div class="card">
          <h2>${icon("users")}Voces de los espectadores</h2>
          <p class="sub">Por defecto todos suenan con tu voz principal. Actívalo para que cada espectador simulado tenga su propia voz.</p>
          ${switchHtml("tts.random_voice_per_user", "Voz distinta para cada espectador")}
          <div class="small faint" style="margin-top:8px" id="now-voice"></div>
        </div>
        <div class="card">
          <h2>${icon("zap")}Ráfagas</h2>
          <p class="sub">Para ver cómo aguanta la cola y los overlays con mucho movimiento.</p>
          <div class="row">
            <button class="btn sm" data-burst="chat" data-count="10">💬 10 mensajes</button>
            <button class="btn sm" data-burst="follow" data-count="5">💜 5 follows</button>
            <button class="btn sm" data-burst="gift" data-count="5">🎁 Lluvia de regalos</button>
            <button class="btn sm" data-burst="like" data-count="6">❤️ Likes</button>
          </div>
        </div>
        <div class="card">
          <h2>${icon("terminal")}Probar comandos del chat</h2>
          <p class="sub">Se envían como si los escribiera el espectador del formulario.</p>
          <div class="chips">${CHAT_TESTS.map((cmd) => `<button class="btn sm" data-chat="${esc(cmd)}">${esc(cmd)}</button>`).join("")}</div>
        </div>
        <div class="card">
          <h2>${icon("sparkles")}Dinámicas rápidas</h2>
          <div class="row">
            <button class="btn sm" id="quick-giveaway">🎁 Sorteo de prueba</button>
            <button class="btn sm" id="quick-poll">📊 Encuesta de prueba</button>
            <button class="btn sm" id="quick-reset">${icon("refresh")}Reiniciar sesión</button>
          </div>
        </div>
      </div>
    </div>`;

  bindForm(root);
  renderVoices();
  renderNowVoice();
  setScreen(screen);
  syncFields();
  const stage = root.querySelector("#stage");
  observer = new ResizeObserver(() => {
    root.querySelector("#screen").style.transform = `scale(${stage.clientWidth / 1920})`;
  });
  observer.observe(stage);
  root.querySelector("#ev-kind").addEventListener("change", syncFields);
  root.addEventListener("click", onClick);
}

function renderVoices() {
  const grid = root?.querySelector("#voice-grid");
  if (!grid) return;
  grid.innerHTML = sampleVoices().map(({ engine, label, voices }) => `
    <div class="stack" style="padding:12px;border:1px solid var(--line);border-radius:12px;background:var(--bg-2);gap:8px">
      <b class="small">${label}</b>
      ${voices.length ? `<select class="input" data-engine-voice="${engine}">${voices.slice(0, 80).map((v) => `<option value="${esc(v.id)}">${esc(v.name)} · ${esc(v.country || v.locale)}</option>`).join("")}</select>
        <button class="btn sm" data-try="${engine}">${icon("play")}Escuchar</button>`
      : `<span class="small faint">${engine === "piper" || engine === "kokoro" ? "Descarga las voces en la página Voces." : engine === "elevenlabs" ? "Pon tu clave en Ajustes y carga tus voces." : "Sin voces disponibles."}</span>`}
      ${engine === "tiktok" ? '<span class="small faint">Requiere tu sessionid (Ajustes).</span>' : ""}
    </div>`).join("");
}

function renderNowVoice(item) {
  const el = root?.querySelector("#now-voice");
  if (!el) return;
  const current = item || store.state.tts.current;
  el.innerHTML = current?.voice_used
    ? `Sonando: <b>${esc(current.voice_used)}</b>${current.fallback ? ` <span style="color:var(--warn)">(respaldo: ${esc(current.voice)} falló)</span>` : ""}`
    : `Voz principal: <b>${esc(getConfig("tts.voice"))}</b>`;
}

function syncFields() {
  const kind = root.querySelector("#ev-kind").value;
  root.querySelector('[data-for="chat"]').style.display = kind === "chat" ? "" : "none";
  root.querySelector('[data-for="gift"]').style.display = kind === "gift" ? "" : "none";
  root.querySelector('[data-for="amount"]').style.display = ["gift", "sub", "bits", "raid", "like"].includes(kind) ? "" : "none";
}

function setScreen(id) {
  screen = id;
  root.querySelector("#screen").src = `/overlay/${id}`;
  root.querySelectorAll("[data-screen]").forEach((b) => b.classList.toggle("active", b.dataset.screen === id));
}

function formData(kind) {
  const q = (id) => root.querySelector(id);
  return {
    kind,
    platform: q("#ev-platform").value,
    user: q("#ev-user").value.trim() || "Ana",
    text: q("#ev-text").value,
    gift: q("#ev-gift").value,
    value: Number(q("#ev-value").value) * (kind === "gift" ? Number(q("#ev-amount").value || 1) : 1),
    amount: Number(q("#ev-amount").value || 1),
    is_moderator: q("#ev-mod").checked,
    is_subscriber: q("#ev-sub").checked,
  };
}

async function onClick(event) {
  const el = event.target.closest("button");
  if (!el) return;
  if (el.dataset.screen) setScreen(el.dataset.screen);
  else if (el.id === "ev-send") {
    const kind = root.querySelector("#ev-kind").value;
    const data = formData(kind);
    if (kind === "gift") data.amount = Number(root.querySelector("#ev-amount").value || 1);
    await action("simulate", data);
  } else if (el.dataset.burst) {
    await action("simulate_burst", { kind: el.dataset.burst, count: Number(el.dataset.count) });
  } else if (el.dataset.chat) {
    await action("simulate", { ...formData("chat"), text: el.dataset.chat });
    toast(`${root.querySelector("#ev-user").value} escribió ${el.dataset.chat}`, "info", 1800);
  } else if (el.dataset.try) {
    const select = root.querySelector(`[data-engine-voice="${el.dataset.try}"]`);
    await action("preview_voice", { voice: select.value, text: root.querySelector("#voice-text").value });
  } else if (el.id === "quick-giveaway") {
    await action("giveaway_start", { keyword: "!sorteo", prize: "Premio de prueba" });
    for (const name of ["Ana", "Luis", "Carla", "Pepe", "Sofi"]) await action("simulate", { kind: "chat", user: name, text: "!sorteo", platform: "tiktok" });
    toast("5 participantes apuntados. Pulsa “Elegir ganador” en Dinámicas o espera.", "success");
    setTimeout(() => action("giveaway_draw"), 2500);
    setScreen("giveaway");
  } else if (el.id === "quick-poll") {
    await action("poll_start", { question: "¿Qué jugamos después?", options: ["Minecraft", "Fortnite", "GTA"], duration: 30 });
    ["1", "2", "1", "3", "1"].forEach((vote, i) => setTimeout(() => action("simulate", { kind: "chat", user: `Votante ${i + 1}`, text: vote }), 600 * (i + 1)));
    setScreen("poll");
  } else if (el.id === "quick-reset") {
    await action("reset_session");
    toast("Sesión reiniciada", "success", 1500);
  }
}

export default {
  id: "playground",
  label: "Campo de pruebas",
  icon: "wand",
  render,
  onEvent(type) {
    if (!root?.isConnected) return;
    if (type === "voices.loaded" || type === "voices") setTimeout(renderVoices, 400);
    if (type === "tts.state") renderNowVoice();
  },
  unmount: () => observer?.disconnect(),
};
