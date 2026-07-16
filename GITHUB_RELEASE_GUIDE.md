# Publicar LiveVoice Studio en GitHub

## 1. Crear el repositorio

Crea un repositorio público vacío en GitHub, por ejemplo `LiveVoiceStudio`.
No marques la opción de crear README, porque el proyecto ya contiene uno.

## 2. Subir el proyecto por primera vez

Abre PowerShell dentro de la carpeta del proyecto y ejecuta:

```powershell
git init
git add .
git commit -m "LiveVoice Studio v0.3 - comandos personalizados"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/LiveVoiceStudio.git
git push -u origin main
```

Sustituye `TU_USUARIO` por tu usuario de GitHub.

## 3. Descargar un EXE de prueba

Cada push a `main` ejecuta **Build Windows EXE**:

1. Abre la pestaña **Actions** del repositorio.
2. Entra al flujo terminado.
3. Descarga el artefacto `LiveVoiceStudio-Windows`.

Los artefactos de Actions son útiles para pruebas, pero no son la descarga pública definitiva.

## 4. Publicar una versión descargable

Crea y sube una etiqueta de versión:

```powershell
git tag v0.3.0
git push origin v0.3.0
```

GitHub Actions compilará Windows y creará automáticamente un Release con:

```text
LiveVoiceStudio-v0.3.0-Windows.zip
```

Los usuarios podrán descargarlo desde la sección **Releases** del repositorio.

## 5. Crear el EXE localmente

En Windows con Python 3.13 instalado:

```powershell
.\build_exe.ps1
```

El resultado quedará en:

```text
dist\LiveVoiceStudio.exe
```

## Nota de Windows SmartScreen

Mientras el ejecutable no tenga una firma digital de editor, Windows puede mostrar una advertencia de SmartScreen. Esto no significa automáticamente que tenga malware. Para una publicación comercial futura conviene firmar el instalador o el ejecutable con un certificado de firma de código.
