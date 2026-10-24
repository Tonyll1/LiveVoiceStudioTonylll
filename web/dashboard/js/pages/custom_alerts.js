import { action, esc, getConfig, icon, modal, setConfig, store, toast, uploadSound, PLATFORM_LABEL } from "../core.js";

const TRIGGERS = [
  ["gift", "🎁 Regalo"], ["follow", "💜 Follow"], ["sub", "⭐ Suscripción"], ["bits", "💎 Bits"],
  ["raid", "🚀 Raid"], ["share", "🔁 Compartir"], ["like", "❤️ Likes"], ["chat", "💬 Palabra en el chat"],
];
const TRIGGER_LABEL = Object.fromEntries(TRIGGERS);

const EXAMPLES = [
  { name: "Galaxia épica", trigger: "gift", match: "galaxia", tts_text: "¡{user} lanzó una galaxia! Esto es increíble.", text: "¡{user} lanzó una GALAXIA!" },
  { name: "Risa del chat", trigger: "chat", match: "jajaja", cooldown: 30, overlay: false },
  { name: "Raid grande", trigger: "raid", min_amount: 20, tts_text: "¡Alerta de raid! {user} llega con {amount} personas.", text: "RAID de {user} ({amount})" },
];

let root;

function rules() {
  return getConfig("custom_alerts", []);
}

function describe(rule) {
  const parts = [TRIGGER_LABEL[rule.trigger] || rule.trigger];
  if (rule.match) parts.push(rule.trigger === "chat" ? `contiene “${esc(rule.match)}”` : `“${esc(rule.match)}”`);
  if (rule.min_amount) parts.push(`mínimo ${rule.min_amount}`);
  if (rule.platforms?.length) parts.push(rule.platforms.map((p) => PLATFORM_LABEL[p]).join(", "));
  return parts.join(" · ");
}

export function customAlertsHtml() {
  const list = rules().map((rule, index) => ({ rule, index })).filter(({ rule }) => !rule.preset);
  return `
    <div class="card flush" id="custom-alerts">
      <div class="card-head"><h2>${icon("sparkles")}Tus alertas propias</h2>
        <button class="btn primary sm" data-ca-new>${icon("plus")}Nueva alerta</button></div>
      <div style="padding:10px 14px">
        <p class="sub" style="margin:0 0 10px">Tu sonido, tu imagen/GIF/video y tu frase (con la voz que quieras) para un regalo concreto, un follow, un raid grande o una palabra del chat.
          Si encaja, sustituye a la alerta normal de ese evento.</p>
        ${list.length ? `<table class="table"><tbody>${list.map(({ rule, index: i }) => `<tr>
          <td><label class="switch"><input type="checkbox" data-ca-toggle="${i}" ${rule.enabled !== false ? "checked" : ""}><i></i></label></td>
          <td><b>${esc(rule.name || "Sin nombre")}</b><div class="small muted">${describe(rule)}</div></td>
          <td class="small">${rule.sound ? "🔊" : ""} ${rule.media ? (rule.media_type === "video" ? "🎬" : "🖼️") : ""} ${rule.tts_text ? "🗣️" : ""}</td>
          <td style="text-align:right;white-space:nowrap"><button class="btn sm" data-ca-test="${i}">${icon("play")}Probar</button>
            <button class="btn sm ghost icon" data-ca-edit="${i}">${icon("edit")}</button>
            <button class="btn sm ghost icon" data-ca-del="${i}">${icon("trash")}</button></td></tr>`).join("")}</tbody></table>`
        : `<div class="row small faint">Ideas rápidas:${EXAMPLES.map((ex, i) => `<button class="btn sm" data-ca-example="${i}">${esc(ex.name)}</button>`).join("")}</div>`}
      </div>
    </div>`;
}

function voiceOptions(selected) {
  const groups = [["edge", "Neuronales"], ["kokoro", "IA Kokoro"], ["elevenlabs", "IA ElevenLabs"], ["piper", "Piper"], ["tiktok", "TikTok"], ["sapi", "Windows"]];
  return `<option value="">Voz principal</option>${groups.map(([engine, label]) => {
    const voices = store.voices.filter((v) => v.engine === engine && (engine !== "edge" || v.language === "es" || v.language === "en"));
    return voices.length ? `<optgroup label="${label}">${voices.map((v) => `<option value="${esc(v.id)}" ${v.id === selected ? "selected" : ""}>${esc(v.name)} · ${esc(v.country || v.locale)}</option>`).join("")}</optgroup>` : "";
  }).join("")}`;
}

export function openAlertEditor(index, preset, onSaved) {
  const current = index === undefined ? { enabled: true, trigger: "gift", overlay: true, replace_default: true, volume: 100, duration: 6, cooldown: 0, ...preset } : { ...rules()[index] };
  const box = modal({
    title: index === undefined ? "Nueva alerta propia" : `Editar “${current.name}”`,
    wide: true,
    body: `
      <div class="grid g2">
        <label class="field"><span>Nombre</span><input class="input" id="ca-name" value="${esc(current.name || "")}" placeholder="Ej: Galaxia épica"></label>
        <label class="field"><span>Cuando…</span><select class="input" id="ca-trigger">${TRIGGERS.map(([id, label]) => `<option value="${id}" ${id === current.trigger ? "selected" : ""}>${label}</option>`).join("")}</select></label>
        <label class="field" id="ca-match-box"><span id="ca-match-label">Nombre del regalo (vacío = cualquiera)</span><input class="input" id="ca-match" value="${esc(current.match || "")}"></label>
        <div class="grid g2" id="ca-min-box">
          <label class="field"><span id="ca-min-label">Valor mínimo</span><input class="input" type="number" min="0" id="ca-min" value="${current.min_amount || 0}"></label>
          <label class="field"><span>Máximo (0 = sin límite)</span><input class="input" type="number" min="0" id="ca-max" value="${current.max_amount || 0}"></label>
        </div>
      </div>
      <div class="field"><span>Solo en (vacío = todas)</span><div class="row">${Object.entries(PLATFORM_LABEL).map(([id, label]) =>
        `<label class="switch"><input type="checkbox" data-ca-platform="${id}" ${(current.platforms || []).includes(id) ? "checked" : ""}><i></i><span>${label}</span></label>`).join("")}</div></div>
      <div class="divider"></div>
      <div class="grid g2">
        <div class="field"><span>🔊 Sonido</span>
          <div class="row nowrap"><input class="input" id="ca-sound" value="${esc(current.sound || "")}" placeholder="MP3, WAV u OGG">
          <label class="btn">${icon("upload")}<input type="file" accept=".mp3,.wav,.ogg" hidden id="ca-sound-file"></label></div></div>
        <label class="field"><span>Volumen del sonido</span><input class="input" type="number" min="0" max="100" id="ca-volume" value="${current.volume ?? 100}"></label>
        <div class="field"><span>🖼️ Imagen, GIF o video para el overlay</span>
          <div class="row nowrap"><input class="input" id="ca-media" value="${esc(current.media || "")}" placeholder="PNG, JPG, GIF, WEBP, MP4, WEBM">
          <label class="btn">${icon("upload")}<input type="file" accept=".png,.jpg,.jpeg,.gif,.webp,.mp4,.webm" hidden id="ca-media-file"></label></div>
          <small id="ca-media-preview"></small></div>
        <label class="field"><span>Duración en pantalla (s)</span><input class="input" type="number" min="2" max="60" id="ca-duration" value="${current.duration || 6}"></label>
      </div>
      <div class="divider"></div>
      <div class="grid g2">
        <label class="field"><span>Título en el overlay</span><input class="input" id="ca-title" value="${esc(current.title || "")}" placeholder="Ej: ¡GALAXIA!"></label>
        <label class="field"><span>Texto en el overlay</span><input class="input" id="ca-text" value="${esc(current.text || "")}" placeholder="{user} envió {amount} {gift}"></label>
        <label class="field"><span>🗣️ Frase que dice la voz</span><input class="input" id="ca-tts" value="${esc(current.tts_text || "")}" placeholder="Vacío = no dice nada"></label>
        <label class="field"><span>Con la voz</span><select class="input" id="ca-voice">${voiceOptions(current.voice || "")}</select></label>
      </div>
      <small class="faint">Variables: {user} nombre, {amount} cantidad, {gift} regalo, {message} mensaje del chat.</small>
      <div class="row">
        <label class="switch"><input type="checkbox" id="ca-overlay" ${current.overlay !== false ? "checked" : ""}><i></i><span>Mostrar en el overlay de alertas</span></label>
        <label class="switch"><input type="checkbox" id="ca-replace" ${current.replace_default !== false ? "checked" : ""}><i></i><span>Sustituir la alerta normal</span></label>
        <label class="field" style="width:180px"><span>Espera entre usos (s)</span><input class="input" type="number" min="0" id="ca-cooldown" value="${current.cooldown || 0}"></label>
      </div>`,
    onSave: (modalEl) => {
      const q = (id) => modalEl.querySelector(id);
      const rule = {
        ...current,
        id: current.id || String(Date.now()),
        enabled: current.enabled !== false,
        name: q("#ca-name").value.trim() || "Alerta",
        trigger: q("#ca-trigger").value,
        match: q("#ca-match").value.trim(),
        min_amount: Number(q("#ca-min").value) || 0,
        max_amount: Number(q("#ca-max").value) || 0,
        platforms: [...modalEl.querySelectorAll("[data-ca-platform]:checked")].map((el) => el.dataset.caPlatform),
        sound: q("#ca-sound").value.trim(),
        volume: Number(q("#ca-volume").value) || 100,
        media: q("#ca-media").value.trim(),
        media_type: /\.(mp4|webm)$/i.test(q("#ca-media").value) ? "video" : q("#ca-media").value ? "image" : "",
        duration: Number(q("#ca-duration").value) || 6,
        title: q("#ca-title").value.trim(),
        text: q("#ca-text").value.trim(),
        tts_text: q("#ca-tts").value.trim(),
        voice: q("#ca-voice").value,
        overlay: q("#ca-overlay").checked,
        replace_default: q("#ca-replace").checked,
        cooldown: Number(q("#ca-cooldown").value) || 0,
      };
      if (rule.trigger === "chat" && !rule.match) throw new Error("Escribe la palabra o frase del chat que activa la alerta.");
      if (!rule.sound && !rule.media && !rule.tts_text && !rule.text) throw new Error("Pon al menos un sonido, una imagen o una frase.");
      const next = [...rules()];
      if (index === undefined) next.push(rule); else next[index] = rule;
      setConfig("custom_alerts", next, { immediate: true });
      refresh();
      onSaved?.();
    },
  });

  const trigger = box.querySelector("#ca-trigger");
  const sync = () => {
    const kind = trigger.value;
    box.querySelector("#ca-match-box").style.display = ["gift", "chat", "sub"].includes(kind) ? "" : "none";
    box.querySelector("#ca-match-label").textContent = kind === "chat" ? "Palabra o frase que debe contener el mensaje"
      : kind === "sub" ? "Variante: Tier 1, Tier 2, Tier 3, Prime, Sub regalada, Miembro, Super fan (vacío = todas)"
      : "Nombre del regalo (vacío = cualquiera)";
    box.querySelector("#ca-min-box").style.display = ["gift", "bits", "raid", "like", "sub"].includes(kind) ? "" : "none";
    box.querySelector("#ca-min-label").textContent = { gift: "Valor mínimo (💎)", bits: "Bits mínimos", raid: "Personas mínimas", like: "Likes mínimos de golpe", sub: "Meses mínimos" }[kind] || "Mínimo";
  };
  trigger.onchange = sync;
  sync();

  const preview = () => {
    const value = box.querySelector("#ca-media").value;
    box.querySelector("#ca-media-preview").innerHTML = value ? `Se verá en el overlay: <code>${esc(value.split(/[\\/]/).pop())}</code>` : "";
  };
  preview();
  box.querySelector("#ca-sound-file").onchange = async (event) => {
    try {
      box.querySelector("#ca-sound").value = (await uploadSound(event.target.files[0], "alerts")).path;
      toast("Sonido subido", "success", 1500);
    } catch (error) { toast(error.message, "error"); }
  };
  box.querySelector("#ca-media-file").onchange = async (event) => {
    try {
      box.querySelector("#ca-media").value = (await uploadSound(event.target.files[0], "media")).path;
      preview();
      toast("Archivo subido", "success", 1500);
    } catch (error) { toast(error.message, "error"); }
  };
}

function refresh() {
  const card = root?.querySelector("#custom-alerts");
  if (card) card.outerHTML = customAlertsHtml();
}

export function wireCustomAlerts(target) {
  root = target;
  root.addEventListener("click", async (event) => {
    const el = event.target.closest("[data-ca-new],[data-ca-edit],[data-ca-del],[data-ca-test],[data-ca-example]");
    if (!el) return;
    if (el.dataset.caNew !== undefined) openAlertEditor();
    else if (el.dataset.caExample) openAlertEditor(undefined, EXAMPLES[Number(el.dataset.caExample)]);
    else if (el.dataset.caEdit) openAlertEditor(Number(el.dataset.caEdit));
    else if (el.dataset.caTest) {
      await action("custom_alert_test", { id: rules()[Number(el.dataset.caTest)].id });
      toast("Mira el overlay de Alertas o el Campo de pruebas", "info", 2500);
    } else if (el.dataset.caDel && confirm(`¿Borrar “${rules()[Number(el.dataset.caDel)].name}”?`)) {
      setConfig("custom_alerts", rules().filter((_, i) => i !== Number(el.dataset.caDel)), { immediate: true });
      refresh();
    }
  });
  root.addEventListener("change", (event) => {
    const toggle = event.target.closest("[data-ca-toggle]");
    if (!toggle) return;
    setConfig("custom_alerts", rules().map((rule, i) => (i === Number(toggle.dataset.caToggle) ? { ...rule, enabled: toggle.checked } : rule)), { immediate: true });
  });
}
