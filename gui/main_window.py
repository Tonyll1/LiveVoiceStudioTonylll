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
from services.tts.manager import TTSManager


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class MainWindow(ctk.CTk):
    def __init__(self, container):
        super().__init__()

        self.container = container
        self.settings_window = None
        self.commands_window = None

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

        user_label = ctk.CTkLabel(
            self.sidebar,
            text="Usuario de TikTok",
            font=("Segoe UI", 13)
        )
        user_label.pack(
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
            text="Conectar LIVE",
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
            text="LiveVoice Studio v0.5",
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

        username = config.get(
            "username",
            ""
        )

        if username:
            self.username_entry.insert(
                0,
                username
            )

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

    def connect_live(self):
        username = (
            self.username_entry
            .get()
            .strip()
            .replace("@", "")
        )

        if not username:
            self.add_system_message(
                "Escribe un usuario válido."
            )
            return

        config = self.container.get("config")
        config.set(
            "username",
            username
        )

        self.status_label.configure(
            text="🟡 Conectando...",
            text_color="#ffaa00"
        )

        self.connect_button.configure(
            state="disabled",
            text="Conectando..."
        )

        self.add_system_message(
            f"Conectando con @{username}..."
        )

        tiktok = self.container.get(
            TikTokClient
        )
        tiktok.connect(username)

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

            self._insert_chat_text(
                f"{nickname}: "
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

    def on_connect(self):
        def update():
            self.status_label.configure(
                text="🟢 Conectado",
                text_color="#55ff88"
            )

            self.connect_button.configure(
                state="normal",
                text="Conectar LIVE"
            )

            self.add_system_message(
                "Conectado correctamente al LIVE."
            )

        self.after(
            0,
            update
        )

    def on_disconnect(self):
        def update():
            self.status_label.configure(
                text="🔴 Desconectado",
                text_color="#ff5555"
            )

            self.connect_button.configure(
                state="normal",
                text="Conectar LIVE"
            )

            self.add_system_message(
                "Desconectado del LIVE."
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

            self.connect_button.configure(
                state="normal",
                text="Conectar LIVE"
            )

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

    def clear_chat(self):
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

        self.add_system_message(
            "Chat limpiado."
        )

    def on_close(self):
        try:
            tts = self.container.get(
                TTSManager
            )
            tts.stop()
        except Exception:
            pass

        self.destroy()