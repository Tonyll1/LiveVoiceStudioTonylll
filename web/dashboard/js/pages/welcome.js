import { icon, selectHtml, switchHtml } from "../core.js";

// Tarjeta de bienvenida compartida por las páginas Lectura y Alertas.
export function welcomeCardHtml() {
  return `
    <div class="card" id="welcome-card">
      <h2>${icon("message")}Bienvenida por voz</h2>
      <p class="sub">El “Bienvenido {user}, gracias por pasar.” que se lee cuando alguien escribe. Elige a quién saludar para que no sature el directo.</p>
      <div class="stack">
        <div class="row">${switchHtml("welcome.enabled", "Saludar por voz")}${switchHtml("welcome.tts", "Leerlo en voz alta")}</div>
        <label class="field"><span>¿A quién saludar?</span>
          ${selectHtml("welcome.mode", [
            ["new", "Solo a quien escribe por primera vez en tu canal (recomendado)"],
            ["session", "A todos la primera vez que escriben en cada directo"],
          ])}</label>
        <label class="field"><span>Texto para nuevos</span><input class="input" data-bind="welcome.text"><small>{user} = nombre. Déjalo vacío para no saludar a nuevos.</small></label>
        <label class="field"><span>Texto para los que vuelven (solo en “a todos”)</span><input class="input" data-bind="welcome.text_back" placeholder="Ej: ¡Qué bueno verte otra vez, {user}!"><small>Vacío = no se saluda a los que ya conocías.</small></label>
        <div class="grid g2">
          <label class="field"><span>Espera entre saludos (s)</span><input class="input" type="number" min="0" data-bind="welcome.cooldown"><small>Si entran muchos a la vez, solo saluda a uno cada X segundos.</small></label>
          <label class="field"><span>No saludar si la cola tiene</span><input class="input" type="number" min="1" data-bind="welcome.max_queue"><small>mensajes o más pendientes.</small></label>
        </div>
      </div>
    </div>`;
}
