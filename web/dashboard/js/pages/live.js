import { action, esc, fmt, getConfig, icon, modal, pfBadge, setConfig, store, timeAgo, toast, PLATFORM_LABEL } from "../core.js";

const PLACEHOLDER = {
  tiktok: "usuario de TikTok (sin @)",
  twitch: "canal de Twitch",
  kick: "canal de Kick",
  youtube: "@canal o enlace del directo",
};
const STATUS_LABEL = {
  offline: "Desconectado", connecting: "Conectando", connected: "En vivo", waiting: "Esperando directo",
  reconnecting: "Reconectando", error: "Error",
};
const EVENT_TEXT = {
  follow: (e) => "empezó a seguirte",
  gift: (e) => `envió ${e.amount}× ${esc(e.gift)}${e.value ? ` <span class="faint">(${fmt(e.value)} 💎)</span>` : ""}`,
  sub: (e) => (e.amount > 1 ? `se suscribió (${e.amount} meses)` : "se suscribió"),
  bits: (e) => `envió ${fmt(e.amount)} bits`,
  raid: (e) => `hizo raid con ${fmt(e.amount)} espectadores`,
  share: () => "compartió el directo",
  join: () => "entró al directo",
};

let root, filter = "all", autoscroll = true, uptimeTimer;

function platformCard(name) {
  const info = store.state.platforms[name];
  const settings = getConfig(`platforms.${name}`);
  const active = !["offline", "error"].includes(info.status);
  return `
    <div class="card platform-card ${name}" data-platform="${name}">
      <div class="pc-head">${pfBadge(name)}<b>${PLATFORM_LABEL[name]}</b>
        <span class="pill ${info.status}">${STATUS_LABEL[info.status] || info.status}</span>
        ${info.viewers ? `<span class="viewers">${icon("eye")}${fmt(info.viewers)}</span>` : ""}
      </div>
      <div class="row nowrap">
        <input class="input" data-channel value="${esc(settings.channel)}" placeholder="${PLACEHOLDER[name]}" ${active ? "disabled" : ""}>
        ${active
          ? `<button class="btn danger" data-disconnect>${icon("x")}Salir</button>`
          : `<button class="btn primary" data-connect>${icon("zap")}Conectar</button>`}
      </div>
      <div class="pc-msg" title="${esc(info.message)}">${esc(info.message) || "&nbsp;"}</div>
    </div>`;
}

function renderPlatforms() {
  const box = root.querySelector("#platforms");
  if (!box) return;
  const focused = document.activeElement?.closest?.("[data-platform]")?.dataset.platform;
  box.innerHTML = ["tiktok", "twitch", "kick", "youtube"].map(platformCard).join("");
  if (focused) box.querySelector(`[data-platform="${focused}"] [data-channel]`)?.focus();
}

function renderStats() {
  const s = store.state.stats;
  const viewers = Object.values(store.state.platforms).reduce((total, p) => total + (p.viewers || 0), 0);
  const tiles = [
    ["eye", fmt(viewers), "Espectadores"],
    ["message", fmt(s.messages), "Mensajes"],
    ["users", fmt(s.chatters), "Personas en el chat"],
    ["heart", fmt(s.likes), "Likes"],
    ["userplus", fmt(s.followers), "Nuevos seguidores"],
    ["gift", fmt(s.gift_value), "Valor en regalos"],
  ];
  const box = root.querySelector("#stats");
  if (box) box.innerHTML = tiles.map(([ic, value, label]) => `<div class="stat"><div class="ic">${icon(ic)}</div><div><b>${value}</b><span>${label}</span></div></div>`).join("");
}

function avatar(user) {
  if (user.avatar) return `<img class="avatar" src="${esc(user.avatar)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.replaceWith(Object.assign(document.createElement('div'),{className:'avatar',textContent:'${esc((user.name || "?")[0]).toUpperCase()}'}))">`;
  return `<div class="avatar">${esc((user.name || "?")[0]).toUpperCase()}</div>`;
}

function messageHtml(event) {
  const user = event.user;
  const time = new Date(event.timestamp * 1000).toLocaleTimeString("es", { hour: "2-digit", minute: "2-digit" });
  const tags = [
    user.is_broadcaster ? '<span class="tag">Streamer</span>' : "",
    user.is_moderator && !user.is_broadcaster ? '<span class="tag mod">Mod</span>' : "",
    user.is_subscriber ? '<span class="tag sub">Sub</span>' : "",
    user.is_vip ? '<span class="tag vip">VIP</span>' : "",
  ].join("");
  const isChat = event.kind === "chat";
  const body = isChat ? esc(event.text) : (EVENT_TEXT[event.kind]?.(event) || esc(event.kind));
  const color = user.color ? `style="color:${esc(user.color)}"` : "";
  return `
    <div class="msg ${isChat ? "" : `event ${event.kind}`}" data-id="${event.id}" data-user="${esc(user.key)}" data-name="${esc(user.name)}">
      ${avatar(user)}
      <div class="body">
        <div class="who">${pfBadge(event.platform, true)}<span ${color}>${esc(user.name)}</span>${tags}<time>${time}</time></div>
        <div class="text ${isChat && !event.tts_allowed ? "muted-tts" : ""}">${body}${isChat && !event.tts_allowed ? ' <span class="faint" title="No se leyó (spam o filtro)">🔇</span>' : ""}</div>
      </div>
      ${isChat ? `<div class="actions">
        <button class="btn sm icon" data-read title="Leer en voz alta">${icon("volume")}</button>
        <button class="btn sm icon" data-voice title="Asignar voz a este espectador">${icon("voice")}</button>
        <button class="btn sm icon" data-ignore title="No leer más a este usuario">${icon("mute")}</button>
      </div>` : ""}
    </div>`;
}

function visible(event) {
  if (filter === "all") return true;
  if (filter === "chat") return event.kind === "chat";
  if (filter === "events") return event.kind !== "chat";
  return event.platform === filter;
}

function renderFeed() {
  const feed = root.querySelector("#feed");
  if (!feed) return;
  const events = store.state.recent.filter(visible).slice(-150);
  feed.innerHTML = events.length
    ? events.map(messageHtml).join("")
    : `<div class="empty">${icon("message")}Conecta una plataforma o usa los <b>eventos de prueba</b> para ver cómo funciona.</div>`;
  feed.scrollTop = feed.scrollHeight;
}

function appendFeed(event) {
  const feed = root.querySelector("#feed");
  if (!feed || !visible(event)) return;
  feed.querySelector(".empty")?.remove();
  feed.insertAdjacentHTML("beforeend", messageHtml(event));
  while (feed.children.length > 200) feed.firstElementChild.remove();
  if (autoscroll) feed.scrollTop = feed.scrollHeight;
}

function renderTTS() {
  const box = root.querySelector("#tts-box");
  if (!box) return;
  const tts = store.state.tts;
  const current = tts.current;
  const engines = Object.entries(tts.engines || {});
  const failing = engines.filter(([, status]) => !status.ok);
  box.innerHTML = `
    <div class="now ${current ? "" : "idle"}">
      <div class="label">${current ? '<span class="wave"><i></i><i></i><i></i><i></i></span> Hablando ahora' : tts.muted ? "🔇 Voz silenciada" : tts.paused ? "⏸ Pausado" : "En silencio"}</div>
      <div class="text">${current ? esc(current.text) : '<span class="faint">Los mensajes del chat sonarán aquí.</span>'}</div>
    </div>
    ${failing.length ? `<div class="callout warn small">⚠️ Motor caído: ${failing.map(([name]) => name).join(", ")}. Se está usando el respaldo automático.</div>` : ""}
    <div class="row" style="margin:12px 0 8px"><b class="small">Cola</b><span class="faint small">${tts.queue_size} pendientes</span><span class="spacer"></span>
      ${tts.queue_size ? `<button class="btn sm ghost" data-clear>${icon("trash")}Vaciar</button>` : ""}</div>
    <div class="queue">${tts.queue.length ? tts.queue.map((item) => `
      <div class="qitem ${item.priority > 10 ? "high" : ""}">${item.platform ? pfBadge(item.platform, true) : "🔔"}
        <span class="t" title="${esc(item.text)}">${esc(item.text)}</span>
        <button class="btn sm icon ghost" data-remove="${item.id}">${icon("x")}</button></div>`).join("") : '<div class="faint small">Vacía</div>'}
    </div>`;
}

function render(target) {
  root = target;
  const s = store.state;
  root.innerHTML = `
    <div class="page-head">
      <div><h1>Directo</h1><p>Conecta tus plataformas y controla todo lo que pasa en el chat.</p></div>
      <div class="row"><span class="pill" id="uptime">${icon("clock")} ${timeAgo(s.stats.uptime)}</span>
        <button class="btn sm" data-reset title="Reinicia contadores y metas de esta sesión">${icon("refresh")}Nueva sesión</button></div>
    </div>
    <div class="grid g4" id="platforms"></div>
    <div class="stats-row" id="stats"></div>
    <div class="live-layout">
      <div class="card flush">
        <div class="card-head"><h2>${icon("message")}Chat y eventos</h2>
          <div class="seg" id="filters">
            ${[["all", "Todo"], ["chat", "Chat"], ["events", "Eventos"], ["tiktok", "TikTok"], ["twitch", "Twitch"], ["kick", "Kick"], ["youtube", "YouTube"]]
              .map(([id, label]) => `<button data-filter="${id}" class="${filter === id ? "active" : ""}">${label}</button>`).join("")}
          </div>
        </div>
        <div class="feed" id="feed"></div>
      </div>
      <div class="stack">
        <div class="card"><h2>${icon("voice")}Voz en vivo</h2><div id="tts-box" style="margin-top:10px"></div></div>
        <div class="card">
          <h2>${icon("send")}Decir algo</h2>
          <p class="sub">Lo dice la voz principal al momento (no pasa por la cola).</p>
          <div class="row nowrap"><input class="input" id="say" placeholder="Ej: ¡Gracias a todos por venir!"><button class="btn primary icon" id="say-btn">${icon("send")}</button></div>
        </div>
        <div class="card">
          <h2>${icon("wand")}Eventos de prueba</h2>
          <p class="sub">Prueba alertas, voces y overlays sin estar en directo.</p>
          <div class="row">
            ${[["chat", "💬 Mensaje"], ["follow", "➕ Follow"], ["gift", "🎁 Regalo"], ["sub", "⭐ Sub"], ["bits", "💎 Bits"], ["raid", "🚀 Raid"], ["share", "🔁 Compartir"], ["like", "❤️ 600 likes"]]
              .map(([kind, label]) => `<button class="btn sm" data-sim="${kind}">${label}</button>`).join("")}
          </div>
        </div>
      </div>
    </div>`;

  renderPlatforms();
  renderStats();
  renderFeed();
  renderTTS();

  root.addEventListener("click", onClick);
  root.querySelector("#feed").addEventListener("scroll", (event) => {
    const el = event.target;
    autoscroll = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
  });
  root.querySelector("#platforms").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && event.target.matches("[data-channel]")) event.target.closest("[data-platform]").querySelector("[data-connect]")?.click();
  });
  const say = root.querySelector("#say");
  const send = () => { if (say.value.trim()) { action("say", { text: say.value }); say.value = ""; } };
  root.querySelector("#say-btn").onclick = send;
  say.addEventListener("keydown", (event) => event.key === "Enter" && send());

  uptimeTimer = setInterval(() => {
    store.state.stats.uptime += 1;
    const el = root.querySelector("#uptime");
    if (el) el.innerHTML = `${icon("clock")} ${timeAgo(store.state.stats.uptime)}`;
  }, 1000);
}

async function onClick(event) {
  const target = event.target.closest("button");
  if (!target) return;
  const card = target.closest("[data-platform]");
  if (target.matches("[data-connect]")) {
    const channel = card.querySelector("[data-channel]").value.trim();
    if (!channel) return toast("Escribe el nombre del canal", "warning");
    setConfig(`platforms.${card.dataset.platform}.enabled`, true);
    await action("connect", { platform: card.dataset.platform, channel });
  } else if (target.matches("[data-disconnect]")) {
    await action("disconnect", { platform: card.dataset.platform });
  } else if (target.dataset.filter) {
    filter = target.dataset.filter;
    root.querySelectorAll("[data-filter]").forEach((b) => b.classList.toggle("active", b === target));
    renderFeed();
  } else if (target.dataset.sim) {
    action("simulate", { kind: target.dataset.sim });
  } else if (target.dataset.remove) {
    action("remove_queue_item", { id: target.dataset.remove });
  } else if (target.matches("[data-clear]")) {
    action("clear_queue");
  } else if (target.matches("[data-reset]")) {
    if (confirm("¿Empezar una nueva sesión? Se reinician los contadores y las metas.")) action("reset_session");
  } else {
    const msg = target.closest(".msg");
    if (!msg) return;
    const name = msg.dataset.name, key = msg.dataset.user;
    if (target.matches("[data-read]")) {
      action("say", { text: `${name} dice: ${msg.querySelector(".text").textContent.replace("🔇", "")}` });
    } else if (target.matches("[data-ignore]")) {
      const ignored = new Set(getConfig("tts.ignored_users", []));
      ignored.add(key);
      setConfig("tts.ignored_users", [...ignored], { immediate: true });
      toast(`No se leerá más a ${name}. Puedes quitarlo en Lectura.`, "info");
    } else if (target.matches("[data-voice]")) {
      assignVoice(key, name);
    }
  }
}

export function assignVoice(key, name) {
  const current = getConfig("tts.user_voices", {})[key] || {};
  const voices = store.voices.filter((v) => v.engine === "edge");
  const presets = store.state.presets;
  modal({
    title: `Voz para ${name}`,
    body: `
      <p class="muted small" style="margin:0">Este espectador siempre sonará con esta voz. También pueden elegirla ellos escribiendo <code>!voz mexicano</code>, <code>!voz ardilla</code>, etc.</p>
      <label class="field"><span>Voz</span><select class="input" id="uv-voice"><option value="">Voz principal</option>
        ${voices.map((v) => `<option value="${esc(v.id)}" ${v.id === current.voice ? "selected" : ""}>${esc(v.name)} · ${esc(v.country || v.locale)} · ${v.gender === "Female" ? "Mujer" : "Hombre"}</option>`).join("")}
      </select></label>
      <label class="field"><span>Personaje</span><select class="input" id="uv-preset">
        ${presets.map((p) => `<option value="${p.id}" ${p.id === (current.preset || "normal") ? "selected" : ""}>${p.emoji} ${p.name}</option>`).join("")}
      </select></label>
      <button class="btn" id="uv-test">${icon("play")}Escuchar</button>`,
    onSave: (box) => {
      const voices = { ...getConfig("tts.user_voices", {}) };
      const voice = box.querySelector("#uv-voice").value, preset = box.querySelector("#uv-preset").value;
      if (!voice && preset === "normal") delete voices[key];
      else voices[key] = { voice, preset, name };
      setConfig("tts.user_voices", voices, { immediate: true });
      toast(`Voz asignada a ${name}`, "success");
    },
  }).querySelector("#uv-test").onclick = (event) => {
    const box = event.target.closest(".modal");
    action("preview_voice", { voice: box.querySelector("#uv-voice").value || getConfig("tts.voice"), preset: box.querySelector("#uv-preset").value, text: `Hola, soy ${name} y así sueno.` });
  };
}

function onEvent(type, data) {
  if (!root?.isConnected) return;
  if (type === "event") appendFeed(data);
  else if (type === "tts.state") renderTTS();
  else if (type === "platform.status") { renderPlatforms(); renderStats(); }
  else if (type === "stats") renderStats();
}

export default {
  id: "live",
  label: "Directo",
  icon: "live",
  render,
  onEvent,
  unmount: () => clearInterval(uptimeTimer),
};
