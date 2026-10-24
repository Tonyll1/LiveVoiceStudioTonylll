# LiveVoice Studio

**La alternativa gratuita a TikFinity para streamers pequeños.** Lee tu chat en voz alta, muestra alertas en OBS y hace dinámicas con tu comunidad en **TikTok, Twitch, Kick y YouTube a la vez**. Sin cuentas, sin suscripciones, sin límite de voces.

## Qué hace

| | |
|---|---|
| 🎙️ **Voz** | +300 voces neuronales (Edge), **voces de IA** (Kokoro local sin internet y ElevenLabs con tu clave, incluso voces clonadas), voces **Piper sin internet**, voces de Windows (incluye Loquendo u otras SAPI si las instalas) y voces de TikTok (Ghostface, Stormtrooper…). Velocidad, tono y 10 personajes. |
| 💻 **100% local** | No hay servidor: todo corre en tu PC. Con Piper o Windows la voz funciona incluso sin internet. |
| 🛟 **No se cae** | Si Microsoft cambia algo, salta solo a Google, Piper o Windows. Las plataformas se reconectan solas y esperan a que empiece el directo. |
| 🧪 **Campo de pruebas** | Simula un directo completo (eventos, ráfagas, comandos, sorteos, encuestas) y mira todos los overlays reaccionar sin estar en vivo. |
| 🧑‍🤝‍🧑 **Voz por espectador** | Voz aleatoria fija para cada persona, o la eligen ellos con `!voz argentino`, `!voz gringo`, `!voz ardilla`… |
| 🌐 **Multiplataforma** | TikTok, Twitch, Kick y YouTube al mismo tiempo, con chat, comandos y dinámicas unificados. |
| ⌨️ **Atajos globales** | Silenciar, saltar, pausar, vaciar cola y clip desde el juego (`Ctrl+Alt+M/S/P/C/K`). Compatible con Stream Deck. |
| 🔔 **Alertas** | Follows, regalos, subs, bits, raids, compartidos e hitos de likes con voz, sonido y animación. **Alertas propias**: tu sonido, imagen/GIF/video, frase y voz para un regalo concreto, un raid grande o una palabra del chat. |
| 🎬 **Overlays para OBS** | Todo en uno, alertas, chat unificado, subtítulos de la voz, metas, ranking, sorteo, encuesta, actividad reciente, último seguidor/regalo, contadores y comandos de sonido (fondo transparente). Temas (Neón, Minimal, Gamer, Pastel, Cristal), fuentes, colores, posición, animaciones y CSS propio. |
| 🎉 **Dinámicas** | Sorteos, encuestas, metas, mensajes automáticos, bienvenida, puntos de fidelidad y juegos (`!dado`, `!bola`, `!amor`, `!moneda`). |
| 🔊 **Comandos de sonido** | `!susto`, `!aplausos`… con cooldown por persona y global, y permisos (todos, subs, mods, lista). |
| ✂️ **Clips** | Guarda el Replay Buffer de OBS con un atajo, con `!clip` de tus mods o automáticamente con regalos grandes. Anota la hora en `clips/marcas.csv`. |

## Usarlo

### Desde el código (Windows)

Doble clic en **`start.bat`**. La primera vez instala todo (necesitas [Python 3.13](https://www.python.org/downloads/)).

O a mano:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Opciones: `--browser` abre el panel en el navegador, `--headless` solo arranca el servidor.

### Si la voz deja de funcionar

Microsoft y TikTok cambian sus servicios de vez en cuando. Mientras tanto la app usa los respaldos, y para volver a las voces neuronales basta con ejecutar **`update.bat`**.

## Primeros pasos

1. Pestaña **Directo** → escribe tu canal → **Conectar**.
2. **Voces** → elige tu voz y pruébala.
3. **Overlays** → copia las URL en OBS como *Fuente de navegador*.
4. La pestaña **Guía** de la app explica OBS, audio en pista separada (VB-Cable), cada plataforma y consejos para crecer.

## Crear el EXE

```powershell
.\build_exe.ps1
```

Se genera `dist\LiveVoiceStudio.exe` (portable: la configuración y los datos se guardan junto al exe).

## Estructura

```
main.py                 Arranque: backend en un hilo + ventana (pywebview)
livevoice/
  app.py                Orquestador: procesa cada evento y expone acciones
  core/                 Configuración, bus de eventos, modelos, estadísticas
  platforms/            TikTok, Twitch (IRC anónimo), Kick (Pusher), YouTube
  tts/                  Motores (Edge, Google, Windows), catálogo, cola con respaldo
  features/             Moderación, lectura, comandos, alertas, dinámicas, OBS, atajos
  server/               Servidor local (panel, API, websocket, overlays)
web/
  dashboard/            Panel de control
  overlays/             Overlays para OBS
tests/                  pytest
```

## Voces extra

- **Kokoro (IA, sin internet):** página Voces → *Voces de IA* → Descargar Kokoro (~355 MB). Voces en español: Alex, Dora, Santa.
- **ElevenLabs (IA, online):** pon tu clave en Ajustes → *Cargar mis voces*. Incluye tus voces clonadas.
- **Piper (sin internet):** página Voces → *Voces sin internet* → Descargar, o descarga `.onnx` + `.onnx.json` de huggingface.co/rhasspy/piper-voices y cópialos a `voices/piper`.
- **Loquendo y otras voces SAPI:** instálalas en Windows y pulsa *Actualizar catálogo*. Las de 32 bits también se detectan.
- **“Brian” de StreamElements:** StreamElements cerró su TTS gratuito (finales de 2025). Usa su equivalente en Edge, Ryan (Reino Unido), o `!voz brian`.
- **TikTok (Ghostface, Stormtrooper…):** requiere tu `sessionid` de TikTok (Ajustes). Experimental.

## Limitaciones conocidas

- Los **follows de Twitch, Kick y YouTube** requieren iniciar sesión con la cuenta del canal; por ahora solo se leen los de TikTok.
- TikTok usa un servidor de firmas gratuito con límite de uso. Si ves errores de “rate limit”, añade una clave gratuita de eulerstream.com en Ajustes.
- La app es de **solo lectura**: no escribe en el chat de las plataformas.

## Licencia

Consulta `LICENSE`.
