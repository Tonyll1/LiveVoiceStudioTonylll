import { action, bindForm, esc, getConfig, icon, modal, setConfig, switchHtml, toast, uploadSound, WHO_OPTIONS } from "../core.js";

let root;

const BUILTIN = [
  ["!voz <alias>", "El espectador elige su voz o personaje", "Todos"],
  ["!voces", "Lee cómo usar !voz", "Todos"],
  ["!puntos", "Dice cuántos puntos tienes", "Todos"],
  ["!top", "Lee el top 3 de puntos", "Todos"],
  ["!dado", "Lanza un dado", "Todos"],
  ["!moneda", "Cara o cruz", "Todos"],
  ["!bola <pregunta>", "Bola mágica 8", "Todos"],
  ["!amor <nombre>", "Porcentaje de amor", "Todos"],
  ["!clip", "Guarda un clip en OBS (configurable)", "Mods"],
  ["!skip", "Salta el mensaje que se está leyendo", "Mods"],
  ["!mute", "Silencia / activa la voz", "Mods"],
];
const PERMISSIONS = [...WHO_OPTIONS.filter(([id]) => id !== "gifters"), ["allowlist", "Solo usuarios de una lista"]];

function list() {
  const commands = getConfig("commands", []);
  if (!commands.length) return `<div class="empty">${icon("terminal")}Aún no tienes comandos. Crea uno como <b>!susto</b> que reproduzca un grito, o <b>!redes</b> que lea tus redes.</div>`;
  return `<table class="table"><thead><tr><th>Comando</th><th>Hace</th><th>Quién</th><th>Espera</th><th>Activo</th><th></th></tr></thead><tbody>
    ${commands.map((c, i) => `<tr>
      <td><b class="mono">${esc(c.name)}</b></td>
      <td class="small">${c.media ? "🖼️ " : ""}${c.sound ? `🔊 ${esc(c.sound.split(/[\\/]/).pop())}` : ""}${c.sound && c.text ? "<br>" : ""}${c.text ? `🗣️ ${esc(c.text.slice(0, 60))}` : ""}</td>
      <td class="small">${esc((PERMISSIONS.find(([id]) => id === c.permission) || ["", "Todos"])[1])}</td>
      <td class="small">${c.cooldown || 0}s</td>
      <td><label class="switch"><input type="checkbox" data-toggle="${i}" ${c.enabled !== false ? "checked" : ""}><i></i></label></td>
      <td style="text-align:right;white-space:nowrap">
        ${c.sound ? `<button class="btn sm ghost icon" data-play="${i}" title="Probar sonido">${icon("play")}</button>` : ""}
        <button class="btn sm ghost icon" data-edit="${i}">${icon("edit")}</button>
        <button class="btn sm ghost icon" data-delete="${i}">${icon("trash")}</button></td></tr>`).join("")}
    </tbody></table>`;
}

function editor(index) {
  const commands = getConfig("commands", []);
  const c = index === undefined ? { name: "!", sound: "", text: "", permission: "everyone", cooldown: 30, global_cooldown: 0, volume: 100, allowed_users: [], enabled: true } : { ...commands[index] };
  const box = modal({
    title: index === undefined ? "Nuevo comando" : `Editar ${c.name}`,
    body: `
      <label class="field"><span>Comando</span><input class="input mono" id="c-name" value="${esc(c.name)}" placeholder="!susto"></label>
      <div class="field"><span>Sonido (opcional)</span>
        <div class="row nowrap"><input class="input" id="c-sound" value="${esc(c.sound)}" placeholder="Sube un MP3, WAV u OGG">
        <label class="btn">${icon("upload")}Subir<input type="file" accept=".mp3,.wav,.ogg" hidden id="c-file"></label></div></div>
      <div class="field"><span>GIF, imagen o video en el overlay “Comandos” (opcional)</span>
        <div class="row nowrap"><input class="input" id="c-media" value="${esc(c.media || "")}" placeholder="PNG, JPG, GIF, WEBP, MP4 o WEBM">
        <label class="btn">${icon("upload")}Subir<input type="file" accept=".png,.jpg,.jpeg,.gif,.webp,.mp4,.webm" hidden id="c-media-file"></label></div></div>
      <label class="field"><span>Frase que dice la voz (opcional)</span><input class="input" id="c-text" value="${esc(c.text)}" placeholder="Ej: Sígueme en Instagram arroba tunombre">
        <small>Variables: {user} quien lo usa, {target} lo que escribe después, {points} sus puntos.</small></label>
      <div class="grid g2">
        <label class="field"><span>Quién puede usarlo</span><select class="input" id="c-perm">${PERMISSIONS.map(([id, l]) => `<option value="${id}" ${id === c.permission ? "selected" : ""}>${l}</option>`).join("")}</select></label>
        <label class="field"><span>Volumen del sonido</span><input class="input" type="number" min="0" max="100" id="c-vol" value="${c.volume ?? 100}"></label>
        <label class="field"><span>Espera por persona (s)</span><input class="input" type="number" min="0" id="c-cd" value="${c.cooldown ?? 30}"></label>
        <label class="field"><span>Espera global (s)</span><input class="input" type="number" min="0" id="c-gcd" value="${c.global_cooldown ?? 0}"><small>Para que no lo spameen entre varios.</small></label>
      </div>
      <label class="field" id="c-allow-box"><span>Usuarios permitidos (separados por coma)</span><input class="input" id="c-allow" value="${esc((c.allowed_users || []).join(", "))}"></label>`,
    onSave: (modalEl) => {
      const q = (id) => modalEl.querySelector(id);
      let name = q("#c-name").value.trim().toLowerCase().split(" ")[0];
      if (!name.startsWith("!")) name = `!${name}`;
      if (name === "!") throw new Error("Escribe un nombre para el comando.");
      const updated = {
        name, sound: q("#c-sound").value.trim(), media: q("#c-media").value.trim(), text: q("#c-text").value.trim(), permission: q("#c-perm").value,
        cooldown: Number(q("#c-cd").value) || 0, global_cooldown: Number(q("#c-gcd").value) || 0,
        volume: Number(q("#c-vol").value) || 100,
        allowed_users: q("#c-allow").value.split(",").map((u) => u.trim().toLowerCase().replace(/^@/, "")).filter(Boolean),
        enabled: c.enabled !== false,
      };
      if (!updated.sound && !updated.text && !updated.media) throw new Error("El comando necesita un sonido, un GIF o una frase.");
      const next = [...commands];
      if (next.some((other, i) => other.name === name && i !== index)) throw new Error(`Ya existe ${name}.`);
      if (index === undefined) next.push(updated); else next[index] = updated;
      setConfig("commands", next, { immediate: true });
      refresh();
    },
  });
  const allowBox = box.querySelector("#c-allow-box");
  const syncAllow = () => (allowBox.style.display = box.querySelector("#c-perm").value === "allowlist" ? "" : "none");
  syncAllow();
  box.querySelector("#c-perm").onchange = syncAllow;
  box.querySelector("#c-media-file").onchange = async (event) => {
    try {
      box.querySelector("#c-media").value = (await uploadSound(event.target.files[0], "media")).path;
      toast("GIF / video subido", "success");
    } catch (error) {
      toast(error.message, "error");
    }
  };
  box.querySelector("#c-file").onchange = async (event) => {
    try {
      const result = await uploadSound(event.target.files[0], "commands");
      box.querySelector("#c-sound").value = result.path;
      const name = box.querySelector("#c-name");
      if (name.value.trim() === "!") name.value = `!${result.name.split("-")[0].toLowerCase().replace(/[^a-z0-9ñ]/g, "")}`;
      toast("Sonido subido", "success");
    } catch (error) {
      toast(error.message, "error");
    }
  };
}

function refresh() {
  root.querySelector("#cmd-list").innerHTML = list();
}

function render(target) {
  root = target;
  root.innerHTML = `
    <div class="page-head"><div><h1>Comandos</h1><p>Sonidos y frases que el chat activa escribiendo un comando. Funcionan en todas las plataformas a la vez.</p></div>
      <button class="btn primary" id="new">${icon("plus")}Nuevo comando</button></div>
    <div class="card flush"><div class="card-head"><h2>${icon("terminal")}Tus comandos</h2></div><div id="cmd-list" style="padding:6px 8px">${list()}</div></div>
    <div class="grid g2" style="margin-top:16px">
      <div class="card">
        <h2>${icon("dice")}Juegos y comandos integrados</h2>
        <p class="sub">Interacción fácil que anima a escribir en el chat.</p>
        <div class="grid g2">
          ${switchHtml("games.enabled", "Juegos activados")}
          ${switchHtml("games.dice", "!dado")}${switchHtml("games.coin", "!moneda")}
          ${switchHtml("games.eightball", "!bola")}${switchHtml("games.love", "!amor")}
          ${switchHtml("games.points_command", "!puntos")}${switchHtml("games.top_command", "!top")}
        </div>
        <label class="field" style="margin-top:12px"><span>Espera entre juegos por persona (s)</span><input class="input" type="number" min="0" data-bind="games.cooldown"></label>
      </div>
      <div class="card flush"><div class="card-head"><h2>${icon("book")}Referencia</h2></div>
        <table class="table"><tbody>${BUILTIN.map(([cmd, desc, who]) => `<tr><td class="mono">${esc(cmd)}</td><td class="small muted">${desc}</td><td class="small">${who}</td></tr>`).join("")}</tbody></table>
      </div>
    </div>`;
  bindForm(root);
  root.querySelector("#new").onclick = () => editor();
  root.addEventListener("click", (event) => {
    const el = event.target.closest("button");
    if (!el) return;
    const commands = getConfig("commands", []);
    if (el.dataset.edit) editor(Number(el.dataset.edit));
    if (el.dataset.play) action("test_effect", { path: commands[el.dataset.play].sound, volume: commands[el.dataset.play].volume ?? 100 });
    if (el.dataset.delete && confirm(`¿Borrar ${commands[el.dataset.delete].name}?`)) {
      setConfig("commands", commands.filter((_, i) => i !== Number(el.dataset.delete)), { immediate: true });
      refresh();
    }
  });
  root.addEventListener("change", (event) => {
    const toggle = event.target.closest("[data-toggle]");
    if (!toggle) return;
    const commands = getConfig("commands", []).map((c, i) => (i === Number(toggle.dataset.toggle) ? { ...c, enabled: toggle.checked } : c));
    setConfig("commands", commands, { immediate: true });
  });
}

export default { id: "commands", label: "Comandos", icon: "terminal", render };
