import { action, bindForm, esc, getConfig, icon, setConfig, store, switchHtml, toast, WHO_OPTIONS } from "../core.js";

let root, capturing = null;

const HOTKEYS = [
  ["toggle_mute", "Silenciar / activar voz"],
  ["skip", "Saltar mensaje actual"],
  ["pause", "Pausar / reanudar"],
  ["clear_queue", "Vaciar la cola"],
  ["clip", "Guardar clip"],
];

function keyName(event) {
  const parts = [];
  if (event.ctrlKey) parts.push("ctrl");
  if (event.altKey) parts.push("alt");
  if (event.shiftKey) parts.push("shift");
  if (event.metaKey) parts.push("windows");
  const key = event.key.toLowerCase();
  if (["control", "alt", "shift", "meta"].includes(key)) return null;
  const named = { " ": "space", arrowup: "up", arrowdown: "down", arrowleft: "left", arrowright: "right", escape: "esc" };
  parts.push(named[key] || (event.code.startsWith("Numpad") ? `num ${key}` : key));
  return parts.join("+");
}

function hotkeysHtml() {
  const state = store.state.hotkeys;
  return `
    ${state.available ? "" : '<div class="callout warn small">La librería de atajos no está disponible. Instala dependencias de nuevo.</div>'}
    <table class="table"><tbody>${HOTKEYS.map(([id, label]) => {
      const combo = getConfig(`hotkeys.${id}`, "");
      const error = state.errors?.[id];
      return `<tr><td>${label}${error ? `<br><span class="small" style="color:var(--bad)">${esc(error)}</span>` : ""}</td>
        <td style="text-align:right"><span class="kbd ${capturing === id ? "capturing" : ""}" data-capture="${id}">${capturing === id ? "Pulsa teclas…" : esc(combo || "—")}</span>
        <button class="btn sm ghost icon" data-clear-key="${id}" title="Quitar">${icon("x")}</button></td></tr>`;
    }).join("")}</tbody></table>`;
}

function render(target) {
  root = target;
  const obs = store.state.obs;
  root.innerHTML = `
    <div class="page-head"><div><h1>Clips y atajos</h1><p>Guarda los mejores momentos sin soltar el mando y controla la voz con el teclado.</p></div>
      <button class="btn primary" id="clip-now">${icon("scissors")}Guardar clip ahora</button></div>
    <div class="grid g2">
      <div class="card">
        <h2>${icon("scissors")}OBS: clips con Replay Buffer</h2>
        <p class="sub">Cada clip guarda los últimos segundos (lo que configures en OBS) y anota la hora en <code>clips/marcas.csv</code> para encontrarlo luego en el VOD.</p>
        <div class="stack">
          ${switchHtml("obs.enabled", "Conectar con OBS")}
          <div class="grid g3">
            <label class="field"><span>Servidor</span><input class="input" data-bind="obs.host"></label>
            <label class="field"><span>Puerto</span><input class="input" type="number" data-bind="obs.port"></label>
            <label class="field"><span>Contraseña</span><input class="input" type="password" data-bind="obs.password" placeholder="(si activaste autenticación)"></label>
          </div>
          <div class="row"><button class="btn" id="obs-test">${icon("zap")}Probar conexión</button><span class="small" id="obs-result">${obs.connected ? "✅ Conectado" : obs.error ? `⚠️ ${esc(obs.error)}` : ""}</span></div>
          <div class="divider"></div>
          <div class="grid g2">
            <label class="field"><span>Comando del chat</span><input class="input mono" data-bind="obs.clip_command"></label>
            <label class="field"><span>Quién puede pedir clips</span><select class="input" data-bind="obs.clip_permission">${WHO_OPTIONS.filter(([id]) => id !== "gifters").map(([id, l]) => `<option value="${id}">${l}</option>`).join("")}</select></label>
            <label class="field"><span>Espera entre clips del chat (s)</span><input class="input" type="number" min="0" data-bind="obs.clip_cooldown"></label>
            <label class="field"><span>Clip automático con regalos de al menos</span><input class="input" type="number" min="0" data-bind="obs.auto_clip_min_gift"><small>💎 / monedas. 0 = desactivado.</small></label>
          </div>
          <p class="small faint">Clips guardados esta sesión: <b>${obs.clips}</b></p>
        </div>
      </div>
      <div class="card">
        <h2>${icon("keyboard")}Atajos de teclado globales</h2>
        <p class="sub">Funcionan aunque estés dentro del juego. Haz clic en un atajo y pulsa la combinación nueva.</p>
        ${switchHtml("hotkeys.enabled", "Atajos activados")}
        <div id="hotkeys" style="margin-top:10px">${hotkeysHtml()}</div>
        <div class="callout small">Consejo: usa combinaciones con <b>Ctrl+Alt</b> para no chocar con el juego. Si tienes Stream Deck, asígnale estos atajos.</div>
      </div>
    </div>`;
  bindForm(root);
  root.querySelector("#clip-now").onclick = () => action("clip", { reason: "botón del panel" });
  root.querySelector("#obs-test").onclick = async () => {
    const el = root.querySelector("#obs-result");
    el.textContent = "Probando…";
    const result = await action("obs_test");
    el.innerHTML = result.ok
      ? `✅ OBS ${esc(result.obs_version)} · Replay Buffer ${result.replay_buffer ? "activo" : "<b>apagado</b> (actívalo en OBS → Ajustes → Salida)"}`
      : `⚠️ ${esc(result.error)}`;
  };
  root.addEventListener("click", (event) => {
    const el = event.target.closest("[data-capture],[data-clear-key]");
    if (!el) return;
    if (el.dataset.capture) { capturing = el.dataset.capture; refreshHotkeys(); }
    if (el.dataset.clearKey) saveHotkey(el.dataset.clearKey, "");
  });
  window.addEventListener("keydown", onKey, true);
}

function refreshHotkeys() {
  const box = root?.querySelector("#hotkeys");
  if (box) box.innerHTML = hotkeysHtml();
}

async function saveHotkey(id, combo) {
  capturing = null;
  setConfig(`hotkeys.${id}`, combo, { immediate: true });
  setTimeout(async () => {
    const result = await action("reload_hotkeys");
    if (result.hotkeys || result.registered) store.state.hotkeys = result;
    refreshHotkeys();
    if (combo) toast(`Atajo guardado: ${combo}`, "success", 1800);
  }, 400);
  refreshHotkeys();
}

function onKey(event) {
  if (!capturing || !root?.isConnected) return;
  event.preventDefault();
  event.stopPropagation();
  if (event.key === "Escape") { capturing = null; refreshHotkeys(); return; }
  const combo = keyName(event);
  if (combo) saveHotkey(capturing, combo);
}

export default {
  id: "clips",
  label: "Clips y atajos",
  icon: "scissors",
  render,
  unmount: () => { window.removeEventListener("keydown", onKey, true); capturing = null; },
};
