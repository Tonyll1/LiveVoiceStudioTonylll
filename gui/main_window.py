import customtkinter as ctk

from core.constants import (
    COMMENT_EVENT,
    CONNECT_EVENT,
    DISCONNECT_EVENT,
    ERROR_EVENT,
    STATUS_EVENT,
)
from core.event_bus import event_bus

from gui.commands_window import CommandsWindow
from gui.settings_window import SettingsWindow

from services.tiktok.client import TikTokClient
from services.twitch.client import TwitchClient
from services.tts.manager import TTSManager


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

CHAT_AUTO_CLEAR_MS = 20 * 60 * 1000


class MainWindow(ctk.CTk):
    def __init__(self, container):
        super().__init__()

        self.container = container
        self.settings_window = None
        self.commands_window = None
        self.active_platform = None

        self.title("LiveVoice Studio")
        self.geometry("1050x680")
        self.minsize(950, 620)

        self.protocol(
            "WM_DELETE_WINDOW",
            self.on_close
        )

        self._build_ui()
        self._load_config()
        self._subscribe_events()
        self._schedule_chat_cleanup()

    def _build_ui(self):
        self.grid_columnconfigure(
            1,
            weight=1
        )
        self.grid_rowconfigure(
            0,
            weight=1
        )

        # ─────────────────────────────
        # Panel lateral
        # ─────────────────────────────

        self.sidebar = ctk.CTkFrame(
            self,
            width=280,
            corner_radius=0
        )
        self.sidebar.grid(
            row=0,
            column=0,
            sticky="nsew"
        )
        self.sidebar.grid_propagate(False)

        title = ctk.CTkLabel(
            self.sidebar,
            text="🎤 LiveVoice\nStudio",
            font=("Segoe UI", 28, "bold"),
            justify="left"
        )
        title.pack(
            pady=(25, 20),
            padx=20,
            anchor="w"
        )

        self.status_label = ctk.CTkLabel(
            self.sidebar,
            text="🔴 Desconectado",
            text_color="#ff5555",
            font=("Segoe UI", 16, "bold")
        )
        self.status_label.pack(
            padx=20,
            pady=(0, 20),
            anchor="w"
        )

        platform_label = ctk.CTkLabel(
            self.sidebar,
            text="Plataforma",
            font=("Segoe UI", 13)
        )
        platform_label.pack(
            padx=20,
            anchor="w"
        )

        self.platform_selector = ctk.CTkOptionMenu(
            self.sidebar,
            values=["TikTok", "Twitch"],
            height=36,
            command=self.on_platform_change
        )
        self.platform_selector.pack(
            padx=20,
            pady=(5, 12),
            fill="x"
        )

        self.channel_label = ctk.CTkLabel(
            self.sidebar,
            text="Usuario de TikTok",
            font=("Segoe UI", 13)
        )
        self.channel_label.pack(
            padx=20,
            anchor="w"
        )

        self.username_entry = ctk.CTkEntry(
            self.sidebar,
            placeholder_text="usuario sin @",
            height=36
        )
        self.username_entry.pack(
            padx=20,
            pady=(5, 15),
            fill="x"
        )

        self.username_entry.bind(
            "<Return>",
            lambda _event: self.connect_live()
        )

        self.connect_button = ctk.CTkButton(
            self.sidebar,
            text="Conectar",
            height=38,
            command=self.connect_live
        )
        self.connect_button.pack(
            padx=20,
            pady=(5, 10),
            fill="x"
        )

        self.test_button = ctk.CTkButton(
            self.sidebar,
            text="Probar voz",
            height=36,
            command=self.test_voice
        )
        self.test_button.pack(
            padx=20,
            pady=(0, 10),
            fill="x"
        )

        self.settings_button = ctk.CTkButton(
            self.sidebar,
            text="Configuración",
            height=36,
            command=self.open_settings
        )
        self.settings_button.pack(
            padx=20,
            pady=(0, 10),
            fill="x"
        )

        self.commands_button = ctk.CTkButton(
            self.sidebar,
            text="Comandos",
            height=36,
            command=self.open_commands
        )
        self.commands_button.pack(
            padx=20,
            pady=(0, 10),
            fill="x"
        )

        self.clear_button = ctk.CTkButton(
            self.sidebar,
            text="Limpiar chat",
            height=36,
            command=self.clear_chat
        )
        self.clear_button.pack(
            padx=20,
            pady=(0, 10),
            fill="x"
        )

        version_label = ctk.CTkLabel(
            self.sidebar,
            text="LiveVoice Studio v0.6.3",
            text_color="#8d8d8d",
            font=("Segoe UI", 11)
        )
        version_label.pack(
            side="bottom",
            padx=20,
            pady=20,
            anchor="w"
        )

        # ─────────────────────────────
        # Panel principal
        # ─────────────────────────────

        self.main = ctk.CTkFrame(self)
        self.main.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=15,
            pady=15
        )

        self.main.grid_columnconfigure(
            0,
            weight=1
        )
        self.main.grid_rowconfigure(
            1,
            weight=1
        )

        header = ctk.CTkFrame(
            self.main,
            fg_color="transparent"
        )
        header.grid(
            row=0,
            column=0,
            padx=20,
            pady=(18, 10),
            sticky="ew"
        )

        header.grid_columnconfigure(
            0,
            weight=1
        )

        main_title = ctk.CTkLabel(
            header,
            text="Chat en vivo",
            font=("Segoe UI", 22, "bold")
        )
        main_title.grid(
            row=0,
            column=0,
            sticky="w"
        )

        self.message_count_label = ctk.CTkLabel(
            header,
            text="0 mensajes",
            text_color="#9b9b9b",
            font=("Segoe UI", 12)
        )
        self.message_count_label.grid(
            row=0,
            column=1,
            sticky="e"
        )

        self.chat_box = ctk.CTkTextbox(
            self.main,
            font=("Segoe UI", 14),
            wrap="word"
        )
        self.chat_box.grid(
            row=1,
            column=0,
            padx=20,
            pady=(0, 20),
            sticky="nsew"
        )

        self.chat_box.insert(
            "end",
            "LiveVoice Studio iniciado.\n"
        )
        self.chat_box.configure(
            state="disabled"
        )

        self.message_count = 0

    def _load_config(self):
        config = self.container.get("config")

        platform = config.get("platform", "TikTok")
        if platform not in ("TikTok", "Twitch"):
            platform = "TikTok"

        self.platform_selector.set(platform)
        self.on_platform_change(platform, load_saved=True)

    def _subscribe_events(self):
        event_bus.subscribe(
            COMMENT_EVENT,
            self.on_comment
        )

        event_bus.subscribe(
            CONNECT_EVENT,
            self.on_connect
        )

        event_bus.subscribe(
            DISCONNECT_EVENT,
            self.on_disconnect
        )

        event_bus.subscribe(
            ERROR_EVENT,
            self.on_error
        )

        event_bus.subscribe(
            STATUS_EVENT,
            self.on_status
        )

    def on_platform_change(self, platform: str, load_saved: bool = False):
        if self.active_platform is not None:
            self.platform_selector.set(self.active_platform)
            return

        config = self.container.get("config")
        config.set("platform", platform)

        self.username_entry.delete(0, "end")
        if platform == "Twitch":
            self.channel_label.configure(text="Canal de Twitch")
            self.username_entry.configure(placeholder_text="canal sin #")
            saved_value = config.get("twitch_channel", "")
        else:
            self.channel_label.configure(text="Usuario de TikTok")
            self.username_entry.configure(placeholder_text="usuario sin @")
            saved_value = config.get("username", "")

        if saved_value:
            self.username_entry.insert(0, saved_value)

    def connect_live(self):
        if self.active_platform is not None:
            self.disconnect_live()
            return

        target = (
            self.username_entry
            .get()
            .strip()
            .replace("@", "")
            .replace("#", "")
        )

        if not target:
            self.add_system_message("Escribe un usuario o canal válido.")
            return

        platform = self.platform_selector.get()
        config = self.container.get("config")
        config.set("platform", platform)

        if platform == "Twitch":
            config.set("twitch_channel", target)
        else:
            config.set("username", target)

        self.status_label.configure(
            text="🟡 Conectando...",
            text_color="#ffaa00"
        )
        self.connect_button.configure(
            state="disabled",
            text="Conectando..."
        )
        self.platform_selector.configure(state="disabled")

        if platform == "Twitch":
            self.add_system_message(f"Conectando con Twitch #{target}...")
            self.container.get(TwitchClient).connect(target)
        else:
            self.add_system_message(f"Conectando con TikTok @{target}...")
            self.container.get(TikTokClient).connect(target)

    def disconnect_live(self):
        if self.active_platform == "Twitch":
            self.container.get(TwitchClient).disconnect()
        elif self.active_platform == "TikTok":
            self.container.get(TikTokClient).disconnect()

        self.connect_button.configure(state="disabled", text="Desconectando...")

    def test_voice(self):
        tts = self.container.get(
            TTSManager
        )

        tts.test_voice()

        self.add_system_message(
            "Reproduciendo prueba de voz..."
        )

    def open_settings(self):
        if (
            self.settings_window is not None
            and self.settings_window.winfo_exists()
        ):
            self.settings_window.focus()
            self.settings_window.lift()
            return

        self.settings_window = SettingsWindow(
            parent=self,
            container=self.container
        )

    def open_commands(self):
        if (
            self.commands_window is not None
            and self.commands_window.winfo_exists()
        ):
            self.commands_window.focus()
            self.commands_window.lift()
            return

        self.commands_window = CommandsWindow(
            parent=self,
            container=self.container
        )

    def on_comment(
        self,
        comment,
        read_tts: bool = True
    ):
        def update():
            nickname = (
                comment.user.nickname
                or comment.user.username
                or "Usuario"
            )

            tts_status = (
                ""
                if read_tts
                else " 🔇"
            )

            platform = getattr(comment, "platform", "tiktok").capitalize()
            self._insert_chat_text(
                f"[{platform}] {nickname}: "
                f"{comment.text}"
                f"{tts_status}\n"
            )

            self.message_count += 1

            self.message_count_label.configure(
                text=(
                    f"{self.message_count} "
                    f"{'mensaje' if self.message_count == 1 else 'mensajes'}"
                )
            )

        self.after(
            0,
            update
        )

    def on_connect(self, platform="tiktok", target=None):
        def update():
            self.active_platform = platform.capitalize()
            self.status_label.configure(
                text=f"🟢 {self.active_platform} conectado",
                text_color="#55ff88"
            )
            self.connect_button.configure(
                state="normal",
                text="Desconectar"
            )
            self.platform_selector.configure(state="disabled")
            destination = f" a {target}" if target else ""
            self.add_system_message(
                f"Conectado correctamente a {self.active_platform}{destination}."
            )

        self.after(
            0,
            update
        )

    def on_disconnect(self, _platform=None):
        def update():
            self.status_label.configure(
                text="🔴 Desconectado",
                text_color="#ff5555"
            )

            self.active_platform = None
            self.connect_button.configure(
                state="normal",
                text="Conectar"
            )
            self.platform_selector.configure(state="normal")

            self.add_system_message(
                "Desconectado del chat en vivo."
            )

        self.after(
            0,
            update
        )

    def on_error(self, message):
        def update():
            self.status_label.configure(
                text="🔴 Error",
                text_color="#ff5555"
            )

            self.active_platform = None
            self.connect_button.configure(
                state="normal",
                text="Conectar"
            )
            self.platform_selector.configure(state="normal")

            self.add_system_message(
                f"Error: {message}"
            )

        self.after(
            0,
            update
        )

    def on_status(self, message):
        self.add_system_message(
            message
        )

    def add_system_message(self, message):
        def update():
            self._insert_chat_text(
                f"[Sistema] {message}\n"
            )

        self.after(
            0,
            update
        )

    def _insert_chat_text(self, text):
        self.chat_box.configure(
            state="normal"
        )

        self.chat_box.insert(
            "end",
            text
        )

        self.chat_box.see(
            "end"
        )

        self.chat_box.configure(
            state="disabled"
        )

    def clear_chat(self, automatic: bool = False):
        self.chat_box.configure(
            state="normal"
        )

        self.chat_box.delete(
            "1.0",
            "end"
        )

        self.chat_box.configure(
            state="disabled"
        )

        self.message_count = 0

        self.message_count_label.configure(
            text="0 mensajes"
        )

        message = (
            "Chat limpiado automáticamente para liberar memoria."
            if automatic
            else "Chat limpiado."
        )
        self.add_system_message(message)

    def _schedule_chat_cleanup(self):
        self.after(
            CHAT_AUTO_CLEAR_MS,
            self._auto_clear_chat
        )

    def _auto_clear_chat(self):
        self.clear_chat(automatic=True)
        self._schedule_chat_cleanup()

    def on_close(self):
        try:
            self.container.get(TwitchClient).disconnect()
        except Exception:
            pass

        try:
            self.container.get(TikTokClient).disconnect()
        except Exception:
            pass

        try:
            tts = self.container.get(
                TTSManager
            )
            tts.stop()
        except Exception:
            pass

        self.destroy()