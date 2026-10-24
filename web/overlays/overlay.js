// Conexión común de los overlays con LiveVoice Studio (reconexión automática).
export const params = new URLSearchParams(location.search);
export const isPreview = params.has("preview");

export const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);

const PF = {
  tiktok: '<path d="M16.6 5.82A4.28 4.28 0 0 1 15.54 3h-3.09v12.4a2.59 2.59 0 0 1-2.59 2.5c-1.42 0-2.6-1.16-2.6-2.6 0-1.72 1.66-3.01 3.37-2.48V9.66c-3.45-.46-6.47 2.22-6.47 5.64 0 3.33 2.76 5.7 5.69 5.7 3.14 0 5.69-2.55 5.69-5.7V9.01a7.35 7.35 0 0 0 4.3 1.38V7.3s-1.88.09-3.24-1.48z"/>',
  twitch: '<path d="M11.64 5.93h1.43v4.28h-1.43m3.93-4.28H17v4.28h-1.43M7 2 3.43 5.57v12.86h4.28V22l3.58-3.57h2.85L20.57 12V2m-1.43 9.29-2.85 2.85h-2.86l-2.5 2.5v-2.5H7.71V3.43h11.43Z"/>',
  kick: '<path d="M3 3h6v4h2V5h2V3h8v6h-2v2h-2v2h2v2h2v6h-8v-2h-2v-2H9v4H3z"/>',
  youtube: '<path d="M21.58 7.19a2.5 2.5 0 0 0-1.77-1.77C18.25 5 12 5 12 5s-6.25 0-7.81.42a2.5 2.5 0 0 0-1.77 1.77C2 8.75 2 12 2 12s0 3.25.42 4.81a2.5 2.5 0 0 0 1.77 1.77C5.75 19 12 19 12 19s6.25 0 7.81-.42a2.5 2.5 0 0 0 1.77-1.77C22 15.25 22 12 22 12s0-3.25-.42-4.81zM10 15V9l5.2 3z"/>',
};
export const pf = (platform) => (PF[platform] ? `<span class="pf ${platform}"><svg viewBox="0 0 24 24">${PF[platform]}</svg></span>` : "");

export function applyConfig(config) {
  if (!config) return;
  const root = document.documentElement.style;
  root.setProperty("--accent", params.get("accent") || config.accent || "#8b5cf6");
  root.setProperty("--font", `${params.get("size") || config.font_size || 22}px`);
}

export function connect(handlers) {
  let retry = 0;
  const open = () => {
    const ws = new WebSocket(`ws://${location.host}/ws`);
    ws.onopen = () => (retry = 0);
    ws.onmessage = (event) => {
      const { type, data } = JSON.parse(event.data);
      if (type === "hello") applyConfig(data.overlay);
      if (type === "overlay.config") applyConfig(data);
      handlers[type]?.(data);
    };
    ws.onclose = () => setTimeout(open, Math.min(5000, 500 * 2 ** retry++));
  };
  open();
}

// Cola para que las animaciones no se pisen entre sí.
export function sequencer(show) {
  const queue = [];
  let busy = false;
  const next = async () => {
    if (busy || !queue.length) return;
    busy = true;
    await show(queue.shift());
    busy = false;
    next();
  };
  return (item) => { queue.push(item); next(); };
}

export const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
