import { action, bindForm, esc, getConfig, icon, setConfig, switchHtml, toast, uploadSound } from "../core.js";
import { welcomeCardHtml } from "./welcome.js";
import { customAlertsHtml, wireCustomAlerts } from "./custom_alerts.js";
import { mountPlatformAlerts, platformAlertsHtml, wirePlatformAlerts } from "./platform_alerts.js";

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

function mediaThumb(path) {
  if (!path) return "";
  const url = `/media/${encodeURIComponent(path.split(/[\\/]/).pop())}`;
  return /\.(mp4|webm)$/i.test(path)
    ? `<video src="${url}" muted autoplay loop playsinline style="height:48px;border-radius:8px"></video>`
    : `<img src="${url}" style="height:48px;border-radius:8px">`;
}

function card([kind, title, ic, platforms, minLabel]) {
  const sound = getConfig(`alerts.${kind}.sound`, "");
  const media = getConfig(`alerts.${kind}.media`, "");
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
        </div>
        <div class="row nowrap">
          <span class="small muted" style="flex:1;display:flex;align-items:center;gap:8px;min-width:0">${media ? mediaThumb(media) : "Sin GIF / video"}</span>
          ${media ? `<input class="input" type="number" min="2" max="60" data-bind="alerts.${kind}.duration" title="Segundos en pantalla (0 = automático)" style="width:70px">` : ""}
          <label class="btn sm">${icon("upload")}GIF / video<input type="file" accept=".png,.jpg,.jpeg,.gif,.webp,.mp4,.webm" hidden data-upload-media="${kind}"></label>
          ${media ? `<button class="btn sm ghost icon" data-nomedia="${kind}" title="Quitar GIF / video">${icon("x")}</button>` : ""}
          <button class="btn sm primary" data-test="${kind}">${icon("play")}Probar</button>
        </div>
      </div>
    </div>`;
}

function rerender() {
  const scroll = document.getElementById("main").scrollTop;
  render(root);
  document.getElementById("main").scrollTop = scroll;
}

function render(target) {
  root = target;
  root.innerHTML = `
    <div class="page-head"><div><h1>Alertas</h1><p>Agradece cada follow y regalo con voz, sonido y animación en pantalla.</p></div>
      ${switchHtml("alerts.enabled", "Alertas activadas")}</div>
    <div class="callout small">Variables: <code>{user}</code> nombre, <code>{amount}</code> cantidad, <code>{gift}</code> nombre del regalo. Añade el overlay <b>Alertas</b> en OBS para ver las animaciones (página Overlays).
      <br>* Los follows de Twitch, Kick y YouTube no se pueden leer sin iniciar sesión con la cuenta del canal.</div>
    <div style="margin-top:16px">${platformAlertsHtml()}</div>
    <div style="margin-top:16px">${customAlertsHtml()}</div>
    <h3 style="margin:22px 0 0">Alertas por defecto</h3>
    <div class="grid g2" style="margin-top:12px">${KINDS.map(card).join("")}</div>
    <div style="margin-top:16px">${welcomeCardHtml()}</div>`;
  bindForm(root);
  mountPlatformAlerts(root);
  if (root.dataset.wired) return;
  root.dataset.wired = "1";
  wireCustomAlerts(root);
  wirePlatformAlerts(root);
  root.addEventListener("click", async (event) => {
    const el = event.target.closest("button");
    if (!el) return;
    if (el.dataset.test) action("simulate", { kind: el.dataset.test });
    if (el.dataset.nosound) { setConfig(`alerts.${el.dataset.nosound}.sound`, "", { immediate: true }); rerender(); }
    if (el.dataset.nomedia) { setConfig(`alerts.${el.dataset.nomedia}.media`, "", { immediate: true }); rerender(); }
  });
  root.addEventListener("change", async (event) => {
    const mediaInput = event.target.closest("[data-upload-media]");
    if (mediaInput?.files[0]) {
      try {
        const result = await uploadSound(mediaInput.files[0], "media");
        setConfig(`alerts.${mediaInput.dataset.uploadMedia}.media`, result.path, { immediate: true });
        toast("GIF / video guardado", "success");
        rerender();
      } catch (error) {
        toast(error.message, "error");
      }
      return;
    }
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
