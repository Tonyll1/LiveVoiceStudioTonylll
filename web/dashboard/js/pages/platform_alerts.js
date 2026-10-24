import { action, esc, fmt, getConfig, icon, pfBadge, setConfig, toast, PLATFORM_LABEL } from "../core.js";
import { openAlertEditor } from "./custom_alerts.js";

// Variantes que cada plataforma puede enviar. Cada una se guarda como una alerta propia con "preset".
const VARIANTS = {
  tiktok: [
    { label: "Follow", trigger: "follow", hint: "Nuevo seguidor" },
    { label: "Compartir", trigger: "share", hint: "Alguien compartió el directo" },
    { label: "Super fan", trigger: "sub", match: "Super fan", hint: "Suscripción de TikTok" },
    { label: "Regalos pequeños", trigger: "gift", min: 1, max: 99, hint: "1–99 💎 (si no tienen alerta propia)" },
    { label: "Regalos medianos", trigger: "gift", min: 100, max: 999, hint: "100–999 💎" },
    { label: "Regalos grandes", trigger: "gift", min: 1000, hint: "1000+ 💎" },
  ],
  twitch: [
    { label: "Sub Tier 1", trigger: "sub", match: "Tier 1" },
    { label: "Sub Tier 2", trigger: "sub", match: "Tier 2" },
    { label: "Sub Tier 3", trigger: "sub", match: "Tier 3" },
    { label: "Sub Prime", trigger: "sub", match: "Prime" },
    { label: "Sub regalada", trigger: "sub", match: "Sub regalada", hint: "Alguien regala una sub" },
    { label: "Subs regaladas en masa", trigger: "gift", match: "Subs regaladas", hint: "Varias subs de golpe" },
    { label: "Bits pequeños", trigger: "bits", min: 1, max: 99, hint: "1–99 bits" },
    { label: "Bits medianos", trigger: "bits", min: 100, max: 999, hint: "100–999 bits" },
    { label: "Bits grandes", trigger: "bits", min: 1000, max: 4999, hint: "1000–4999 bits" },
    { label: "Bits épicos", trigger: "bits", min: 5000, hint: "5000+ bits" },
    { label: "Raid pequeño", trigger: "raid", min: 1, max: 9, hint: "Menos de 10 personas" },
    { label: "Raid grande", trigger: "raid", min: 10, hint: "10 personas o más" },
  ],
  kick: [
    { label: "Suscripción", trigger: "sub", match: "Sub" },
    { label: "Subs regaladas", trigger: "gift", match: "Subs regaladas" },
    { label: "Cualquier Kick", trigger: "gift", hint: "Si ese Kick no tiene alerta propia" },
    { label: "Host / raid", trigger: "raid" },
  ],
  youtube: [
    { label: "Super Chat pequeño", trigger: "gift", match: "Super Chat", min: 1, max: 4, hint: "1–4 (tu moneda)" },
    { label: "Super Chat mediano", trigger: "gift", match: "Super Chat", min: 5, max: 19, hint: "5–19" },
    { label: "Super Chat grande", trigger: "gift", match: "Super Chat", min: 20, max: 99, hint: "20–99" },
    { label: "Super Chat épico", trigger: "gift", match: "Super Chat", min: 100, hint: "100 o más" },
    { label: "Super Sticker", trigger: "gift", match: "Super Sticker" },
    { label: "Nuevo miembro", trigger: "sub", match: "Miembro" },
    { label: "Membresías regaladas", trigger: "gift", match: "Membresías regaladas" },
  ],
};

let root, platform = "tiktok", gifts = [], search = "";

function presetKey(platformId, variant) {
  return [platformId, variant.trigger, variant.match || "", variant.min || 0, variant.max || 0].join("|");
}

function findRule(key) {
  const rules = getConfig("custom_alerts", []);
  const index = rules.findIndex((rule) => rule.preset === key);
  return { index, rule: rules[index] };
}

function status(rule) {
  if (!rule) return '<span class="faint small">Alerta normal</span>';
  const parts = [rule.sound ? "🔊" : "", rule.media ? (rule.media_type === "video" ? "🎬" : "🖼️") : "", rule.tts_text ? "🗣️" : ""].join(" ");
  return `<span class="small">${parts || "—"}</span>${rule.enabled === false ? ' <span class="tag">apagada</span>' : ""}`;
}

function variantRow(variant) {
  const key = presetKey(platform, variant);
  const { rule } = findRule(key);
  return `<tr>
    <td><b>${esc(variant.label)}</b>${variant.hint ? `<div class="small muted">${esc(variant.hint)}</div>` : ""}</td>
    <td>${status(rule)}</td>
    <td style="text-align:right;white-space:nowrap">
      ${rule ? `<button class="btn sm" data-pa-test="${esc(key)}">${icon("play")}</button>` : ""}
      <button class="btn sm ${rule ? "" : "primary"}" data-pa-edit="${esc(key)}">${icon(rule ? "edit" : "plus")}${rule ? "Editar" : "Personalizar"}</button>
      ${rule ? `<button class="btn sm ghost icon" data-pa-del="${esc(key)}" title="Volver a la alerta normal">${icon("trash")}</button>` : ""}
    </td></tr>`;
}

function giftKey(name) {
  return [platform, "gift", name, 0, 0].join("|");
}

function giftsHtml() {
  if (!["tiktok", "kick"].includes(platform)) return "";
  const q = search.trim().toLowerCase();
  const list = gifts.filter((gift) => !q || gift.name.toLowerCase().includes(q));
  const configured = new Set(getConfig("custom_alerts", []).filter((rule) => rule.preset?.startsWith(`${platform}|gift|`)).map((rule) => rule.match));
  return `
    <div class="row" style="margin:16px 0 8px"><b>${platform === "tiktok" ? "Regalos de TikTok" : "Kicks recibidos"}</b>
      <span class="faint small">${platform === "tiktok" ? `${list.length} regalos · los que ya recibiste salen primero` : "Aparecen aquí cuando te los envían en directo"}</span>
      <span class="spacer"></span>
      <input class="input" id="pa-search" placeholder="Buscar regalo (Rose, Galaxy, Lion…)" value="${esc(search)}" style="max-width:260px">
      ${platform === "tiktok" ? `<button class="btn sm ghost" id="pa-refresh" title="Volver a descargar el catálogo">${icon("refresh")}</button>` : ""}</div>
    ${list.length ? `<div class="presets" style="grid-template-columns:repeat(auto-fill,minmax(112px,1fr));max-height:420px;overflow:auto">${list.slice(0, 240).map((gift) => `
      <div class="preset" data-pa-gift="${esc(gift.name)}" title="${esc(gift.name)}" style="${configured.has(gift.name) ? "border-color:var(--accent);background:var(--accent-soft)" : ""}">
        ${gift.image ? `<img src="${esc(gift.image)}" referrerpolicy="no-referrer" loading="lazy" style="width:44px;height:44px;object-fit:contain">` : '<div class="e">🎁</div>'}
        <b style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(gift.name)}</b>
        <small>${gift.value ? `${fmt(gift.value)} 💎` : ""}${gift.seen ? " · recibido" : ""}${configured.has(gift.name) ? " · ✓" : ""}</small>
      </div>`).join("")}</div>`
      : `<div class="faint small">${platform === "tiktok" ? "Cargando catálogo…" : "Todavía no has recibido Kicks. Mientras tanto usa “Cualquier Kick”."}</div>`}`;
}

export function platformAlertsHtml() {
  return `
    <div class="card" id="platform-alerts">
      <div class="row"><h2 style="margin:0">${icon("layers")}Alertas por plataforma</h2><span class="spacer"></span>
        <div class="seg" id="pa-tabs">${Object.keys(VARIANTS).map((id) => `<button data-pa-tab="${id}" class="${id === platform ? "active" : ""}">${PLATFORM_LABEL[id]}</button>`).join("")}</div></div>
      <p class="sub" style="margin-top:6px">Cada plataforma tiene sus propias acciones. Ponle a cada una (o a cada regalo) su GIF, sonido, frase y voz.
        Si un evento encaja en varias, gana la más concreta (un regalo exacto antes que un rango). Lo que no personalices usa la alerta normal de abajo.</p>
      <div id="pa-body"></div>
    </div>`;
}

function renderBody() {
  const body = root?.querySelector("#pa-body");
  if (!body) return;
  body.innerHTML = `
    <div class="row" style="margin-bottom:6px">${pfBadge(platform)}<b>${PLATFORM_LABEL[platform]}</b></div>
    <table class="table"><tbody>${VARIANTS[platform].map(variantRow).join("")}</tbody></table>
    ${giftsHtml()}`;
  const input = body.querySelector("#pa-search");
  if (input) {
    input.oninput = () => {
      search = input.value;
      const position = input.selectionStart;
      renderBody();
      const again = root.querySelector("#pa-search");
      again.focus();
      again.setSelectionRange(position, position);
    };
  }
}

async function loadGifts(refresh = false) {
  gifts = [];
  if (!["tiktok", "kick"].includes(platform)) return renderBody();
  renderBody();
  const result = await action("gift_catalog", { platform, refresh });
  gifts = result.gifts || [];
  renderBody();
}

function edit(key, preset) {
  const { index } = findRule(key);
  openAlertEditor(index >= 0 ? index : undefined, preset, renderBody);
}

function variantPreset(variant) {
  return {
    preset: presetKey(platform, variant),
    name: `${PLATFORM_LABEL[platform]} · ${variant.label}`,
    trigger: variant.trigger,
    match: variant.match || "",
    match_mode: variant.match ? "exact" : "",
    min_amount: variant.min || 0,
    max_amount: variant.max || 0,
    platforms: [platform],
    title: variant.label,
    text: variant.trigger === "gift" || variant.trigger === "bits" ? "{user} envió {amount} {gift}" : "{user}",
  };
}

// Se llama en cada render de la página Alertas (la sección se vuelve a pintar).
export function mountPlatformAlerts(target) {
  root = target;
  if (gifts.length) renderBody();
  else loadGifts();
}

// Se llama una sola vez: escucha los clics de la sección.
export function wirePlatformAlerts(target) {
  root = target;
  root.addEventListener("click", async (event) => {
    const el = event.target.closest("[data-pa-tab],[data-pa-edit],[data-pa-del],[data-pa-test],[data-pa-gift],#pa-refresh");
    if (!el || !root.querySelector("#platform-alerts")?.contains(el)) return;
    if (el.dataset.paTab) {
      platform = el.dataset.paTab;
      search = "";
      root.querySelectorAll("[data-pa-tab]").forEach((b) => b.classList.toggle("active", b === el));
      loadGifts();
    } else if (el.id === "pa-refresh") {
      toast("Descargando el catálogo de regalos de TikTok…");
      loadGifts(true);
    } else if (el.dataset.paEdit) {
      const variant = VARIANTS[platform].find((item) => presetKey(platform, item) === el.dataset.paEdit);
      edit(el.dataset.paEdit, variantPreset(variant));
    } else if (el.dataset.paGift) {
      const gift = gifts.find((item) => item.name === el.dataset.paGift);
      edit(giftKey(gift.name), {
        preset: giftKey(gift.name),
        name: `${PLATFORM_LABEL[platform]} · ${gift.name}`,
        trigger: "gift",
        match: gift.name,
        match_mode: "exact",
        platforms: [platform],
        gift_image: gift.image || "",
        title: gift.name,
        text: "{user} envió {amount} {gift}",
      });
    } else if (el.dataset.paTest) {
      const { rule } = findRule(el.dataset.paTest);
      if (rule) action("custom_alert_test", { id: rule.id });
    } else if (el.dataset.paDel) {
      const { rule } = findRule(el.dataset.paDel);
      if (rule && confirm(`¿Quitar la personalización de “${rule.name}”? Volverá a usar la alerta normal.`)) {
        setConfig("custom_alerts", getConfig("custom_alerts", []).filter((item) => item !== rule), { immediate: true });
        renderBody();
      }
    }
  });
}
