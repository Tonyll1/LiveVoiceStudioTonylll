import { action, bindForm, copy, icon, rangeHtml, switchHtml } from "../core.js";

const OVERLAYS = [
  { id: "alerts", name: "Alertas", desc: "Animación con nombre y avatar en cada follow, regalo, sub o raid.", size: "1920 × 1080 (pantalla completa)", test: "gift" },
  { id: "chat", name: "Chat", desc: "Chat de todas las plataformas juntas, con icono de cada una.", size: "450 × 700", test: "chat" },
  { id: "tts", name: "Subtítulos de voz", desc: "Muestra quién está hablando y lo que dice la voz.", size: "1000 × 220", test: "chat" },
  { id: "goal", name: "Meta (likes)", desc: "Barra de progreso de la meta. Cambia ?goal= por followers, gifts o subs.", size: "700 × 120", query: "?goal=likes", test: "like" },
  { id: "goal", name: "Meta (seguidores)", desc: "Barra de progreso de seguidores.", size: "700 × 120", query: "?goal=followers", test: "follow" },
  { id: "leaderboard", name: "Top regaladores", desc: "Ranking de quienes más regalaron en esta sesión. ?type=points para el ranking de puntos.", size: "380 × 420", test: "gift" },
  { id: "giveaway", name: "Sorteo", desc: "Contador de participantes y ruleta con el ganador.", size: "600 × 500" },
  { id: "poll", name: "Encuesta", desc: "Barras de votación en tiempo real.", size: "600 × 450" },
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
      <h2>${icon("settings")}Apariencia</h2>
      <div class="grid g4" style="margin-top:12px;align-items:end">
        <label class="field"><span>Color principal</span><input class="input" type="color" data-bind="overlay.accent" style="height:40px;padding:4px"></label>
        ${rangeHtml("overlay.font_size", "Tamaño de letra", 14, 40, 1, "px")}
        ${rangeHtml("overlay.chat_max", "Mensajes visibles (chat)", 3, 20, 1, "")}
        ${rangeHtml("overlay.chat_fade_seconds", "Ocultar mensajes tras (s, 0 = nunca)", 0, 120, 5, "s")}
      </div>
      <div style="margin-top:12px">${switchHtml("overlay.show_platform_icon", "Mostrar icono de la plataforma en el chat")}</div>
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
  root.addEventListener("click", (event) => {
    const el = event.target.closest("button");
    if (!el) return;
    if (el.dataset.copy) copy(url(OVERLAYS[Number(el.dataset.copy)]));
    if (el.dataset.test) action("simulate", { kind: el.dataset.test });
  });
}

export default { id: "overlays", label: "Overlays", icon: "layers", render };
