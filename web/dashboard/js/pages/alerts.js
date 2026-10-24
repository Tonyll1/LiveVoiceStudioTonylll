import { action, bindForm, esc, getConfig, icon, setConfig, switchHtml, toast, uploadSound } from "../core.js";

const KINDS = [
  ["follow", "Nuevo seguidor", "userplus", "TikTok · Twitch*", ""],
  ["gift", "Regalos", "gift", "TikTok · Kick · YouTube (Super Chat) · subs regaladas", "Valor mínimo (💎 / monedas)"],
  ["sub", "Suscripciones", "sparkles", "Todas", ""],
  ["bits", "Bits", "zap", "Twitch", "Mínimo de bits"],
  ["raid", "Raids / hosts", "users", "Twitch · Kick", ""],
  ["share", "Compartir directo", "external", "TikTok", ""],
  ["like", "Hitos de likes", "heart", "TikTok", "Avisar cada N likes"],
  ["join", "Entradas al directo", "eye", "TikTok", ""],
];

let root;

function card([kind, title, ic, platforms, minLabel]) {
  const sound = getConfig(`alerts.${kind}.sound`, "");
  return `
    <div class="card" data-kind="${kind}">
      <div class="row"><h2 style="margin:0">${icon(ic)}${title}</h2><span class="spacer"></span>${switchHtml(`alerts.${kind}.enabled`, "")}</div>
      <p class="sub" style="margin-top:4px">${platforms}</p>
      <div class="stack">
        <label class="field"><span>Texto (se lee y aparece en el overlay)</span><input class="input" data-bind="alerts.${kind}.text"></label>
        <div class="row">${switchHtml(`alerts.${kind}.tts`, "Leer en voz")}${switchHtml(`alerts.${kind}.overlay`, "Mostrar en overlay")}</div>
        ${minLabel ? `<label class="field"><span>${minLabel}</span><input class="input" type="number" min="1" data-bind="alerts.${kind}.min_amount"></label>` : ""}
        <div class="row nowrap">
          <span class="small muted" style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(sound)}">${sound ? `🔊 ${esc(sound.split(/[\\/]/).pop())}` : "Sin sonido"}</span>
          <label class="btn sm">${icon("upload")}Sonido<input type="file" accept=".mp3,.wav,.ogg" hidden data-upload="${kind}"></label>
          ${sound ? `<button class="btn sm ghost icon" data-nosound="${kind}" title="Quitar sonido">${icon("x")}</button>` : ""}
          <button class="btn sm primary" data-test="${kind}">${icon("play")}Probar</button>
        </div>
      </div>
    </div>`;
}

function render(target) {
  root = target;
  root.innerHTML = `
    <div class="page-head"><div><h1>Alertas</h1><p>Agradece cada follow y regalo con voz, sonido y animación en pantalla.</p></div>
      ${switchHtml("alerts.enabled", "Alertas activadas")}</div>
    <div class="callout small">Variables: <code>{user}</code> nombre, <code>{amount}</code> cantidad, <code>{gift}</code> nombre del regalo. Añade el overlay <b>Alertas</b> en OBS para ver las animaciones (página Overlays).
      <br>* Los follows de Twitch, Kick y YouTube no se pueden leer sin iniciar sesión con la cuenta del canal.</div>
    <div class="grid g2" style="margin-top:16px">${KINDS.map(card).join("")}</div>
    <div class="card" style="margin-top:16px">
      <h2>${icon("message")}Bienvenida</h2>
      <p class="sub">Saluda a cada persona la primera vez que escribe en la sesión. Hace que la gente se sienta vista y vuelva a escribir.</p>
      <div class="row">${switchHtml("welcome.enabled", "Activar bienvenida")}${switchHtml("welcome.tts", "Leerla en voz")}</div>
      <label class="field" style="margin-top:10px"><span>Texto</span><input class="input" data-bind="welcome.text"></label>
    </div>`;
  bindForm(root);
  if (root.dataset.wired) return;
  root.dataset.wired = "1";
  root.addEventListener("click", async (event) => {
    const el = event.target.closest("button");
    if (!el) return;
    if (el.dataset.test) action("simulate", { kind: el.dataset.test });
    if (el.dataset.nosound) { setConfig(`alerts.${el.dataset.nosound}.sound`, "", { immediate: true }); render(root); }
  });
  root.addEventListener("change", async (event) => {
    const input = event.target.closest("[data-upload]");
    if (!input?.files[0]) return;
    try {
      const result = await uploadSound(input.files[0], "alerts");
      setConfig(`alerts.${input.dataset.upload}.sound`, result.path, { immediate: true });
      toast("Sonido guardado", "success");
      const scroll = document.getElementById("main").scrollTop;
      render(root);
      document.getElementById("main").scrollTop = scroll;
    } catch (error) {
      toast(error.message, "error");
    }
  });
}

export default { id: "alerts", label: "Alertas", icon: "bell", render };
