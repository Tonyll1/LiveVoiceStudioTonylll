import { action, bindForm, esc, getConfig, icon, rangeHtml, setConfig, store, switchHtml, toast } from "../core.js";
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
  const voices = filtered();
  root.querySelector("#voice-count").textContent = `${voices.length} voces`;
  box.innerHTML = voices.length ? voices.slice(0, 400).map((v) => `
    <div class="voice ${v.id === selected ? "selected" : ""}" data-voice="${esc(v.id)}">
      <div class="flag">${esc((v.locale.split("-")[1] || v.locale).slice(0, 3))}</div>
      <div style="flex:1;min-width:0"><div class="vname">${esc(v.name)} ${v.id === selected ? '<span class="tag sub">En uso</span>' : ""}</div>
        <div class="vmeta">${esc(v.language_name)} · ${esc(v.country || v.locale)} · ${v.gender === "Female" ? "Mujer" : v.gender === "Male" ? "Hombre" : "Neutral"} · ${v.engine === "edge" ? "Neuronal" : v.engine === "sapi" ? "Windows (offline)" : "Google"}</div></div>
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
          <div class="seg" id="engine">${[["edge", "Neuronales"], ["sapi", "Windows"], ["google", "Google"], ["all", "Todas"]].map(([id, l]) => `<button data-e="${id}" class="${engine === id ? "active" : ""}">${l}</button>`).join("")}</div>
        </div>
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
    </div>`;

  bindForm(root);
  renderList();
  renderUserVoices();

  root.querySelector("#search").addEventListener("input", (e) => { search = e.target.value; renderList(); });
  root.querySelector("#language").addEventListener("change", (e) => { language = e.target.value; renderList(); });
  root.querySelector("#refresh").onclick = async () => { toast("Actualizando catálogo de voces..."); await action("refresh_voices"); };
  root.querySelector("#test").onclick = () => action("preview_voice", { text: root.querySelector("#test-text").value });
  root.addEventListener("click", (event) => {
    const el = event.target.closest("[data-g],[data-e],[data-preview],[data-voice],[data-preset],[data-del-user],[data-edit-user]");
    if (!el) return;
    if (el.dataset.g) { gender = el.dataset.g; root.querySelectorAll("[data-g]").forEach((b) => b.classList.toggle("active", b === el)); renderList(); }
    else if (el.dataset.e) { engine = el.dataset.e; root.querySelectorAll("[data-e]").forEach((b) => b.classList.toggle("active", b === el)); renderList(); }
    else if (el.dataset.preview) { event.stopPropagation(); action("preview_voice", { voice: el.dataset.preview, text: root.querySelector("#test-text").value }); }
    else if (el.dataset.voice) { setConfig("tts.voice", el.dataset.voice, { immediate: true }); renderList(); toast("Voz principal cambiada", "success", 1500); }
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
  onEvent(type) {
    if (root?.isConnected && (type === "voices.loaded" || type === "voices")) setTimeout(renderList, 300);
  },
};
