import { action, api, bindForm, esc, icon, rangeHtml, store, switchHtml, toast, PLATFORM_LABEL } from "../core.js";

let root;

const ENGINE_LABEL = { edge: "Microsoft Edge (neuronal, online)", google: "Google (respaldo online)", sapi: "Windows (sin internet)" };

function diagnosticsHtml() {
  const engines = store.state.tts.engines || {};
  const platforms = store.state.platforms;
  return `
    <table class="table"><tbody>
      ${Object.entries(engines).map(([name, s]) => `<tr><td>${ENGINE_LABEL[name] || name}</td>
        <td style="text-align:right">${s.ok ? '<span class="pill connected">OK</span>' : `<span class="pill error" title="${esc(s.error)}">Falló</span>`}</td></tr>`).join("")}
      ${Object.values(platforms).map((p) => `<tr><td>${PLATFORM_LABEL[p.platform]} ${p.channel ? `<span class="faint small">${esc(p.channel)}</span>` : ""}</td>
        <td style="text-align:right"><span class="pill ${p.status}">${esc(p.status)}</span></td></tr>`).join("")}
      <tr><td>Audio</td><td style="text-align:right">${store.state.audio.available ? `<span class="pill connected">${esc(store.state.audio.device || "Predeterminado")}</span>` : '<span class="pill error">Sin dispositivo</span>'}</td></tr>
    </tbody></table>`;
}

function render(target) {
  root = target;
  root.innerHTML = `
    <div class="page-head"><div><h1>Ajustes</h1><p>Audio, conexión automática y diagnóstico.</p></div></div>
    <div class="grid g2">
      <div class="stack">
        <div class="card">
          <h2>${icon("volume")}Salida de audio</h2>
          <p class="sub">Elige un dispositivo virtual (ej. <b>CABLE Input</b> de VB-Audio) para tener la voz en una pista separada en OBS.</p>
          <div class="row nowrap"><select class="input" id="device"><option value="">Predeterminado de Windows</option></select>
            <button class="btn" id="device-test">${icon("play")}Probar</button></div>
          <div class="stack" style="margin-top:14px">
            ${rangeHtml("audio.tts_volume", "Volumen de la voz", 0, 100, 1, "%")}
            ${rangeHtml("audio.sfx_volume", "Volumen de sonidos y alertas", 0, 100, 1, "%")}
          </div>
        </div>
        <div class="card">
          <h2>${icon("zap")}Conexión automática</h2>
          <p class="sub">Al abrir LiveVoice Studio se conecta solo y espera a que empieces el directo.</p>
          <div class="stack">${["tiktok", "twitch", "kick", "youtube"].map((p) => switchHtml(`platforms.${p}.auto_connect`, `Conectar ${PLATFORM_LABEL[p]} al iniciar`)).join("")}</div>
        </div>
        <div class="card">
          <h2>${icon("shield")}TikTok avanzado</h2>
          <p class="sub">TikTok limita las conexiones gratuitas del servidor de firmas. Si ves errores de “rate limit”, crea una clave gratis en <b>eulerstream.com</b> y pégala aquí.</p>
          <label class="field"><span>Clave API de firmas (opcional)</span><input class="input" type="password" data-bind="platforms.tiktok.sign_api_key" placeholder="euler_..."></label>
        </div>
        <div class="card">
          <h2>${icon("sparkles")}ElevenLabs (voces de IA)</h2>
          <p class="sub">Crea una cuenta gratis en elevenlabs.io → perfil → <b>API Keys</b> → crea una clave con permiso de <i>Text to Speech</i> y <i>Voices (lectura)</i>. Se guarda solo en tu PC.</p>
          <label class="field"><span>Clave API</span><input class="input" type="password" data-bind="tts.elevenlabs_key" placeholder="sk_..."></label>
          <label class="field" style="margin-top:10px"><span>Modelo</span><select class="input" data-bind="tts.elevenlabs_model">
            <option value="eleven_flash_v2_5">Flash v2.5 — rápido y gasta la mitad de caracteres (recomendado)</option>
            <option value="eleven_multilingual_v2">Multilingual v2 — máxima calidad</option>
          </select></label>
          <button class="btn sm" style="margin-top:10px" id="eleven-load">${icon("refresh")}Cargar mis voces</button>
        </div>
        <div class="card">
          <h2>${icon("voice")}Voces de TikTok (experimental)</h2>
          <p class="sub">Para usar Ghostface, Stormtrooper, el señor mexicano, etc. TikTok solo las genera para cuentas con sesión iniciada.
            Copia la cookie <code>sessionid</code> de tiktok.com (F12 → Aplicación → Cookies). Se guarda solo en tu PC, en config.json.</p>
          <div class="callout warn small">Úsalo con una cuenta secundaria: el sessionid da acceso a la cuenta. Si TikTok lo invalida, las voces caen al respaldo automático.</div>
          <label class="field"><span>sessionid</span><input class="input" type="password" data-bind="tts.tiktok_session_id" placeholder="pega aquí tu sessionid"></label>
        </div>
      </div>
      <div class="stack">
        <div class="card"><div class="row"><h2 style="margin:0">${icon("check")}Diagnóstico</h2><span class="spacer"></span><button class="btn sm" id="diag-refresh">${icon("refresh")}</button></div>
          <div id="diag" style="margin-top:10px">${diagnosticsHtml()}</div></div>
        <div class="card">
          <h2>${icon("settings")}Sistema</h2>
          <div class="stack" style="margin-top:10px">
            <label class="field"><span>Puerto del servidor local</span><input class="input" type="number" data-bind="general.port"><small>Si lo cambias, reinicia la app y actualiza las URLs de los overlays en OBS.</small></label>
            <div class="row"><button class="btn" id="refresh-voices">${icon("refresh")}Actualizar voces</button>
              <button class="btn" id="open-browser">${icon("external")}Abrir panel en el navegador</button></div>
            <p class="small faint">Tus datos (config.json, puntos, sonidos, clips y logs) se guardan junto al programa. Versión ${esc(store.state.version)}.</p>
          </div>
        </div>
      </div>
    </div>`;
  bindForm(root);
  loadDevices();
  root.querySelector("#device").onchange = async (event) => {
    const result = await action("set_audio_device", { device: event.target.value });
    toast(result.ok ? "Dispositivo de audio cambiado" : "No se pudo abrir ese dispositivo; se usa el predeterminado", result.ok ? "success" : "warning");
  };
  root.querySelector("#device-test").onclick = () => action("preview_voice", { text: "Prueba de audio. Uno, dos, tres." });
  root.querySelector("#eleven-load").onclick = async () => {
    const result = await action("elevenlabs_refresh");
    if (result.ok) toast(`${result.count} voces de ElevenLabs cargadas. Elígelas en Voces → ElevenLabs.`, "success");
  };
  root.querySelector("#refresh-voices").onclick = () => { action("refresh_voices"); toast("Actualizando voces…"); };
  root.querySelector("#open-browser").onclick = () => window.open(location.href, "_blank");
  root.querySelector("#diag-refresh").onclick = async () => {
    Object.assign(store.state, await api("state"));
    root.querySelector("#diag").innerHTML = diagnosticsHtml();
  };
}

async function loadDevices() {
  const data = await api("audio-devices");
  const select = root.querySelector("#device");
  if (!select) return;
  select.innerHTML = `<option value="">Predeterminado de Windows</option>${data.devices.map((d) => `<option ${d === data.current ? "selected" : ""}>${esc(d)}</option>`).join("")}`;
}

export default {
  id: "settings",
  label: "Ajustes",
  icon: "settings",
  render,
  onEvent(type) {
    if (root?.isConnected && (type === "tts.state" || type === "platform.status")) {
      const el = root.querySelector("#diag");
      if (el) el.innerHTML = diagnosticsHtml();
    }
  },
};
