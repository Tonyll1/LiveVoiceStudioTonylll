import { action, api, bindForm, esc, fmt, getConfig, icon, pfBadge, setConfig, store, switchHtml, toast, WHO_OPTIONS } from "../core.js";

let root;
const GOALS = [["likes", "❤️ Likes"], ["followers", "➕ Seguidores"], ["gifts", "🎁 Regalos (valor)"], ["subs", "⭐ Subs"]];

function giveawayHtml() {
  const g = store.state.giveaway;
  return `
    <div class="row"><h2 style="margin:0">${icon("gift")}Sorteo</h2><span class="spacer"></span>
      <span class="pill ${g.active ? "connected" : ""}">${g.active ? "Abierto" : g.winner ? "Terminado" : "Cerrado"}</span></div>
    <p class="sub" style="margin-top:4px">Los espectadores entran escribiendo la palabra clave. Ideal para retener gente hasta el final.</p>
    ${g.active || g.winner ? "" : `
      <div class="grid g2">
        <label class="field"><span>Palabra clave</span><input class="input mono" id="gw-key" value="${esc(g.keyword || "!sorteo")}"></label>
        <label class="field"><span>Premio</span><input class="input" id="gw-prize" value="${esc(g.prize)}" placeholder="Ej: una camiseta"></label>
      </div>
      <label class="field" style="margin-top:10px"><span>Pueden participar</span><select class="input" id="gw-who">${WHO_OPTIONS.filter(([id]) => id !== "gifters").map(([id, l]) => `<option value="${id}">${l}</option>`).join("")}</select></label>`}
    <div class="row" style="margin:14px 0">
      <div class="stat" style="flex:1"><div class="ic">${icon("users")}</div><div><b>${fmt(g.count)}</b><span>Participantes</span></div></div>
      ${g.winner ? `<div class="stat" style="flex:2;border-color:rgba(245,158,11,.5)"><div class="ic">${icon("trophy")}</div><div><b>${esc(g.winner.name)}</b><span>Ganador · ${esc(g.winner.platform)}</span></div></div>` : ""}
    </div>
    <div class="row">
      ${!g.active && !g.winner ? `<button class="btn primary" data-gw="start">${icon("play")}Abrir sorteo</button>` : ""}
      ${g.active ? `<button class="btn" data-gw="stop">${icon("pause")}Cerrar entradas</button>` : ""}
      ${g.count ? `<button class="btn primary" data-gw="draw">${icon("trophy")}${g.winner ? "Sortear otra vez" : "Elegir ganador"}</button>` : ""}
      ${g.active || g.winner || g.count ? `<button class="btn ghost" data-gw="reset">${icon("refresh")}Reiniciar</button>` : ""}
    </div>
    ${g.entrants?.length ? `<div class="chips" style="margin-top:12px;max-height:120px;overflow:auto">${g.entrants.map((e) => `<span class="chip" style="padding-right:10px">${pfBadge(e.platform, true)} ${esc(e.name)}</span>`).join("")}</div>` : ""}`;
}

function pollHtml() {
  const p = store.state.poll;
  return `
    <div class="row"><h2 style="margin:0">${icon("chart")}Encuesta</h2><span class="spacer"></span>
      ${p.active ? `<span class="pill connected">${p.remaining}s</span>` : ""}</div>
    <p class="sub" style="margin-top:4px">El chat vota escribiendo el número de la opción. Funciona en todas las plataformas a la vez.</p>
    ${p.active || p.results.length ? `
      <div style="margin-bottom:10px"><b>${esc(p.question)}</b> <span class="faint small">· ${p.total} votos</span></div>
      <div class="stack">${p.results.map((r, i) => `<div><div class="row small"><span><b>${i + 1}.</b> ${esc(r.option)}</span><span class="spacer"></span><span>${r.votes} · ${r.percent}%</span></div>
        <div class="bar"><i style="width:${r.percent}%"></i></div></div>`).join("")}</div>` : ""}
    ${p.active ? "" : `
      <div class="stack" style="margin-top:12px">
        <input class="input" id="poll-q" placeholder="Pregunta: ¿Qué juego jugamos después?">
        <textarea class="input" id="poll-o" placeholder="Una opción por línea (2 a 6)&#10;Minecraft&#10;Fortnite"></textarea>
        <label class="field"><span>Duración (segundos)</span><input class="input" type="number" id="poll-d" value="60" min="10"></label>
      </div>`}
    <div class="row" style="margin-top:12px">
      ${p.active ? `<button class="btn" data-poll="finish">${icon("check")}Terminar ya</button>` : `<button class="btn primary" data-poll="start">${icon("play")}Lanzar encuesta</button>`}
    </div>`;
}

function goalsHtml() {
  const goals = store.state.goals;
  return GOALS.map(([key, label]) => {
    const g = goals[key] || {};
    const percent = Math.min(100, Math.round(((g.current || 0) * 100) / (g.target || 1)));
    return `
      <div class="stack" style="padding:12px;border:1px solid var(--line);border-radius:12px;background:var(--bg-2)">
        <div class="row">${switchHtml(`goals.${key}.enabled`, `<b>${label}</b>`)}<span class="spacer"></span>
          <span class="small"><b>${fmt(g.current)}</b> / ${fmt(g.target)}</span>
          <button class="btn sm ghost icon" data-goal-reset="${key}" title="Reiniciar progreso">${icon("refresh")}</button></div>
        <div class="bar"><i style="width:${percent}%"></i></div>
        <div class="grid g2"><input class="input" data-bind="goals.${key}.title" placeholder="Título"><input class="input" type="number" min="1" data-bind="goals.${key}.target" placeholder="Objetivo"></div>
      </div>`;
  }).join("");
}

function timersHtml() {
  const timers = getConfig("timers", []);
  return timers.map((t, i) => `
    <div class="stack" style="padding:12px;border:1px solid var(--line);border-radius:12px;background:var(--bg-2)">
      <div class="row">${switchHtml(`timers.${i}.enabled`, "Activo")}<span class="spacer"></span><button class="btn sm ghost icon" data-timer-del="${i}">${icon("trash")}</button></div>
      <textarea class="input" data-timer="${i}" data-field="text" rows="2">${esc(t.text)}</textarea>
      <div class="grid g2">
        <label class="field"><span>Cada (minutos)</span><input class="input" type="number" min="1" data-timer="${i}" data-field="interval_minutes" value="${t.interval_minutes}"></label>
        <label class="field"><span>Mín. mensajes en el chat</span><input class="input" type="number" min="0" data-timer="${i}" data-field="min_messages" value="${t.min_messages}"></label>
      </div>
    </div>`).join("") || '<div class="faint small">Sin mensajes automáticos.</div>';
}

async function leaderboardHtml() {
  const top = await api("leaderboard");
  return top.length ? `<table class="table"><tbody>${top.map((v, i) => `<tr><td style="width:30px"><b>${i + 1}</b></td><td>${pfBadge(v.platform, true)} ${esc(v.name)}</td>
    <td style="text-align:right"><b>${fmt(v.points)}</b> <span class="faint small">${esc(getConfig("points.name"))}</span></td></tr>`).join("")}</tbody></table>`
    : '<div class="faint small">Todavía nadie tiene puntos.</div>';
}

function render(target) {
  root = target;
  root.innerHTML = `
    <div class="page-head"><div><h1>Dinámicas</h1><p>Sorteos, encuestas, metas y puntos: razones para que la gente se quede, escriba y vuelva.</p></div></div>
    <div class="grid g2">
      <div class="card" id="giveaway">${giveawayHtml()}</div>
      <div class="card" id="poll">${pollHtml()}</div>
    </div>
    <div class="grid g2" style="margin-top:16px">
      <div class="card"><h2>${icon("target")}Metas del directo</h2><p class="sub">Se muestran en el overlay <b>Meta</b>. Al cumplirse, la voz lo celebra.</p><div class="stack" id="goals">${goalsHtml()}</div></div>
      <div class="stack">
        <div class="card"><div class="row"><h2 style="margin:0">${icon("clock")}Mensajes automáticos</h2><span class="spacer"></span><button class="btn sm" id="timer-add">${icon("plus")}Añadir</button></div>
          <p class="sub" style="margin-top:4px">Recordatorios leídos en voz (sígueme, comparte, redes…). Solo suenan si hubo actividad en el chat.</p>
          <div class="stack" id="timers">${timersHtml()}</div></div>
        <div class="card">
          <h2>${icon("trophy")}Puntos de fidelidad</h2>
          <p class="sub">Se ganan participando. Los espectadores los consultan con <code>!puntos</code> y <code>!top</code>.</p>
          <div class="grid g2">
            ${switchHtml("points.enabled", "Activados")}
            <label class="field"><span>Nombre</span><input class="input" data-bind="points.name"></label>
            <label class="field"><span>Por mensaje</span><input class="input" type="number" data-bind="points.per_message"></label>
            <label class="field"><span>Por follow</span><input class="input" type="number" data-bind="points.per_follow"></label>
            <label class="field"><span>Por compartir</span><input class="input" type="number" data-bind="points.per_share"></label>
            <label class="field"><span>Por moneda regalada</span><input class="input" type="number" data-bind="points.per_gift_coin"></label>
          </div>
          <div class="divider" style="margin:14px 0"></div>
          <div id="leaderboard" class="small faint">Cargando ranking…</div>
        </div>
      </div>
    </div>`;
  bindForm(root);
  leaderboardHtml().then((html) => { const el = root.querySelector("#leaderboard"); if (el) { el.className = ""; el.innerHTML = html; } });
  root.addEventListener("click", onClick);
  root.addEventListener("input", onTimerInput);
}

function onTimerInput(event) {
  const el = event.target.closest("[data-timer]");
  if (!el) return;
  const timers = getConfig("timers", []).map((t) => ({ ...t }));
  const value = el.type === "number" ? Number(el.value) : el.value;
  timers[Number(el.dataset.timer)][el.dataset.field] = value;
  setConfig("timers", timers);
}

async function onClick(event) {
  const el = event.target.closest("button");
  if (!el) return;
  if (el.dataset.gw === "start") {
    await action("giveaway_start", { keyword: root.querySelector("#gw-key").value, prize: root.querySelector("#gw-prize").value, who: root.querySelector("#gw-who").value });
  } else if (el.dataset.gw) {
    if (el.dataset.gw === "reset" && !confirm("¿Reiniciar el sorteo y borrar participantes?")) return;
    await action(`giveaway_${el.dataset.gw}`);
  } else if (el.dataset.poll === "start") {
    const options = root.querySelector("#poll-o").value.split("\n").map((o) => o.trim()).filter(Boolean);
    const result = await action("poll_start", { question: root.querySelector("#poll-q").value, options, duration: Number(root.querySelector("#poll-d").value) });
    if (result.ok === false) return;
  } else if (el.dataset.poll === "finish") {
    await action("poll_finish");
  } else if (el.dataset.goalReset) {
    await action("goal_reset", { goal: el.dataset.goalReset });
  } else if (el.id === "timer-add") {
    setConfig("timers", [...getConfig("timers", []), { enabled: true, text: "", interval_minutes: 10, min_messages: 5 }], { immediate: true });
    root.querySelector("#timers").innerHTML = timersHtml();
    bindForm(root.querySelector("#timers"));
  } else if (el.dataset.timerDel) {
    setConfig("timers", getConfig("timers", []).filter((_, i) => i !== Number(el.dataset.timerDel)), { immediate: true });
    root.querySelector("#timers").innerHTML = timersHtml();
    bindForm(root.querySelector("#timers"));
  }
}

function onEvent(type) {
  if (!root?.isConnected) return;
  const typing = document.activeElement && root.contains(document.activeElement) && document.activeElement.matches("input,textarea,select");
  if (type === "giveaway" && !(typing && document.activeElement.closest("#giveaway"))) root.querySelector("#giveaway").innerHTML = giveawayHtml();
  if (type === "poll" && !(typing && document.activeElement.closest("#poll"))) root.querySelector("#poll").innerHTML = pollHtml();
  if (type === "goals" && !(typing && document.activeElement.closest("#goals"))) {
    root.querySelector("#goals").innerHTML = goalsHtml();
    bindForm(root.querySelector("#goals"));
  }
}

export default { id: "dynamics", label: "Dinámicas", icon: "sparkles", render, onEvent };
