// Núcleo del panel: estado, API, websocket, iconos y helpers de formularios.

export const store = {
  state: null,
  voices: [],
  feed: [],
  listeners: new Set(),
};

// ── API ────────────────────────────────────────────────────────────
export async function api(path, body, method) {
  const options = { method: method || (body === undefined ? "GET" : "POST"), headers: {} };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const response = await fetch(`/api/${path}`, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok && data.error) throw new Error(data.error);
  return data;
}

export async function action(name, data = {}) {
  const result = await api(`action/${name}`, data);
  if (result && result.ok === false && result.error && result.error !== "cooldown") toast(result.error, "error");
  return result;
}

export async function loadState() {
  store.state = await api("state");
  return store.state;
}

export async function loadVoices() {
  store.voices = await api("voices");
  return store.voices;
}

// ── Configuración ──────────────────────────────────────────────────
export function getConfig(path, fallback) {
  let node = store.state?.config;
  for (const part of path.split(".")) {
    if (node == null || typeof node !== "object" || !(part in node)) return fallback;
    node = node[part];
  }
  return node;
}

function setLocal(path, value) {
  const parts = path.split(".");
  let node = store.state.config;
  for (const part of parts.slice(0, -1)) node = node[part] ??= {};
  node[parts.at(-1)] = value;
}

function buildPatch(path, value) {
  return path.split(".").reverse().reduce((acc, part) => ({ [part]: acc }), value);
}

// Si la ruta pasa por una lista (ej. "timers.0.enabled") se envía la lista completa,
// porque el servidor reemplaza las listas en vez de mezclarlas.
function arrayRoot(path) {
  const parts = path.split(".");
  let node = store.state.config;
  for (let i = 0; i < parts.length - 1; i++) {
    node = node?.[parts[i]];
    if (Array.isArray(node)) return parts.slice(0, i + 1).join(".");
  }
  return null;
}

const pending = new Map();
export function setConfig(path, value, { immediate = false } = {}) {
  setLocal(path, value);
  const listPath = arrayRoot(path);
  if (listPath) {
    path = listPath;
    value = getConfig(listPath);
  }
  clearTimeout(pending.get(path));
  const send = async () => {
    pending.delete(path);
    try {
      await api("config", buildPatch(path, value));
      flashSaved();
    } catch (error) {
      toast(`No se pudo guardar: ${error.message}`, "error");
    }
  };
  if (immediate) send();
  else pending.set(path, setTimeout(send, 350));
}

let savedTimer;
function flashSaved() {
  let el = document.getElementById("saved-flag");
  if (!el) {
    el = document.createElement("div");
    el.id = "saved-flag";
    el.style.cssText = "position:fixed;top:14px;right:18px;padding:6px 12px;border-radius:99px;background:rgba(34,197,94,.15);color:#86efac;border:1px solid rgba(34,197,94,.35);font-size:12px;font-weight:600;z-index:60;transition:opacity .3s";
    el.textContent = "✓ Guardado";
    document.body.append(el);
  }
  el.style.opacity = "1";
  clearTimeout(savedTimer);
  savedTimer = setTimeout(() => (el.style.opacity = "0"), 1200);
}

// Enlaza automáticamente los controles con data-bind="ruta.de.config".
export function bindForm(root) {
  root.querySelectorAll("[data-bind]").forEach((el) => {
    const path = el.dataset.bind;
    const type = el.dataset.type || (el.type === "checkbox" ? "bool" : el.type === "range" || el.type === "number" ? "number" : "text");
    const current = getConfig(path);
    if (type === "bool") el.checked = !!current;
    else if (type === "list") el.value = (current || []).join(type === "list" ? ", " : "\n");
    else if (current !== undefined && current !== null) el.value = current;

    const output = root.querySelector(`[data-out="${path}"]`);
    const format = (value) => (el.dataset.suffix ? `${value}${el.dataset.suffix}` : value);
    if (output) output.textContent = format(el.value);

    const handler = () => {
      let value = el.value;
      if (type === "bool") value = el.checked;
      else if (type === "number") value = Number(value);
      else if (type === "list") value = value.split(/[,\n]/).map((item) => item.trim()).filter(Boolean);
      if (output) output.textContent = format(el.value);
      setConfig(path, value);
      el.dispatchEvent(new CustomEvent("bound-change", { bubbles: true, detail: { path, value } }));
    };
    el.addEventListener(el.tagName === "SELECT" || type === "bool" ? "change" : "input", handler);
  });
}

// ── WebSocket ──────────────────────────────────────────────────────
export function connectSocket(onMessage) {
  let retry = 0;
  const open = () => {
    const ws = new WebSocket(`ws://${location.host}/ws`);
    ws.onopen = () => { retry = 0; document.body.classList.remove("offline"); };
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      onMessage(message.type, message.data);
    };
    ws.onclose = () => {
      document.body.classList.add("offline");
      setTimeout(open, Math.min(5000, 500 * 2 ** retry++));
    };
  };
  open();
}

// ── Helpers de UI ──────────────────────────────────────────────────
export const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);

export function toast(text, level = "info", timeout = 4200) {
  const box = document.getElementById("toasts");
  const el = document.createElement("div");
  el.className = `toast ${level}`;
  el.textContent = text;
  box.append(el);
  while (box.children.length > 5) box.firstChild.remove();
  setTimeout(() => el.remove(), timeout);
}

export function modal({ title, body, onSave, saveLabel = "Guardar", wide = false }) {
  const back = document.createElement("div");
  back.className = "modal-back";
  back.innerHTML = `
    <div class="modal" style="${wide ? "width:min(860px,100%)" : ""}">
      <div class="modal-head"><h3>${esc(title)}</h3><button class="btn ghost icon" data-close>${icon("x")}</button></div>
      <div class="modal-body">${body}</div>
      ${onSave ? `<div class="modal-foot"><button class="btn" data-close>Cancelar</button><button class="btn primary" data-save>${esc(saveLabel)}</button></div>` : ""}
    </div>`;
  const close = () => back.remove();
  back.addEventListener("click", (event) => {
    if (event.target === back || event.target.closest("[data-close]")) close();
  });
  back.querySelector("[data-save]")?.addEventListener("click", async () => {
    try {
      if ((await onSave(back)) !== false) close();
    } catch (error) {
      toast(error.message, "error");
    }
  });
  document.body.append(back);
  return back;
}

export const switchHtml = (bind, label, hint = "") =>
  `<label class="switch"><input type="checkbox" data-bind="${bind}"><i></i><span>${label}${hint ? `<small>${hint}</small>` : ""}</span></label>`;

export const rangeHtml = (bind, label, min, max, step = 1, suffix = "") =>
  `<div class="range"><div class="range-head"><span>${label}</span><b data-out="${bind}"></b></div>
   <input type="range" data-bind="${bind}" min="${min}" max="${max}" step="${step}" data-suffix="${suffix}"></div>`;

export const fieldHtml = (label, control, hint = "") =>
  `<label class="field"><span>${label}</span>${control}${hint ? `<small>${hint}</small>` : ""}</label>`;

export const selectHtml = (bind, options) =>
  `<select class="input" data-bind="${bind}">${options.map(([value, label]) => `<option value="${esc(value)}">${esc(label)}</option>`).join("")}</select>`;

export function timeAgo(seconds) {
  const h = Math.floor(seconds / 3600), m = Math.floor((seconds % 3600) / 60), s = seconds % 60;
  return h ? `${h}h ${String(m).padStart(2, "0")}m` : `${m}:${String(s).padStart(2, "0")}`;
}

export const fmt = (n) => new Intl.NumberFormat("es").format(n || 0);

export async function copy(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const area = document.createElement("textarea");
    area.value = text;
    document.body.append(area);
    area.select();
    document.execCommand("copy");
    area.remove();
  }
  toast("Copiado al portapapeles", "success", 1800);
}

export async function uploadSound(file, folder = "commands") {
  const form = new FormData();
  form.append("folder", folder);
  form.append("file", file);
  const response = await fetch("/api/upload-sound", { method: "POST", body: form });
  const data = await response.json();
  if (!data.ok) throw new Error(data.error || "Error al subir");
  return data;
}

export const WHO_OPTIONS = [
  ["everyone", "Todos"],
  ["followers", "Seguidores"],
  ["subscribers", "Suscriptores / miembros"],
  ["moderators", "Solo moderadores"],
  ["gifters", "Quienes enviaron regalo"],
];

export const PLATFORM_LABEL = { tiktok: "TikTok", twitch: "Twitch", kick: "Kick", youtube: "YouTube" };

// ── Iconos (trazos estilo Lucide) ──────────────────────────────────
const ICONS = {
  logo: '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/>',
  live: '<circle cx="12" cy="12" r="2"/><path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49m11.31-2.82a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14"/>',
  voice: '<path d="M2 10v3"/><path d="M6 6v11"/><path d="M10 3v18"/><path d="M14 8v7"/><path d="M18 5v13"/><path d="M22 10v3"/>',
  book: '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
  bell: '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
  terminal: '<polyline points="4 17 10 11 4 5"/><line x1="12" x2="20" y1="19" y2="19"/>',
  sparkles: '<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/>',
  layers: '<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>',
  scissors: '<circle cx="6" cy="6" r="3"/><path d="M8.12 8.12 12 12"/><path d="M20 4 8.12 15.88"/><circle cx="6" cy="18" r="3"/><path d="M14.8 14.8 20 20"/>',
  keyboard: '<rect width="20" height="16" x="2" y="4" rx="2"/><path d="M6 8h.01M10 8h.01M14 8h.01M18 8h.01M8 12h.01M12 12h.01M16 12h.01M7 16h10"/>',
  help: '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>',
  settings: '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
  mute: '<path d="M11 4.7a.7.7 0 0 0-1.2-.5L6.4 7.6A1.4 1.4 0 0 1 5.4 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.4a1.4 1.4 0 0 1 1 .4l3.4 3.4a.7.7 0 0 0 1.2-.5z"/><line x1="22" x2="16" y1="9" y2="15"/><line x1="16" x2="22" y1="9" y2="15"/>',
  volume: '<path d="M11 4.7a.7.7 0 0 0-1.2-.5L6.4 7.6A1.4 1.4 0 0 1 5.4 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.4a1.4 1.4 0 0 1 1 .4l3.4 3.4a.7.7 0 0 0 1.2-.5z"/><path d="M16 9a5 5 0 0 1 0 6"/><path d="M19.4 18.4a9 9 0 0 0 0-12.7"/>',
  pause: '<rect x="14" y="4" width="4" height="16" rx="1"/><rect x="6" y="4" width="4" height="16" rx="1"/>',
  play: '<polygon points="6 3 20 12 6 21 6 3"/>',
  skip: '<polygon points="5 4 15 12 5 20 5 4"/><line x1="19" x2="19" y1="5" y2="19"/>',
  trash: '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>',
  x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  plus: '<path d="M5 12h14"/><path d="M12 5v14"/>',
  copy: '<rect width="14" height="14" x="8" y="8" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>',
  external: '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  eye: '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
  message: '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>',
  heart: '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>',
  gift: '<rect x="3" y="8" width="18" height="4" rx="1"/><path d="M12 8v13"/><path d="M19 12v7a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-7"/><path d="M7.5 8a2.5 2.5 0 0 1 0-5A4.8 8 0 0 1 12 8a4.8 8 0 0 1 4.5-5 2.5 2.5 0 0 1 0 5"/>',
  userplus: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" x2="19" y1="8" y2="14"/><line x1="22" x2="16" y1="11" y2="11"/>',
  clock: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
  zap: '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
  trophy: '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',
  chart: '<path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>',
  target: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
  dice: '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M16 8h.01M8 8h.01M8 16h.01M16 16h.01M12 12h.01"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  alert: '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
  shield: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>',
  refresh: '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
  wand: '<path d="m21.64 3.64-1.28-1.28a1.21 1.21 0 0 0-1.72 0L2.36 18.64a1.21 1.21 0 0 0 0 1.72l1.28 1.28a1.2 1.2 0 0 0 1.72 0L21.64 5.36a1.2 1.2 0 0 0 0-1.72"/><path d="m14 7 3 3"/><path d="M5 6v4M19 14v4M10 2v2M7 8H3M21 16h-4M11 3H9"/>',
  send: '<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>',
  tiktok: '<path fill="currentColor" stroke="none" d="M16.6 5.82s.51.5 0 0A4.28 4.28 0 0 1 15.54 3h-3.09v12.4a2.59 2.59 0 0 1-2.59 2.5c-1.42 0-2.6-1.16-2.6-2.6 0-1.72 1.66-3.01 3.37-2.48V9.66c-3.45-.46-6.47 2.22-6.47 5.64 0 3.33 2.76 5.7 5.69 5.7 3.14 0 5.69-2.55 5.69-5.7V9.01a7.35 7.35 0 0 0 4.3 1.38V7.3s-1.88.09-3.24-1.48z"/>',
  twitch: '<path fill="currentColor" stroke="none" d="M11.64 5.93h1.43v4.28h-1.43m3.93-4.28H17v4.28h-1.43M7 2 3.43 5.57v12.86h4.28V22l3.58-3.57h2.85L20.57 12V2m-1.43 9.29-2.85 2.85h-2.86l-2.5 2.5v-2.5H7.71V3.43h11.43Z"/>',
  kick: '<path fill="currentColor" stroke="none" d="M3 3h6v4h2V5h2V3h8v6h-2v2h-2v2h2v2h2v6h-8v-2h-2v-2H9v4H3z"/>',
  youtube: '<path fill="currentColor" stroke="none" d="M21.58 7.19a2.5 2.5 0 0 0-1.77-1.77C18.25 5 12 5 12 5s-6.25 0-7.81.42a2.5 2.5 0 0 0-1.77 1.77C2 8.75 2 12 2 12s0 3.25.42 4.81a2.5 2.5 0 0 0 1.77 1.77C5.75 19 12 19 12 19s6.25 0 7.81-.42a2.5 2.5 0 0 0 1.77-1.77C22 15.25 22 12 22 12s0-3.25-.42-4.81zM10 15V9l5.2 3z"/>',
};

export function icon(name) {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONS[name] || ""}</svg>`;
}

export const pfBadge = (platform, small = false) => `<span class="pf ${platform} ${small ? "sm" : ""}" title="${PLATFORM_LABEL[platform] || platform}">${icon(platform)}</span>`;
