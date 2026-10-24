import { bindForm, esc, fieldHtml, getConfig, icon, selectHtml, setConfig, switchHtml, WHO_OPTIONS } from "../core.js";
import { welcomeCardHtml } from "./welcome.js";

let root;

function chipList(path, placeholder) {
  const items = getConfig(path, []);
  return `
    <div class="chips" data-chips="${path}">${items.map((item) => `<span class="chip">${esc(item.includes(":") ? `${item.split(":")[1]} (${item.split(":")[0]})` : item)}<button data-remove-chip="${esc(item)}">×</button></span>`).join("") || '<span class="faint small">Vacío</span>'}</div>
    <div class="row nowrap" style="margin-top:8px"><input class="input" data-chip-input="${path}" placeholder="${placeholder}"><button class="btn" data-add-chip="${path}">${icon("plus")}</button></div>`;
}

function replacementsHtml() {
  const entries = Object.entries(getConfig("tts.replacements", {}));
  return `
    <table class="table"><tbody>${entries.map(([from, to]) => `<tr><td class="mono">${esc(from)}</td><td>→</td><td>${esc(to)}</td>
      <td style="text-align:right"><button class="btn sm ghost" data-del-rep="${esc(from)}">${icon("trash")}</button></td></tr>`).join("")}</tbody></table>
    <div class="row nowrap" style="margin-top:8px"><input class="input" id="rep-from" placeholder="Escriben… (ej: xd)"><input class="input" id="rep-to" placeholder="Se lee… (ej: equis de)">
      <button class="btn" id="rep-add">${icon("plus")}</button></div>`;
}

function render(target) {
  root = target;
  root.innerHTML = `
    <div class="page-head"><div><h1>Lectura del chat</h1><p>Qué se lee, quién puede hablar y cómo suena cada mensaje.</p></div></div>
    <div class="grid g2">
      <div class="stack">
        <div class="card">
          <h2>${icon("voice")}Básico</h2>
          <div class="stack" style="margin-top:12px">
            ${switchHtml("tts.enabled", "Leer el chat en voz alta")}
            ${switchHtml("tts.read_username", "Decir el nombre de quien escribe")}
            ${fieldHtml("Formato", '<input class="input" data-bind="tts.template">', "Usa {user}, {message} y {platform}. Ej: <code>{user}: {message}</code>")}
            ${switchHtml("tts.read_platform", "Decir la plataforma (útil en multistream)")}
            <div class="grid g2">
              ${fieldHtml("Máx. caracteres por mensaje", '<input class="input" type="number" min="20" max="500" data-bind="tts.max_length">')}
              ${fieldHtml("Máx. mensajes en cola", '<input class="input" type="number" min="1" max="200" data-bind="tts.max_queue">', "Si el chat va muy rápido se descartan los más viejos.")}
            </div>
          </div>
        </div>
        <div class="card">
          <h2>${icon("users")}¿Quién puede usar la voz?</h2>
          <div class="stack" style="margin-top:12px">
            ${fieldHtml("Leer mensajes de", selectHtml("tts.who", WHO_OPTIONS), "En TikTok se detectan seguidores; en Twitch/Kick/YouTube “seguidores” equivale a todos.")}
            ${fieldHtml("Prefijo obligatorio (opcional)", '<input class="input" data-bind="tts.prefix" placeholder="Ej: !tts  — vacío = se lee todo">', "Si lo pones, solo se leen los mensajes que empiecen así.")}
            ${fieldHtml("Espera por persona (segundos)", '<input class="input" type="number" min="0" max="600" data-bind="tts.user_cooldown">', "Evita que una sola persona acapare la voz. 0 = sin límite.")}
            ${switchHtml("tts.skip_commands", "No leer comandos (mensajes que empiezan con !)")}
            ${switchHtml("tts.ignore_bots", "Ignorar bots (Nightbot, StreamElements…)")}
          </div>
        </div>
        ${welcomeCardHtml()}
        <div class="card">
          <h2>${icon("mute")}Usuarios ignorados</h2>
          <p class="sub">Nunca se leen. También puedes silenciar a alguien desde el chat en vivo.</p>
          ${chipList("tts.ignored_users", "nombre de usuario")}
        </div>
      </div>
      <div class="stack">
        <div class="card">
          <h2>${icon("shield")}Filtros y moderación</h2>
          <div class="stack" style="margin-top:12px">
            ${switchHtml("moderation.filter_spam", "Filtro antispam", "No lee mensajes repetidos, solo números, solo símbolos o letras repetidas.")}
            ${switchHtml("tts.skip_links", "No leer enlaces (dice “un enlace”)")}
            ${switchHtml("tts.read_emojis", "Leer emojis")}
            ${fieldHtml("Con palabras bloqueadas", selectHtml("moderation.blocked_mode", [["replace", "Censurar con ***"], ["mute", "Mostrar pero no leer"], ["hide", "Ocultar el mensaje"]]))}
          </div>
          <div style="margin-top:12px"><span class="small muted">Palabras bloqueadas</span>${chipList("moderation.blocked_words", "palabra o frase")}</div>
        </div>
        <div class="card">
          <h2>${icon("bell")}Leer eventos</h2>
          <p class="sub">Se combinan con los textos de la página Alertas.</p>
          <div class="grid g2">
            ${switchHtml("tts.read_events.follow", "Follows")}${switchHtml("tts.read_events.gift", "Regalos / bits")}
            ${switchHtml("tts.read_events.sub", "Suscripciones")}${switchHtml("tts.read_events.raid", "Raids")}
            ${switchHtml("tts.read_events.share", "Compartidos")}${switchHtml("tts.read_events.join", "Entradas al directo")}
          </div>
        </div>
        <div class="card">
          <h2>${icon("edit")}Pronunciación</h2>
          <p class="sub">Reemplaza abreviaturas y palabras para que la voz las diga bien.</p>
          <div id="replacements">${replacementsHtml()}</div>
        </div>
        <div class="card">
          <h2>${icon("refresh")}Respaldo automático</h2>
          ${switchHtml("tts.fallback_enabled", "Si una voz falla, usar otro motor", "Edge → Google → Windows. Así el directo nunca se queda mudo aunque Microsoft cambie algo.")}
        </div>
      </div>
    </div>`;
  bindForm(root);
  if (root.dataset.wired) return;
  root.dataset.wired = "1";
  root.addEventListener("click", onClick);
  root.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && event.target.dataset.chipInput) root.querySelector(`[data-add-chip="${event.target.dataset.chipInput}"]`).click();
  });
}

function rerender() {
  const scroll = document.getElementById("main").scrollTop;
  render(root);
  document.getElementById("main").scrollTop = scroll;
}

function onClick(event) {
  const el = event.target.closest("button");
  if (!el) return;
  if (el.dataset.addChip) {
    const path = el.dataset.addChip;
    const input = root.querySelector(`[data-chip-input="${path}"]`);
    const value = input.value.trim().toLowerCase().replace(/^@/, "");
    if (!value) return;
    setConfig(path, [...new Set([...getConfig(path, []), value])], { immediate: true });
    rerender();
  } else if (el.dataset.removeChip !== undefined) {
    const path = el.closest("[data-chips]").dataset.chips;
    setConfig(path, getConfig(path, []).filter((item) => item !== el.dataset.removeChip), { immediate: true });
    rerender();
  } else if (el.id === "rep-add") {
    const from = root.querySelector("#rep-from").value.trim().toLowerCase();
    const to = root.querySelector("#rep-to").value.trim();
    if (!from || !to) return;
    setConfig("tts.replacements", { ...getConfig("tts.replacements", {}), [from]: to }, { immediate: true });
    rerender();
  } else if (el.dataset.delRep) {
    const reps = { ...getConfig("tts.replacements", {}) };
    delete reps[el.dataset.delRep];
    setConfig("tts.replacements", reps, { immediate: true });
    rerender();
  }
}

export default { id: "reading", label: "Lectura", icon: "book", render };
