# LiveVoice Studio

**La plataforma definitiva para creadores en directo.**

LiveVoice Studio es una aplicación de escritorio para conectar chats de TikTok LIVE y Twitch, mostrar comentarios y convertirlos en voz. Esta versión añade comandos personalizados para reproducir sonidos desde el chat.

## Funciones actuales

- Conexión con TikTok LIVE.
- Lectura del chat público de Twitch por canal.
- Selector de plataforma TikTok/Twitch.
- Lectura de comentarios mediante Edge TTS.
- Catálogo dinámico de voces.
- Filtros y palabras bloqueadas.
- Configuración persistente.
- Comandos personalizados como `!susto`.
- Reproducción de sonidos MP3, WAV y OGG.
- Cooldown por usuario.
- Comandos para todos o para una lista de usuarios permitidos.

## Descargar para Windows

Abre la sección **Releases** del repositorio y descarga el archivo más reciente con el nombre:

```text
LiveVoiceStudio-vX.Y.Z-Windows.zip
```

Descomprime el ZIP y abre `LiveVoiceStudio.exe`.

## Ejecutar desde el código fuente

Requisitos:

- Windows 10 u 11.
- Python 3.13.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

## Crear el EXE

```powershell
.\build_exe.ps1
```

El ejecutable se generará en:

```text
dist\LiveVoiceStudio.exe
```

## Publicar una versión

El repositorio contiene GitHub Actions para compilar automáticamente el programa en Windows. Al subir una etiqueta como `v0.3.0`, se crea un Release público con el ejecutable comprimido.

```powershell
git tag v0.3.0
git push origin v0.3.0
```

Consulta `GITHUB_RELEASE_GUIDE.md` para el procedimiento completo.

## Estado del proyecto

LiveVoice Studio se encuentra en desarrollo. Esta versión incluye la primera etapa de comandos personalizados y soporte inicial de Twitch Chat.

## Licencia

Consulta el archivo `LICENSE`.
