"""LiveVoice Studio: punto de entrada.

El backend (plataformas, voz, servidor local) corre en un hilo con su propio
event loop; la ventana del panel (pywebview) ocupa el hilo principal. Si
pywebview no está disponible, el panel se abre en el navegador.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import threading
import urllib.request
import webbrowser

from livevoice import APP_NAME, VERSION
from livevoice.core.logger import logger


def already_running(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state", timeout=1) as response:
            return response.status == 200
    except Exception:
        return False


def _quiet_exceptions(loop, context):
    # En Windows, cerrar sockets que el servidor remoto ya cortó genera ruido inofensivo.
    if isinstance(context.get("exception"), (ConnectionResetError, ConnectionAbortedError)):
        return
    loop.default_exception_handler(context)


class Backend(threading.Thread):
    def __init__(self):
        super().__init__(name="LiveVoiceBackend", daemon=True)
        self.ready = threading.Event()
        self.url = ""
        self.error: Exception | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self._shutdown: asyncio.Event | None = None

    def run(self):
        try:
            asyncio.run(self._main())
        except Exception as error:
            logger.exception("El backend se detuvo por un error")
            self.error = error
            self.ready.set()

    async def _main(self):
        from livevoice.app import Studio
        from livevoice.server.app import Server

        self.loop = asyncio.get_running_loop()
        self.loop.set_exception_handler(_quiet_exceptions)
        self._shutdown = asyncio.Event()
        studio = Studio()
        server = Server(studio, port=int(studio.config.get("general.port", 8765)))
        port = await server.start()
        await studio.start()
        self.url = f"http://127.0.0.1:{port}/app/"
        self.ready.set()
        await self._shutdown.wait()
        await studio.shutdown()
        await server.stop()

    def stop(self):
        if self.loop and self._shutdown:
            self.loop.call_soon_threadsafe(self._shutdown.set)


def main():
    parser = argparse.ArgumentParser(description=f"{APP_NAME} {VERSION}")
    parser.add_argument("--browser", action="store_true", help="Abrir el panel en el navegador en vez de ventana propia")
    parser.add_argument("--headless", action="store_true", help="No abrir ninguna ventana (solo servidor)")
    args = parser.parse_args()

    from livevoice.core.config import Config

    port = int(Config().get("general.port", 8765))
    if already_running(port):
        webbrowser.open(f"http://127.0.0.1:{port}/app/")
        return

    backend = Backend()
    backend.start()
    backend.ready.wait(timeout=30)
    if backend.error or not backend.url:
        print(f"No se pudo iniciar {APP_NAME}: {backend.error}", file=sys.stderr)
        sys.exit(1)

    if args.headless:
        print(f"{APP_NAME} en {backend.url}")
        try:
            backend.join()
        except KeyboardInterrupt:
            backend.stop()
        return

    use_window = not args.browser
    if use_window:
        try:
            import webview

            webview.create_window(
                f"{APP_NAME} {VERSION}",
                backend.url,
                width=1360,
                height=860,
                min_size=(1000, 680),
                background_color="#0b0b12",
            )
            webview.start()
        except Exception as error:
            logger.warning("No se pudo abrir la ventana propia (%s); se usa el navegador.", error)
            use_window = False

    if not use_window:
        webbrowser.open(backend.url)
        print(f"{APP_NAME} abierto en {backend.url}  (Ctrl+C para cerrar)")
        try:
            while backend.is_alive():
                backend.join(timeout=0.5)
        except KeyboardInterrupt:
            pass

    backend.stop()
    backend.join(timeout=5)


if __name__ == "__main__":
    main()
