import secrets
import socket
import ssl
import threading

from core.constants import (
    COMMENT_EVENT,
    CONNECT_EVENT,
    DISCONNECT_EVENT,
    ERROR_EVENT,
    STATUS_EVENT,
)
from core.event_bus import event_bus
from core.logger import logger
from models.comment import Comment
from models.user import User
from services.tiktok.filters import MessageFilter


class TwitchClient:
    """Cliente de lectura para Twitch Chat mediante IRC seguro y anónimo.

    Esta primera versión solo lee el chat público. No envía mensajes ni realiza
    acciones de moderación, por lo que no requiere OAuth del usuario.
    """

    HOST = "irc.chat.twitch.tv"
    PORT = 6697

    def __init__(self, config):
        self.config = config
        self.filter = MessageFilter(config)
        self.channel = ""
        self.connected = False
        self.thread: threading.Thread | None = None
        self._socket: ssl.SSLSocket | None = None
        self._stop_event = threading.Event()

    def connect(self, channel: str):
        channel = self._normalize_channel(channel)
        if not channel:
            event_bus.emit(ERROR_EVENT, "Escribe un canal de Twitch válido.")
            return

        if self.thread and self.thread.is_alive():
            event_bus.emit(STATUS_EVENT, "Ya hay una conexión de Twitch activa.")
            return

        self.channel = channel
        self._stop_event.clear()
        self.thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="TwitchChatThread",
        )
        self.thread.start()

    def disconnect(self):
        self._stop_event.set()
        sock = self._socket
        self._socket = None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass

    def _run(self):
        emitted_disconnect = False
        try:
            event_bus.emit(
                STATUS_EVENT,
                f"Conectando con el chat de Twitch #{self.channel}...",
            )
            raw_socket = socket.create_connection((self.HOST, self.PORT), timeout=20)
            context = ssl.create_default_context()
            self._socket = context.wrap_socket(raw_socket, server_hostname=self.HOST)
            self._socket.settimeout(1.0)

            nickname = f"justinfan{secrets.randbelow(80000) + 10000}"
            self._send("CAP REQ :twitch.tv/tags twitch.tv/commands")
            self._send("PASS SCHMOOPIIE")
            self._send(f"NICK {nickname}")
            self._send(f"JOIN #{self.channel}")

            buffer = ""
            while not self._stop_event.is_set():
                try:
                    chunk = self._socket.recv(4096)
                except socket.timeout:
                    continue
                if not chunk:
                    break

                buffer += chunk.decode("utf-8", errors="replace")
                while "\r\n" in buffer:
                    line, buffer = buffer.split("\r\n", 1)
                    self._handle_line(line)

        except (OSError, ssl.SSLError) as error:
            if not self._stop_event.is_set():
                logger.exception("Error conectando con Twitch: %s", error)
                event_bus.emit(ERROR_EVENT, f"Twitch: {error}")
        except Exception as error:
            logger.exception("Error general en TwitchClient: %s", error)
            event_bus.emit(ERROR_EVENT, f"Twitch: {error}")
        finally:
            was_connected = self.connected
            self.connected = False
            self.disconnect()
            if was_connected:
                event_bus.emit(DISCONNECT_EVENT, "twitch")
                emitted_disconnect = True
            if not emitted_disconnect and self._stop_event.is_set():
                event_bus.emit(DISCONNECT_EVENT, "twitch")

    def _handle_line(self, line: str):
        if line.startswith("PING"):
            self._send(line.replace("PING", "PONG", 1))
            return

        if " 001 " in line and not self.connected:
            self.connected = True
            logger.info("Conectado a Twitch Chat: #%s", self.channel)
            event_bus.emit(CONNECT_EVENT, "twitch", self.channel)
            return

        if " PRIVMSG " not in line:
            return

        tags, remainder = self._split_tags(line)
        try:
            prefix, message = remainder.split(" PRIVMSG ", 1)
            _target, text = message.split(" :", 1)
        except ValueError:
            return

        username = prefix.lstrip(":").split("!", 1)[0]
        display_name = self._unescape_tag(tags.get("display-name", "")) or username
        user_id = tags.get("user-id", "") or username

        show_message, read_tts, processed_text = self.filter.process(user_id, text)
        if not show_message:
            return

        event_bus.emit(
            COMMENT_EVENT,
            Comment(
                user=User(
                    id=user_id,
                    username=username,
                    nickname=display_name,
                    photo=None,
                ),
                text=processed_text,
                platform="twitch",
            ),
            read_tts,
        )

    def _send(self, line: str):
        if self._socket is None:
            return
        self._socket.sendall(f"{line}\r\n".encode("utf-8"))

    @staticmethod
    def _normalize_channel(channel: str) -> str:
        value = channel.strip().lower()
        for prefix in ("https://www.twitch.tv/", "https://twitch.tv/", "twitch.tv/"):
            if value.startswith(prefix):
                value = value[len(prefix):]
                break
        return value.strip().lstrip("#@").split("/", 1)[0]

    @staticmethod
    def _split_tags(line: str) -> tuple[dict[str, str], str]:
        if not line.startswith("@"):
            return {}, line
        raw_tags, remainder = line.split(" ", 1)
        tags: dict[str, str] = {}
        for item in raw_tags[1:].split(";"):
            key, _, value = item.partition("=")
            tags[key] = value
        return tags, remainder

    @staticmethod
    def _unescape_tag(value: str) -> str:
        replacements = {
            r"\s": " ",
            r"\:": ";",
            r"\\": "\\",
            r"\r": "\r",
            r"\n": "\n",
        }
        for encoded, decoded in replacements.items():
            value = value.replace(encoded, decoded)
        return value
