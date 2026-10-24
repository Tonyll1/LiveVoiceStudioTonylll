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
      <li><code>/overlay/events</code> — actividad reciente (follows, regalos, subs, raids).</li>
      <li><code>/overlay/latest?type=follow</code> — último seguidor (<code>gift</code>, <code>sub</code>, <code>bits</code>, <code>raid</code>).</li>
      <li><code>/overlay/counter?stat=likes</code> — contador animado (<code>viewers</code>, <code>followers</code>, <code>messages</code>…).</li>
      <li><code>/overlay/command</code> — aviso cuando alguien usa un comando de sonido.</li>
      <li><code>/overlay/all</code> — <b>todo en uno</b>: una sola fuente 1920×1080 con lo principal ya colocado.</li>
    </ul>
    <p>Todos aceptan <code>?accent=%23ff0066</code> (color) y <code>?size=28</code> (tamaño de letra) para personalizarlos por separado.
      Pruébalos todos a la vez en <a href="#" data-go="playground">Campo de pruebas</a>.</p>`],

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

  local: ["💻 Todo funciona en tu PC", () => `
    <p>LiveVoice Studio <b>no necesita ningún servidor</b> ni cuenta: lo instalas y todo corre en tu computadora.</p>
    <ul>
      <li><b>El panel y los overlays</b> los sirve la propia app en <code>${origin()}</code>. Solo tu PC (y OBS, que corre en ella) los ve.</li>
      <li><b>Tus datos</b> (config, puntos, sonidos, clips, voces descargadas) se guardan en la carpeta del programa. Puedes copiarla a otro PC o a un USB.</li>
      <li><b>El chat</b> se lee directamente de TikTok/Twitch/Kick/YouTube desde tu PC.</li>
    </ul>
    <h3>¿Qué necesita internet y qué no?</h3>
    <table class="table"><tbody>
      <tr><td>Voces <b>Piper</b> y <b>Windows</b> (incluido Loquendo si lo instalas)</td><td><span class="pill connected">Sin internet</span></td></tr>
      <tr><td>Voces Edge y Google</td><td><span class="pill waiting">Necesitan internet</span></td></tr>
      <tr><td>Voces de TikTok</td><td><span class="pill waiting">Internet + tu sessionid</span></td></tr>
      <tr><td>Leer el chat de las plataformas</td><td><span class="pill waiting">Internet (obvio: estás en directo)</span></td></tr>
    </tbody></table>
    <div class="callout">💡 Para no depender de nadie: descarga una voz Piper en español (página Voces). Si Microsoft o Google fallan, la app usa Piper o Windows automáticamente.</div>`],

  voices: ["🎭 Voces extra y Loquendo", () => `
    <h3>Motores disponibles</h3>
    <ul>
      <li><b>Edge</b> — 300+ voces neuronales de Microsoft. La mejor calidad gratis.</li>
      <li><b>Piper</b> — voces neuronales que corren en tu PC, sin internet. Descárgalas en la página Voces.</li>
      <li><b>¿Y “Brian” de StreamElements?</b> StreamElements cerró su generador de voces gratuito a finales de 2025. Su equivalente es <b>Ryan (Reino Unido)</b> en Edge; el chat lo pide con <code>!voz brian</code>.</li>
      <li><b>TikTok</b> — Ghostface, Stormtrooper, C-3PO, Rocket, el señor mexicano, cantantes… Igual que TikFinity, necesitan tu <code>sessionid</code> (Ajustes).</li>
      <li><b>Windows</b> — las voces instaladas en tu sistema (Raúl, Sabina…) y cualquier voz SAPI que instales, como Loquendo.</li>
      <li><b>Google</b> — la voz del traductor; respaldo de emergencia.</li>
    </ul>
    <h3>Loquendo (Jorge, Carmen, Javier…)</h3>
    <p>Loquendo es un programa <b>comercial y descontinuado</b> (ahora es de Nuance/Microsoft), por eso no puede venir incluido. Pero si tienes un instalador de sus voces <b>SAPI5</b>:</p>
    <ol class="steps">
      <li>Instálalo normalmente en Windows (son voces de 32 bits).</li>
      <li>En LiveVoice: Voces → <b>Actualizar catálogo</b>.</li>
      <li>Aparecerán en el filtro <b>Windows</b> con la etiqueta “(32 bits)”. Elige una y listo: sin internet.</li>
    </ol>
    <div class="callout warn">Descarga instaladores solo de fuentes legítimas o de licencias que tengas. Los “Loquendo gratis” de sitios desconocidos suelen traer malware.</div>
    <p>Lo mismo vale para otras voces SAPI (IVONA, Acapela, Cepstral, eSpeak…): si Windows las ve, LiveVoice también.</p>
    <h3>Más voces gratis de Windows</h3>
    <ol class="steps">
      <li>Windows → Configuración → Hora e idioma → <b>Voz</b> → Agregar voces.</li>
      <li>Instala idiomas/voces (ej. Español de España, Inglés). Son gratis y funcionan sin internet.</li>
      <li>En LiveVoice pulsa <b>Actualizar catálogo</b>.</li>
    </ol>
    <h3>Crear tu propia voz (o la de un personaje)</h3>
    <p>Puedes entrenar una voz Piper con unas horas de grabaciones limpias de una persona (¡con su permiso!):</p>
    <ol class="steps">
      <li>Graba o reúne 1–3 horas de audio claro con su transcripción (formato LJSpeech: <code>wav</code> + <code>metadata.csv</code>).</li>
      <li>Usa el entrenamiento de Piper (proyecto <code>rhasspy/piper</code>, carpeta <code>TRAINING.md</code>) partiendo de una voz en español existente; con una GPU tarda unas horas.</li>
      <li>Exporta el modelo a <code>.onnx</code> y copia <code>mi-voz.onnx</code> y <code>mi-voz.onnx.json</code> a la carpeta <code>voices/piper</code> del programa.</li>
      <li>Actualiza el catálogo: aparecerá como voz Piper y funcionará sin internet.</li>
    </ol>
    <div class="callout">Para efectos rápidos sin entrenar nada usa los <b>personajes</b> (ardilla, gigante, robot…) sobre cualquier voz neuronal.</div>`],

  ai: ["🤖 Voces de IA y Piper", () => `
    <p>Todas las voces “neuronales” son IA. Estas son las opciones, de más fácil a más avanzada:</p>
    <table class="table"><tbody>
      <tr><td><b>Edge</b></td><td>300+ voces IA de Microsoft</td><td><span class="pill waiting">Internet</span></td><td>Ya incluidas</td></tr>
      <tr><td><b>Kokoro</b></td><td>IA local de alta calidad (Alex, Dora, Santa…)</td><td><span class="pill connected">Sin internet</span></td><td>Voces → Voces de IA → Descargar (~355 MB)</td></tr>
      <tr><td><b>Piper</b></td><td>IA local ligera, muchos acentos</td><td><span class="pill connected">Sin internet</span></td><td>Voces → Voces sin internet → Descargar (20–110 MB)</td></tr>
      <tr><td><b>ElevenLabs</b></td><td>La IA más realista y voces clonadas</td><td><span class="pill waiting">Internet + clave</span></td><td>Ajustes → ElevenLabs</td></tr>
    </tbody></table>

    <h3>Cómo conseguir voces Piper</h3>
    <ol class="steps">
      <li><b>Desde la app (lo más fácil):</b> Voces → “Voces sin internet (Piper)” → <b>Ver voces para descargar</b> → elige y pulsa Descargar. En español hay de México (Ald, Claude), España (Davefx, Sharvard, Carlfm) y Argentina (Daniela).</li>
      <li><b>A mano:</b> entra en <code>huggingface.co/rhasspy/piper-voices</code>, abre <code>es/</code> → país → voz → calidad, y descarga los dos archivos: <code>.onnx</code> y <code>.onnx.json</code>.</li>
      <li>Cópialos a la carpeta <code>voices/piper</code> del programa (junto a config.json) y pulsa <b>Actualizar catálogo</b> en Voces.</li>
      <li><b>Voces de la comunidad:</b> hay miles de modelos Piper entrenados por usuarios (personajes, acentos, idiomas). Cualquier par <code>.onnx</code> + <code>.onnx.json</code> compatible con Piper funciona igual.</li>
    </ol>
    <div class="callout">💡 Calidad: <b>x_low</b> y <b>low</b> son rápidas y ligeras; <b>medium</b> es el equilibrio; <b>high</b> suena mejor pero pesa más.</div>

    <h3>Kokoro (IA local recomendada)</h3>
    <p>Suena más natural que Piper y funciona sin internet. Tras descargarla, filtra por “IA Kokoro” en Voces. La primera frase tarda un poco mientras carga el modelo; después ~1 segundo por frase.
      Las voces en inglés (Heart, Bella, Adam, Michael…) leyendo español dan un acento “gringo” muy gracioso.</p>

    <h3>ElevenLabs (clonar voces)</h3>
    <ol class="steps">
      <li>Crea una cuenta gratis en <code>elevenlabs.io</code>.</li>
      <li>Para clonar: Voices → <b>Add voice</b> → <b>Instant Voice Clone</b> → sube 1–2 minutos de audio limpio. <b>Solo voces propias o con permiso.</b></li>
      <li>Perfil → API Keys → crea una clave y pégala en Ajustes → ElevenLabs → <b>Cargar mis voces</b>.</li>
      <li>El plan gratis tiene un límite de caracteres al mes: úsala en alertas propias o para personajes, no para todo el chat. Si se acaba, la app usa el respaldo automático.</li>
    </ol>

    <h3>Entrenar tu propia voz Piper (avanzado)</h3>
    <p>Con 1–3 horas de grabaciones limpias de una persona (con su permiso) puedes entrenar un modelo Piper partiendo de una voz en español (proyecto <code>rhasspy/piper</code>, guía <code>TRAINING.md</code>; necesitas una GPU). Exportas a <code>.onnx</code> y lo copias a <code>voices/piper</code>.</p>`],

  custom: ["✨ Alertas propias y personalizar", () => `
    <h3>Alertas propias</h3>
    <p>En <a href="#" data-go="alerts">Alertas</a> → <b>Tus alertas propias</b> → <b>Nueva alerta</b>. Cada alerta tiene:</p>
    <ul>
      <li><b>Cuándo:</b> un regalo concreto (ej. “Galaxia”) o cualquiera con un valor mínimo, follow, sub, bits, raid con mínimo de personas, compartir, likes, o una <b>palabra del chat</b> (ej. “jajaja” → sonido de risa).</li>
      <li><b>Solo en:</b> limítala a una plataforma (ej. solo raids de Twitch).</li>
      <li><b>Sonido:</b> tu MP3/WAV/OGG con su volumen.</li>
      <li><b>Imagen, GIF o video:</b> PNG, JPG, GIF, WEBP, MP4 o WEBM. Aparece en el overlay de Alertas; los videos duran lo que dure el clip.</li>
      <li><b>Frase y voz:</b> lo que dice, con la voz que quieras (por ejemplo Ghostface o una voz clonada de ElevenLabs solo para esa alerta).</li>
      <li><b>Sustituir la alerta normal:</b> si está activo, ese evento ya no muestra la alerta por defecto.</li>
    </ul>
    <div class="callout">💡 Consigue sonidos y GIFs libres en sitios como <code>myinstants.com</code>, <code>freesound.org</code>, <code>pixabay.com</code> o <code>giphy.com</code> (revisa la licencia si monetizas).</div>
    <h3>Personalizar los overlays</h3>
    <p>En <a href="#" data-go="overlays">Overlays</a> → <b>Apariencia</b>: tema (Neón, Minimal, Gamer, Pastel, Cristal), fuente, colores, opacidad, posición, animación y duración de las alertas. Los cambios se ven al momento en OBS.</p>
    <p>¿Quieres un overlay distinto en otra escena? Añade parámetros a su URL: <code>?theme=gamer</code>, <code>?accent=%23ff0066</code>, <code>?size=30</code>, <code>?font=Bangers</code>, <code>?position=bottom</code>, <code>?animation=bounce</code>, <code>?duration=8</code>.</p>
    <p>Para control total: <b>CSS personalizado</b> en Apariencia, o el campo “CSS personalizado” de la fuente de navegador en OBS.</p>`],

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
