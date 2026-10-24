import { action, bindForm, copy, getConfig, icon, rangeHtml, setConfig, switchHtml } from "../core.js";

const THEMES = [["neon", "Neón", "💜"], ["minimal", "Minimal", "⚪"], ["gamer", "Gamer", "🎮"], ["pastel", "Pastel", "🍬"], ["glass", "Cristal", "🧊"]];
const FONTS = ["Inter", "Poppins", "Montserrat", "Nunito", "Bangers", "Orbitron", "Press Start 2P", "Comic Neue"];

const OVERLAYS = [
  { id: "all", name: "⭐ Todo en uno", desc: "Una sola fuente con alertas, subtítulos, meta, chat, actividad y comandos ya colocados. Usa ?hide=chat,events para quitar piezas.", size: "1920 × 1080", test: "gift" },
  { id: "alerts", name: "Alertas", desc: "Animación con nombre y avatar en cada follow, regalo, sub o raid.", size: "1920 × 1080 (pantalla completa)", test: "gift" },
  { id: "chat", name: "Chat", desc: "Chat de todas las plataformas juntas, con icono de cada una.", size: "450 × 700", test: "chat" },
  { id: "tts", name: "Subtítulos de voz", desc: "Muestra quién está hablando y lo que dice la voz.", size: "1000 × 220", test: "chat" },
  { id: "goal", name: "Meta (likes)", desc: "Barra de progreso de la meta. Cambia ?goal= por followers, gifts o subs.", size: "700 × 120", query: "?goal=likes", test: "like" },
  { id: "goal", name: "Meta (seguidores)", desc: "Barra de progreso de seguidores.", size: "700 × 120", query: "?goal=followers", test: "follow" },
  { id: "leaderboard", name: "Top regaladores", desc: "Ranking de quienes más regalaron en esta sesión. ?type=points para el ranking de puntos.", size: "380 × 420", test: "gift" },
  { id: "giveaway", name: "Sorteo", desc: "Contador de participantes y ruleta con el ganador.", size: "600 × 500" },
  { id: "poll", name: "Encuesta", desc: "Barras de votación en tiempo real.", size: "600 × 450" },
  { id: "events", name: "Actividad reciente", desc: "Lista de los últimos follows, regalos, subs y raids. ?kinds=follow,gift para filtrar.", size: "420 × 320", test: "follow" },
  { id: "latest", name: "Último seguidor", desc: "Etiqueta con el último seguidor. Cambia ?type= por gift, sub, bits o raid.", size: "500 × 70", query: "?type=follow", test: "follow" },
  { id: "latest", name: "Último regalo", desc: "Etiqueta con el último regalo y su cantidad.", size: "500 × 70", query: "?type=gift", test: "gift" },
  { id: "counter", name: "Contador de likes", desc: "Número animado. ?stat= likes, followers, viewers, messages, chatters, gift_value, subs o shares.", size: "320 × 70", query: "?stat=likes", test: "like" },
  { id: "counter", name: "Espectadores", desc: "Espectadores sumando todas las plataformas conectadas.", size: "320 × 70", query: "?stat=viewers" },
  { id: "command", name: "Comandos de sonido", desc: "Aviso “Ana usó !susto” cada vez que alguien activa un comando.", size: "600 × 300" },
];

let root;

function url(overlay) {
  return `${location.origin}/overlay/${overlay.id}${overlay.query || ""}`;
}

function render(target) {
  root = target;
  root.innerHTML = `
    <div class="page-head"><div><h1>Overlays para OBS</h1><p>Copia la URL y añádela en OBS como <b>Fuente → Navegador</b> (Browser Source). El fondo es transparente.</p></div>
      <button class="btn" onclick="window.lvsNavigate('guide')">${icon("help")}Cómo añadirlos</button></div>
    <div class="card" style="margin-bottom:16px">
      <div class="row"><h2 style="margin:0">${icon("settings")}Apariencia</h2><span class="spacer"></span>
        <span class="small faint">Los cambios se ven al momento en OBS.</span>
        <button class="btn sm" id="look-test">${icon("play")}Probar alerta</button></div>
      <div class="grid g2" style="margin-top:14px;align-items:start">
        <div class="stack">
          <div class="field"><span>Tema</span><div class="presets" id="themes">${THEMES.map(([id, name, emoji]) =>
            `<div class="preset ${getConfig("overlay.theme", "neon") === id ? "selected" : ""}" data-theme="${id}" style="${getConfig("overlay.theme", "neon") === id ? "border-color:var(--accent);background:var(--accent-soft)" : ""}"><div class="e">${emoji}</div><b>${name}</b></div>`).join("")}</div></div>
          <div class="grid g2">
            <label class="field"><span>Fuente</span><select class="input" data-bind="overlay.font">${FONTS.map((font) => `<option>${font}</option>`).join("")}</select></label>
            <label class="field"><span>Color principal</span><input class="input" type="color" data-bind="overlay.accent" style="height:40px;padding:4px"></label>
            <label class="field"><span>Color del texto</span><input class="input" type="color" data-bind="overlay.text_color" style="height:40px;padding:4px"></label>
            ${rangeHtml("overlay.card_opacity", "Opacidad del fondo", 0, 100, 5, "%")}
          </div>
          ${rangeHtml("overlay.font_size", "Tamaño de letra", 14, 40, 1, "px")}
        </div>
        <div class="stack">
          <div class="grid g2">
            <label class="field"><span>Posición de las alertas</span><select class="input" data-bind="overlay.alert_position">
              <option value="top">Arriba</option><option value="center">Centro</option><option value="bottom">Abajo</option></select></label>
            <label class="field"><span>Animación de entrada</span><select class="input" data-bind="overlay.alert_animation">
              <option value="pop">Pop</option><option value="bounce">Rebote</option><option value="slide">Caer desde arriba</option><option value="zoom">Zoom</option><option value="fade">Aparecer suave</option></select></label>
          </div>
          ${rangeHtml("overlay.alert_duration", "Duración de cada alerta", 2, 15, 1, " s")}
          ${rangeHtml("overlay.chat_max", "Mensajes visibles (chat)", 3, 20, 1, "")}
          ${rangeHtml("overlay.chat_fade_seconds", "Ocultar mensajes del chat tras (0 = nunca)", 0, 120, 5, " s")}
          ${switchHtml("overlay.show_platform_icon", "Mostrar icono de la plataforma en el chat")}
        </div>
      </div>
      <details style="margin-top:12px"><summary class="small muted" style="cursor:pointer">CSS personalizado (avanzado)</summary>
        <textarea class="input mono" data-bind="overlay.custom_css" rows="5" style="margin-top:8px" placeholder=".alert { border-radius: 0; }&#10;.m { font-style: italic; }"></textarea>
        <small class="faint">Se aplica a todos los overlays. Clases útiles: <code>.alert</code>, <code>.name</code>, <code>.title</code> (alertas), <code>.m</code> (chat), <code>.sub</code> (subtítulos), <code>.goal</code>, <code>.board</code>.</small>
      </details>
      <div class="overlay-preview" style="height:260px;margin-top:14px"><iframe id="look-preview" src="/overlay/all?preview=1"></iframe></div>
    </div>
    <div class="grid g2">
      ${OVERLAYS.map((o, i) => `
        <div class="card overlay-card">
          <div class="row"><h2 style="margin:0">${icon("layers")}${o.name}</h2><span class="spacer"></span><span class="faint small">${o.size}</span></div>
          <p class="sub" style="margin:4px 0 0">${o.desc}</p>
          <div class="url"><input class="input" readonly value="${url(o)}"><button class="btn icon" data-copy="${i}" title="Copiar">${icon("copy")}</button>
            <a class="btn icon" href="${url(o)}" target="_blank" title="Abrir">${icon("external")}</a>
            ${o.test ? `<button class="btn" data-test="${o.test}">${icon("play")}Probar</button>` : ""}</div>
          <div class="overlay-preview"><iframe src="${url(o)}${o.query ? "&" : "?"}preview=1" loading="lazy"></iframe></div>
        </div>`).join("")}
    </div>`;
  bindForm(root);
  root.querySelector("#themes").addEventListener("click", (event) => {
    const theme = event.target.closest("[data-theme]");
    if (!theme) return;
    setConfig("overlay.theme", theme.dataset.theme, { immediate: true });
    root.querySelectorAll("[data-theme]").forEach((el) => {
      const active = el === theme;
      el.style.borderColor = active ? "var(--accent)" : "";
      el.style.background = active ? "var(--accent-soft)" : "";
    });
  });
  root.addEventListener("click", (event) => {
    const el = event.target.closest("button");
    if (!el) return;
    if (el.dataset.copy) copy(url(OVERLAYS[Number(el.dataset.copy)]));
    if (el.id === "look-test") action("simulate", { kind: "gift" });
    if (el.dataset.test) action("simulate", { kind: el.dataset.test });
  });
}

export default { id: "overlays", label: "Overlays", icon: "layers", render };
