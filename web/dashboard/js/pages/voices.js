import { action, bindForm, esc, getConfig, icon, rangeHtml, setConfig, store, switchHtml, toast } from "../core.js";

const ENGINE_LABEL = {
  edge: "Neuronal (online)", piper: "Piper · sin internet", kokoro: "IA Kokoro · sin internet", elevenlabs: "IA ElevenLabs (tu clave)",
  tiktok: "TikTok (sessionid)", sapi: "Windows · sin internet", google: "Google (online)",
};
let piperCatalog = null;

// Motores que solo funcionan con una clave del usuario.
function missingCredential(engine) {
  if (engine === "tiktok" && !getConfig("tts.tiktok_session_id")) return "Las voces de TikTok necesitan tu sessionid (Ajustes)";
  if (engine === "elevenlabs" && !getConfig("tts.elevenlabs_key")) return "ElevenLabs necesita tu clave API (Ajustes)";
  return "";
}

function mainVoiceWarning() {
  const voice = store.voices.find((v) => v.id === getConfig("tts.voice"));
  const problem = voice && missingCredential(voice.engine);
  return problem
    ? `<div class="callout warn small" style="margin-bottom:10px">⚠️ Tu voz principal (<b>${esc(voice.name)}</b>) no puede sonar: ${problem}. Mientras tanto todo suena con la voz de respaldo, por eso las voces parecen iguales. Elige una voz <b>Neuronal</b>, <b>Piper</b> o <b>Windows</b>, o añade la clave.</div>`
    : "";
}
const downloads = {};
import { assignVoice } from "./live.js";

let root, search = "", language = "es", gender = "all", engine = "edge";

const ALIASES = [
  ["mexicano / mexicana", "🇲🇽"], ["argentino / argentina", "🇦🇷"], ["colombiano / colombiana", "🇨🇴"],
  ["chileno / chilena", "🇨🇱"], ["peruano / peruana", "🇵🇪"], ["venezolano / venezolana", "🇻🇪"],
  ["cubano / cubana", "🇨🇺"], ["dominicano / dominicana", "🇩🇴"], ["espanol / espanola", "🇪🇸"],
  ["gringo / gringa", "🇺🇸"], ["ingles / inglesa", "🇬🇧"], ["brasileno / brasilena", "🇧🇷"],
  ["frances / francesa", "🇫🇷"], ["italiano / italiana", "🇮🇹"], ["aleman / alemana", "🇩🇪"],
  ["japones / japonesa", "🇯🇵"], ["coreano / coreana", "🇰🇷"], ["ruso / rusa", "🇷🇺"],
];

function filtered() {
  const q = search.toLowerCase();
  return store.voices.filter((v) =>
    (engine === "all" || v.engine === engine) &&
    (language === "all" || v.language === language) &&
    (gender === "all" || v.gender === gender) &&
    (!q || `${v.name} ${v.country} ${v.locale} ${v.language_name} ${v.id}`.toLowerCase().includes(q)));
}

function renderList() {
  const box = root.querySelector("#voice-list");
  if (!box) return;
  const selected = getConfig("tts.voice");
  const warning = root.querySelector("#main-voice-warning");
  if (warning) warning.innerHTML = mainVoiceWarning();
  const voices = filtered();
  root.querySelector("#voice-count").textContent = `${voices.length} voces`;
  box.innerHTML = voices.length ? voices.slice(0, 400).map((v) => `
    <div class="voice ${v.id === selected ? "selected" : ""}" data-voice="${esc(v.id)}">
      <div class="flag">${esc((v.locale.split("-")[1] || v.locale).slice(0, 3))}</div>
      <div style="flex:1;min-width:0"><div class="vname">${esc(v.name)} ${v.id === selected ? '<span class="tag sub">En uso</span>' : ""}${missingCredential(v.engine) ? ' <span class="tag" title="' + missingCredential(v.engine) + '">🔑 requiere clave</span>' : ""}</div>
        <div class="vmeta">${esc(v.language_name)} · ${esc(v.country || v.locale)} · ${v.gender === "Female" ? "Mujer" : v.gender === "Male" ? "Hombre" : "—"} · ${ENGINE_LABEL[v.engine] || v.engine}</div></div>
      <button class="btn sm icon" data-preview="${esc(v.id)}" title="Escuchar">${icon("play")}</button>
    </div>`).join("") : '<div class="empty">No hay voces con esos filtros.</div>';
}

function renderUserVoices() {
  const box = root.querySelector("#user-voices");
  if (!box) return;
  const entries = Object.entries(getConfig("tts.user_voices", {}));
  box.innerHTML = entries.length ? `
    <table class="table"><thead><tr><th>Espectador</th><th>Voz</th><th>Personaje</th><th></th></tr></thead><tbody>
    ${entries.map(([key, value]) => {
      const voice = store.voices.find((v) => v.id === value.voice);
      const preset = store.state.presets.find((p) => p.id === value.preset);
      return `<tr><td><b>${esc(value.name || key.split(":")[1])}</b> <span class="faint small">${esc(key.split(":")[0])}</span></td>
        <td>${voice ? `${esc(voice.name)} <span class="faint small">${esc(voice.country)}</span>` : esc(value.voice || "Principal")}</td>
        <td>${preset ? `${preset.emoji} ${preset.name}` : "—"}</td>
        <td style="text-align:right"><button class="btn sm ghost" data-edit-user="${esc(key)}">${icon("edit")}</button>
        <button class="btn sm ghost" data-del-user="${esc(key)}">${icon("trash")}</button></td></tr>`;
    }).join("")}</tbody></table>`
    : '<div class="faint small">Nadie tiene voz propia todavía. Asígnalas desde el chat (botón de voz en cada mensaje) o deja que usen <code>!voz</code>.</div>';
}

let kokoroStatus = null;

async function renderAI() {
  const box = root?.querySelector("#ai-card");
  if (!box) return;
  if (!kokoroStatus) kokoroStatus = await action("kokoro_status");
  const download = downloads.kokoro;
  const kokoro = store.voices.filter((v) => v.engine === "kokoro");
  const eleven = store.voices.filter((v) => v.engine === "elevenlabs");
  const hasKey = !!getConfig("tts.elevenlabs_key");
  box.innerHTML = `
    <h2>${icon("sparkles")}Voces de IA</h2>
    <p class="sub">Voces generadas por inteligencia artificial, más naturales que las clásicas.</p>
    <div class="grid g2">
      <div class="stack" style="padding:14px;border:1px solid var(--line);border-radius:12px;background:var(--bg-2)">
        <div class="row"><b>Kokoro</b><span class="pill ${kokoroStatus?.installed ? "connected" : ""}">${kokoroStatus?.installed ? "Instalada" : "No instalada"}</span><span class="pill waiting">Sin internet</span></div>
        <span class="small muted">IA que corre en tu PC, gratis y sin límites. Español: <b>Alex</b>, <b>Santa</b> (hombre) y <b>Dora</b> (mujer), más voces en inglés, portugués, francés e italiano. Descarga única de ~${kokoroStatus?.size_mb || 355} MB. Tarda ~1 s por frase.</span>
        ${kokoroStatus?.available === false ? '<div class="callout warn small">Falta la librería: ejecuta update.bat.</div>' : ""}
        <div class="row">
          ${kokoroStatus?.installed
            ? `<button class="btn sm" data-try-voice="kokoro:em_alex">${icon("play")}Alex</button><button class="btn sm" data-try-voice="kokoro:ef_dora">${icon("play")}Dora</button><button class="btn sm" data-try-voice="kokoro:em_santa">${icon("play")}Santa</button>
               <button class="btn sm ghost" id="kokoro-del">${icon("trash")}Borrar</button>`
            : download && !download.error ? `<span class="small">Descargando… ${download.percent || 0}%</span>`
            : `<button class="btn primary sm" id="kokoro-get">${icon("upload")}Descargar Kokoro</button>`}
        </div>
        ${kokoro.length ? `<span class="small faint">${kokoro.length} voces instaladas. Filtra por “IA Kokoro” arriba para elegir una.</span>` : ""}
      </div>
      <div class="stack" style="padding:14px;border:1px solid var(--line);border-radius:12px;background:var(--bg-2)">
        <div class="row"><b>ElevenLabs</b><span class="pill ${hasKey ? "connected" : ""}">${hasKey ? "Clave puesta" : "Sin clave"}</span><span class="pill waiting">Online</span></div>
        <span class="small muted">La IA de voz más realista, y puedes <b>clonar voces</b> en elevenlabs.io (con permiso de la persona). El plan gratis trae ~10.000 caracteres al mes (unos 150–250 mensajes): úsala para alertas o personajes especiales.</span>
        <div class="row">
          <button class="btn sm" onclick="window.lvsNavigate('settings')">${icon("settings")}${hasKey ? "Cambiar clave" : "Poner clave"}</button>
          ${hasKey ? `<button class="btn sm" id="eleven-refresh">${icon("refresh")}Cargar mis voces</button>` : ""}
        </div>
        ${eleven.length ? `<span class="small faint">${eleven.length} voces de tu cuenta. Filtra por “ElevenLabs” arriba.</span>` : ""}
      </div>
    </div>`;
}

function renderPiper() {
  const box = root?.querySelector("#piper-list");
  if (!box) return;
  const installed = store.voices.filter((v) => v.engine === "piper");
  const installedKeys = new Set(installed.map((v) => v.id.slice(6)));
  const rows = (piperCatalog || []).filter((entry) => !installedKeys.has(entry.key));
  box.innerHTML = `
    ${installed.length ? `<div class="small muted" style="margin:6px 0">Instaladas</div><div class="chips">${installed.map((v) =>
      `<span class="chip">🟢 ${esc(v.name)} · ${esc(v.locale)}<button data-try-voice="${esc(v.id)}" title="Escuchar">▶</button><button data-piper-del="${esc(v.id.slice(6))}" title="Borrar">×</button></span>`).join("")}</div>` : ""}
    ${piperCatalog ? `<table class="table" style="margin-top:10px"><thead><tr><th>Voz</th><th>Idioma</th><th>Calidad</th><th>Tamaño</th><th></th></tr></thead><tbody>
      ${rows.map((entry) => {
        const state = downloads[entry.key];
        return `<tr><td><b>${esc(entry.name)}</b>${entry.speakers > 1 ? ` <span class="faint small">${entry.speakers} voces</span>` : ""}</td>
          <td class="small">${esc(entry.locale)} ${esc(entry.country)}</td><td class="small">${esc(entry.quality)}</td><td class="small">${entry.size_mb} MB</td>
          <td style="text-align:right">${state && state.percent !== undefined && !state.error ? `<span class="small">${state.percent}%</span>`
            : `<button class="btn sm" data-piper-get="${esc(entry.key)}">${icon("upload")}Descargar</button>`}</td></tr>`;
      }).join("")}</tbody></table>` : ""}`;
}

function render(target) {
  root = target;
  const languages = [...new Map(store.voices.map((v) => [v.language, v.language_name])).entries()].sort((a, b) => a[1].localeCompare(b[1]));
  root.innerHTML = `
    <div class="page-head"><div><h1>Voces</h1><p>Más de 300 voces neuronales gratis, personajes y una voz distinta para cada espectador.</p></div>
      <button class="btn" id="refresh">${icon("refresh")}Actualizar catálogo</button></div>
    <div class="grid g2">
      <div class="card">
        <div class="row" style="margin-bottom:12px"><h2 style="margin:0">${icon("voice")}Voz principal</h2><span class="spacer"></span><span class="faint small" id="voice-count"></span></div>
        <div class="row nowrap" style="margin-bottom:10px"><input class="input" id="search" placeholder="Buscar: Dalia, México, inglés, hombre..." value="${esc(search)}"></div>
        <div class="row" style="margin-bottom:12px">
          <select class="input" id="language" style="width:auto"><option value="all">Todos los idiomas</option>${languages.map(([code, name]) => `<option value="${code}" ${code === language ? "selected" : ""}>${esc(name)}</option>`).join("")}</select>
          <div class="seg" id="gender">${[["all", "Todas"], ["Female", "Mujer"], ["Male", "Hombre"]].map(([id, l]) => `<button data-g="${id}" class="${gender === id ? "active" : ""}">${l}</button>`).join("")}</div>
          <div class="seg" id="engine">${[["edge", "Neuronales"], ["kokoro", "IA Kokoro"], ["elevenlabs", "ElevenLabs"], ["piper", "Piper"], ["tiktok", "TikTok"], ["sapi", "Windows"], ["google", "Google"], ["all", "Todas"]].map(([id, l]) => `<button data-e="${id}" class="${engine === id ? "active" : ""}">${l}</button>`).join("")}</div>
        </div>
        <div id="main-voice-warning"></div>
        <div class="voice-list" id="voice-list"></div>
      </div>
      <div class="stack">
        <div class="card">
          <h2>${icon("wand")}Velocidad y tono</h2>
          <p class="sub">Se aplica a la voz principal. Cada personaje suma su propio ajuste.</p>
          <div class="stack">
            ${rangeHtml("tts.rate", "Velocidad", -50, 100, 5, "%")}
            ${rangeHtml("tts.pitch", "Tono", -50, 50, 1, " Hz")}
            ${rangeHtml("audio.tts_volume", "Volumen de la voz", 0, 100, 1, "%")}
            <div class="row"><input class="input" id="test-text" value="¡Hola! Gracias por el follow, bienvenido al directo." style="flex:1"><button class="btn primary" id="test">${icon("play")}Probar</button></div>
          </div>
        </div>
        <div class="card">
          <h2>${icon("sparkles")}Personajes</h2>
          <p class="sub">Haz clic para escuchar con la voz principal. Los espectadores los activan con <code>!voz ardilla</code>.</p>
          <div class="presets">${store.state.presets.map((p) => `<div class="preset" data-preset="${p.id}"><div class="e">${p.emoji}</div><b>${p.name}</b><small>${p.pitch >= 0 ? "+" : ""}${p.pitch}Hz · ${p.rate >= 0 ? "+" : ""}${p.rate}%</small></div>`).join("")}</div>
        </div>
        <div class="card">
          <h2>${icon("users")}Una voz por espectador</h2>
          <div class="stack" style="margin-top:12px">
            ${switchHtml("tts.random_voice_per_user", "Voz aleatoria para cada persona", "Cada espectador recibe automáticamente una voz distinta (siempre la misma).")}
            <label class="field"><span>Idioma de las voces aleatorias</span><select class="input" data-bind="tts.random_voice_language">${languages.map(([code, name]) => `<option value="${code}">${esc(name)}</option>`).join("")}</select></label>
            ${switchHtml("tts.allow_voice_command", "Permitir que el chat elija con !voz", "Ej: <code>!voz argentino</code>, <code>!voz gringo</code>, <code>!voz ardilla</code>, <code>!voz normal</code>.")}
          </div>
        </div>
      </div>
    </div>
    <div class="grid g2" style="margin-top:16px">
      <div class="card"><h2>${icon("users")}Voces asignadas</h2><p class="sub">Espectadores con voz propia.</p><div id="user-voices"></div></div>
      <div class="card"><h2>${icon("message")}Lo que el chat puede escribir</h2><p class="sub">Comando <code>!voz</code> + una de estas palabras (sin tildes también sirve):</p>
        <div class="chips">${ALIASES.map(([name, flag]) => `<span class="chip" style="padding-right:10px">${flag} ${name}</span>`).join("")}
          ${store.state.presets.slice(1).map((p) => `<span class="chip" style="padding-right:10px">${p.emoji} ${p.id}</span>`).join("")}
          <span class="chip" style="padding-right:10px">🎲 random</span><span class="chip" style="padding-right:10px">↩️ normal</span></div>
      </div>
    </div>
    <div class="card" style="margin-top:16px" id="ai-card"></div>
    <div class="card" style="margin-top:16px">
      <div class="row"><h2 style="margin:0">${icon("upload")}Voces sin internet (Piper)</h2><span class="spacer"></span>
        <button class="btn" id="piper-load">${icon("search")}Ver voces para descargar</button></div>
      <p class="sub" style="margin-top:4px">Voces neuronales que se ejecutan en tu PC: no dependen de Microsoft ni de ningún servidor. Se descargan una vez (20–110 MB) desde el repositorio oficial de Piper.
        También puedes poner tus propios modelos <code>.onnx</code> + <code>.onnx.json</code> en la carpeta <code>voices/piper</code> (ver Guía → Voces extra).</p>
      <div id="piper-list"></div>
    </div>`;

  bindForm(root);
  renderList();
  renderPiper();
  renderAI();
  root.querySelector("#piper-load").onclick = async () => {
    root.querySelector("#piper-list").innerHTML = '<div class="faint small">Cargando catálogo…</div>';
    const result = await action("piper_catalog");
    if (result.ok) { piperCatalog = result.voices; renderPiper(); }
  };
  renderUserVoices();

  root.querySelector("#search").addEventListener("input", (e) => { search = e.target.value; renderList(); });
  root.querySelector("#language").addEventListener("change", (e) => { language = e.target.value; renderList(); });
  root.querySelector("#refresh").onclick = async () => { toast("Actualizando catálogo de voces..."); await action("refresh_voices"); };
  root.querySelector("#test").onclick = () => action("preview_voice", { text: root.querySelector("#test-text").value });
  root.addEventListener("click", (event) => {
    const el = event.target.closest("[data-g],[data-e],[data-preview],[data-voice],[data-preset],[data-del-user],[data-edit-user],[data-piper-get],[data-piper-del],[data-try-voice],#kokoro-get,#kokoro-del,#eleven-refresh");
    if (!el) return;
    if (el.id === "kokoro-get") {
      downloads.kokoro = { percent: 0 };
      action("kokoro_download");
      renderAI();
      return;
    }
    if (el.id === "kokoro-del") {
      if (confirm("¿Borrar el modelo Kokoro (~355 MB)?")) action("kokoro_delete").then(() => { kokoroStatus = null; renderAI(); });
      return;
    }
    if (el.id === "eleven-refresh") {
      action("elevenlabs_refresh").then((r) => r.ok && toast(`${r.count} voces de ElevenLabs cargadas`, "success"));
      return;
    }
    if (el.dataset.piperGet) {
      const entry = piperCatalog.find((item) => item.key === el.dataset.piperGet);
      downloads[entry.key] = { percent: 0 };
      action("piper_download", { entry });
      renderPiper();
      return;
    }
    if (el.dataset.piperDel) {
      if (confirm(`¿Borrar la voz ${el.dataset.piperDel}?`)) action("piper_delete", { key: el.dataset.piperDel });
      return;
    }
    if (el.dataset.tryVoice) { action("preview_voice", { voice: el.dataset.tryVoice, text: root.querySelector("#test-text").value }); return; }
    if (el.dataset.g) { gender = el.dataset.g; root.querySelectorAll("[data-g]").forEach((b) => b.classList.toggle("active", b === el)); renderList(); }
    else if (el.dataset.e) { engine = el.dataset.e; root.querySelectorAll("[data-e]").forEach((b) => b.classList.toggle("active", b === el)); renderList(); }
    else if (el.dataset.preview) { event.stopPropagation(); action("preview_voice", { voice: el.dataset.preview, text: root.querySelector("#test-text").value }); }
    else if (el.dataset.voice) {
      setConfig("tts.voice", el.dataset.voice, { immediate: true });
      renderList();
      const voice = store.voices.find((v) => v.id === el.dataset.voice);
      const problem = voice && missingCredential(voice.engine);
      if (problem) toast(`${problem}. Hasta entonces sonará la voz de respaldo.`, "warning", 6000);
      else toast("Voz principal cambiada", "success", 1500);
    }
    else if (el.dataset.preset) action("preview_voice", { preset: el.dataset.preset, text: root.querySelector("#test-text").value });
    else if (el.dataset.delUser) {
      const voices = { ...getConfig("tts.user_voices", {}) };
      delete voices[el.dataset.delUser];
      setConfig("tts.user_voices", voices, { immediate: true });
      renderUserVoices();
    } else if (el.dataset.editUser) {
      const key = el.dataset.editUser;
      assignVoice(key, getConfig("tts.user_voices", {})[key]?.name || key.split(":")[1]);
    }
  });
}

export default {
  id: "voices",
  label: "Voces",
  icon: "voice",
  render,
  onEvent(type, data) {
    if (!root?.isConnected) return;
    if (type === "voices.loaded" || type === "voices") setTimeout(() => { kokoroStatus = null; renderList(); renderPiper(); renderAI(); }, 400);
    if (type === "download") {
      downloads[data.key] = data;
      if (data.done || data.error) delete downloads[data.key];
      renderPiper();
      if (data.key === "kokoro") renderAI();
    }
  },
};
