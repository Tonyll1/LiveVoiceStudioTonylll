import { icon } from "../core.js";

const origin = () => location.origin;

const SECTIONS = {
  start: ["🚀 Primeros pasos", () => `
    <div class="card welcome-hero" style="margin-bottom:18px"><h2 style="font-size:20px">¡Bienvenido a LiveVoice Studio!</h2>
      <p class="muted" style="margin:6px 0 0">La alternativa gratuita para leer tu chat en voz alta, mostrar alertas y hacer dinámicas en TikTok, Twitch, Kick y YouTube a la vez. Sin cuentas, sin suscripciones y sin límites de voces.</p></div>
    <ol class="steps">
      <li><b>Conecta tu canal.</b> Ve a <a href="#" data-go="live">Directo</a>, escribe tu usuario en la tarjeta de tu plataforma y pulsa <b>Conectar</b>. Si todavía no estás en vivo no pasa nada: se queda <i>esperando</i> y se conecta solo cuando empieces.</li>
      <li><b>Elige tu voz.</b> En <a href="#" data-go="voices">Voces</a> busca por país o nombre y pulsa ▶ para escucharlas. Haz clic en una para usarla. Ajusta velocidad y tono.</li>
      <li><b>Prueba sin estar en directo.</b> En Directo usa los <b>eventos de prueba</b> (mensaje, follow, regalo…) para oír cómo queda.</li>
      <li><b>Añade los overlays a OBS.</b> Mira la sección <a href="#" data-section="obs">Overlays en OBS</a>.</li>
      <li><b>Configura tus atajos.</b> Por defecto: <code>Ctrl+Alt+M</code> silenciar, <code>Ctrl+Alt+S</code> saltar, <code>Ctrl+Alt+P</code> pausar, <code>Ctrl+Alt+C</code> vaciar cola, <code>Ctrl+Alt+K</code> clip.</li>
    </ol>
    <div class="callout">💡 Activa <b>Conexión automática</b> en Ajustes: abres LiveVoice Studio antes del directo y te olvidas.</div>`],

  obs: ["🎬 Overlays en OBS", () => `
    <ol class="steps">
      <li>En OBS, en tu escena pulsa <b>+</b> → <b>Navegador</b> (Browser). Ponle un nombre, por ejemplo “LiveVoice Alertas”.</li>
      <li>En <b>URL</b> pega la dirección del overlay. Por ejemplo: <code>${origin()}/overlay/alerts</code></li>
      <li>Ancho y alto: los que indica la página <a href="#" data-go="overlays">Overlays</a> (alertas: 1920×1080).</li>
      <li>Marca <b>“Actualizar el navegador cuando la escena se active”</b>. No hace falta CSS personalizado: el fondo ya es transparente.</li>
      <li>Pulsa <b>Probar</b> en la página Overlays para ver la animación en OBS.</li>
    </ol>
    <div class="callout warn">⚠️ LiveVoice Studio tiene que estar abierto mientras transmites: los overlays se sirven desde tu PC.</div>
    <h3>Overlays disponibles</h3>
    <ul>
      <li><code>/overlay/alerts</code> — alertas animadas (follows, regalos, subs, raids, metas).</li>
      <li><code>/overlay/chat</code> — chat unificado de todas las plataformas.</li>
      <li><code>/overlay/tts</code> — subtítulos de lo que está diciendo la voz.</li>
      <li><code>/overlay/goal?goal=likes</code> — barra de meta (<code>likes</code>, <code>followers</code>, <code>gifts</code>, <code>subs</code>).</li>
      <li><code>/overlay/leaderboard</code> — top regaladores (<code>?type=points</code> para puntos).</li>
      <li><code>/overlay/giveaway</code> y <code>/overlay/poll</code> — sorteos y encuestas.</li>
    </ul>`],

  audio: ["🔊 Audio y voz en OBS", () => `
    <h3>Opción simple</h3>
    <p>La voz sale por tus altavoces/auriculares predeterminados. Si OBS captura el “Audio del escritorio”, tus espectadores la oyen.</p>
    <h3>Opción pro: la voz en su propia pista</h3>
    <ol class="steps">
      <li>Instala <b>VB-Audio Virtual Cable</b> (gratis).</li>
      <li>En <a href="#" data-go="settings">Ajustes</a> → Salida de audio, elige <b>CABLE Input</b>.</li>
      <li>En OBS añade <b>Captura de entrada de audio</b> → <b>CABLE Output</b>. Ahora puedes subir/bajar la voz aparte del juego.</li>
      <li>Para oírla tú también: en OBS → Propiedades avanzadas de audio → monitor “Monitorear y salida”.</li>
    </ol>
    <div class="callout">💡 Si la voz tapa el juego, baja el volumen de la voz o usa un filtro “Compresor” con sidechain en OBS.</div>`],

  tiktok: ["TikTok", () => `
    <ol class="steps">
      <li>Escribe tu usuario <b>sin @</b> (ej. <code>mi_usuario</code>).</li>
      <li>Lee: comentarios, regalos (con su valor en diamantes), follows, likes, compartidos, entradas y suscripciones.</li>
      <li>Los regalos en racha se leen <b>una sola vez</b> al terminar la racha (“envió 15 Rosas”).</li>
    </ol>
    <div class="callout warn">Si aparece “rate limit” o “sign”, TikTok está limitando el servidor gratuito de firmas. Espera unos minutos o pon una clave gratuita de eulerstream.com en Ajustes → TikTok avanzado.</div>
    <div class="callout">Los directos con restricción de edad no se pueden leer sin iniciar sesión.</div>`],

  twitch: ["Twitch", () => `
    <ol class="steps">
      <li>Escribe el nombre del canal (ej. <code>mi_canal</code>). No hace falta iniciar sesión.</li>
      <li>Lee: chat, bits, subs (y regaladas), raids. Detecta mods, VIP y subs para los permisos.</li>
    </ol>
    <div class="callout">Los follows de Twitch requieren iniciar sesión con la cuenta del canal (EventSub), por eso no aparecen. Las demás alertas funcionan.</div>`],

  kick: ["Kick", () => `
    <ol class="steps">
      <li>Escribe el nombre del canal tal como aparece en la URL (<code>kick.com/mi-canal</code> → <code>mi-canal</code>).</li>
      <li>Lee: chat, subs, subs regaladas, hosts/raids y Kicks.</li>
    </ol>
    <div class="callout">Kick cambia a veces sus claves internas. LiveVoice las obtiene automáticamente en cada conexión, así que no deberías tener que actualizar nada.</div>`],

  youtube: ["YouTube", () => `
    <ol class="steps">
      <li>Escribe tu <b>@handle</b> (ej. <code>@MiCanal</code>) o pega el enlace del directo.</li>
      <li>Lee: chat, Super Chats (como regalos) y nuevos miembros.</li>
      <li>Si tienes varios directos a la vez, pega el enlace del que quieras.</li>
    </ol>`],

  grow: ["📈 Crecer como streamer pequeño", () => `
    <p>Con pocos espectadores, cada persona cuenta. Estas funciones están pensadas para que quien entra, se quede y vuelva:</p>
    <ul>
      <li><b>Bienvenida automática</b> (Alertas): saluda por su nombre a cada persona que escribe por primera vez. Se sienten vistos.</li>
      <li><b>Voz propia para cada espectador</b> (Voces → aleatoria, o <code>!voz argentino</code>): la gente escribe más solo por oír su voz. Explícalo en pantalla.</li>
      <li><b>Metas de likes</b> (Dinámicas + overlay Meta): en TikTok los likes empujan el directo en el algoritmo. Pon metas pequeñas y alcanzables (500, 1000…).</li>
      <li><b>Sorteos</b>: anúncialo al principio y sortea al final. Retiene gente durante todo el directo.</li>
      <li><b>Encuestas</b>: deja que el chat decida qué jugar o qué reto hacer. La participación sube muchísimo.</li>
      <li><b>Comandos de sonido</b>: <code>!susto</code>, <code>!aplausos</code>, <code>!bruh</code>… pequeños sustos y risas que generan clips.</li>
      <li><b>Mensajes automáticos</b>: “Si te gusta, sígueme y comparte” cada 10–15 min, solo si hay actividad.</li>
      <li><b>Clips</b>: activa el Replay Buffer de OBS y pulsa <code>Ctrl+Alt+K</code> cuando pase algo bueno. Súbelos como Shorts/TikToks: es la forma #1 de que te descubran.</li>
      <li><b>Multistream</b>: conecta TikTok + Twitch + Kick a la vez; el chat y las dinámicas se unifican.</li>
    </ul>`],

  problems: ["🛠️ Problemas frecuentes", () => `
    <h3>No se oye nada</h3>
    <ul><li>Comprueba que no esté silenciado (botón del altavoz abajo a la izquierda) y el volumen de la voz.</li>
      <li>En Ajustes revisa el dispositivo de salida y pulsa <b>Probar</b>.</li>
      <li>En Ajustes → Diagnóstico mira si algún motor de voz falló. Con el respaldo activado se usará otro automáticamente.</li></ul>
    <h3>“Edge TTS falló” / 403</h3>
    <p>Microsoft cambia de vez en cuando su servicio. LiveVoice cambia solo a Google o a las voces de Windows para que el directo no se quede mudo. Para recuperar las voces neuronales, actualiza: <code>pip install -U edge-tts</code> (o descarga la última versión).</p>
    <h3>Dice “Esperando directo”</h3>
    <p>Es normal: el canal no está en vivo todavía. Reintenta cada 30 segundos y se conecta solo.</p>
    <h3>El chat va muy rápido</h3>
    <p>En Lectura: baja el máximo de la cola, pon una espera por persona o un prefijo (ej. <code>!tts</code>), o lee solo a seguidores/subs.</p>
    <h3>Los overlays no aparecen en OBS</h3>
    <p>LiveVoice debe estar abierto. Comprueba la URL (puerto) y pulsa “Actualizar caché de la página actual” en las propiedades de la fuente.</p>
    <h3>Logs</h3>
    <p>Si algo falla, el archivo <code>logs/livevoice.log</code> junto al programa tiene el detalle.</p>`],
};

let active = "start";

function render(root) {
  root.innerHTML = `
    <div class="page-head"><div><h1>Guía</h1><p>Todo lo que necesitas para configurar tu directo en 5 minutos.</p></div></div>
    <div class="guide-tabs">${Object.entries(SECTIONS).map(([id, [label]]) => `<button class="btn sm ${id === active ? "primary" : ""}" data-section="${id}">${label}</button>`).join("")}</div>
    <div class="card guide" id="guide-body">${SECTIONS[active][1]()}</div>`;
  if (root.dataset.wired) return;
  root.dataset.wired = "1";
  root.addEventListener("click", (event) => {
    const go = event.target.closest("[data-go]");
    if (go) { event.preventDefault(); window.lvsNavigate(go.dataset.go); return; }
    const section = event.target.closest("[data-section]");
    if (section) { event.preventDefault(); active = section.dataset.section; render(root); }
  });
}

export default { id: "guide", label: "Guía", icon: "help", render };
