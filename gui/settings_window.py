import threading

import customtkinter as ctk

from services.tiktok.blocked_words import BlockedWordsManager
from services.tts.manager import TTSManager
from services.tts.voices import Voice, VoiceCatalog


MODE_LABELS = {
    "Reemplazar por ***": "replace",
    "Mostrar sin leer": "mute",
    "Ocultar completamente": "hide"
}

MODE_VALUES = {
    value: label
    for label, value in MODE_LABELS.items()
}


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, container):
        super().__init__(parent)

        self.container = container

        self.config = container.get("config")
        self.tts = container.get(TTSManager)
        self.voice_catalog = container.get(VoiceCatalog)
        self.blocked_words = container.get(
            BlockedWordsManager
        )

        self.filtered_voices: list[Voice] = []

        self.title("Configuración — LiveVoice Studio")
        self.geometry("900x670")
        self.minsize(800, 600)

        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._load_blocked_words()
        self._load_voice_catalog()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        title = ctk.CTkLabel(
            self,
            text="Configuración",
            font=("Segoe UI", 26, "bold")
        )
        title.grid(
            row=0,
            column=0,
            padx=25,
            pady=(20, 10),
            sticky="w"
        )

        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(
            row=1,
            column=0,
            padx=20,
            pady=(0, 20),
            sticky="nsew"
        )

        self.voice_tab = self.tabs.add("Voces")
        self.reading_tab = self.tabs.add(
            "Lectura y filtros"
        )
        self.words_tab = self.tabs.add(
            "Palabras bloqueadas"
        )

        self._build_voice_tab()
        self._build_reading_tab()
        self._build_words_tab()

    # ─────────────────────────────────────
    # VOCES
    # ─────────────────────────────────────

    def _build_voice_tab(self):
        self.voice_tab.grid_columnconfigure(
            0,
            weight=1
        )
        self.voice_tab.grid_rowconfigure(
            4,
            weight=1
        )

        self.voice_status = ctk.CTkLabel(
            self.voice_tab,
            text="Cargando catálogo de voces..."
        )
        self.voice_status.grid(
            row=0,
            column=0,
            padx=15,
            pady=(15, 10),
            sticky="w"
        )

        filters_frame = ctk.CTkFrame(
            self.voice_tab
        )
        filters_frame.grid(
            row=1,
            column=0,
            padx=15,
            pady=5,
            sticky="ew"
        )

        for column in range(3):
            filters_frame.grid_columnconfigure(
                column,
                weight=1
            )

        ctk.CTkLabel(
            filters_frame,
            text="Idioma"
        ).grid(
            row=0,
            column=0,
            padx=10,
            pady=(10, 2),
            sticky="w"
        )

        self.language_combo = ctk.CTkComboBox(
            filters_frame,
            values=["Todos"],
            command=self._on_language_change
        )
        self.language_combo.grid(
            row=1,
            column=0,
            padx=10,
            pady=(0, 10),
            sticky="ew"
        )
        self.language_combo.set("es")

        ctk.CTkLabel(
            filters_frame,
            text="Región"
        ).grid(
            row=0,
            column=1,
            padx=10,
            pady=(10, 2),
            sticky="w"
        )

        self.locale_combo = ctk.CTkComboBox(
            filters_frame,
            values=["Todos"],
            command=lambda _: self._apply_voice_filters()
        )
        self.locale_combo.grid(
            row=1,
            column=1,
            padx=10,
            pady=(0, 10),
            sticky="ew"
        )
        self.locale_combo.set("Todos")

        ctk.CTkLabel(
            filters_frame,
            text="Género"
        ).grid(
            row=0,
            column=2,
            padx=10,
            pady=(10, 2),
            sticky="w"
        )

        self.gender_combo = ctk.CTkComboBox(
            filters_frame,
            values=[
                "Todos",
                "Female",
                "Male"
            ],
            command=lambda _: self._apply_voice_filters()
        )
        self.gender_combo.grid(
            row=1,
            column=2,
            padx=10,
            pady=(0, 10),
            sticky="ew"
        )
        self.gender_combo.set("Todos")

        self.search_entry = ctk.CTkEntry(
            self.voice_tab,
            placeholder_text=(
                "Buscar por nombre, idioma o identificador..."
            )
        )
        self.search_entry.grid(
            row=2,
            column=0,
            padx=15,
            pady=10,
            sticky="ew"
        )
        self.search_entry.bind(
            "<KeyRelease>",
            lambda _: self._apply_voice_filters()
        )

        ctk.CTkLabel(
            self.voice_tab,
            text="Voz seleccionada"
        ).grid(
            row=3,
            column=0,
            padx=15,
            pady=(5, 2),
            sticky="w"
        )

        self.voice_combo = ctk.CTkComboBox(
            self.voice_tab,
            values=["Cargando..."],
            command=self._on_voice_selected
        )
        self.voice_combo.grid(
            row=4,
            column=0,
            padx=15,
            pady=(0, 10),
            sticky="new"
        )

        controls = ctk.CTkFrame(
            self.voice_tab
        )
        controls.grid(
            row=5,
            column=0,
            padx=15,
            pady=15,
            sticky="ew"
        )

        controls.grid_columnconfigure(0, weight=1)
        controls.grid_columnconfigure(1, weight=1)

        self.test_voice_button = ctk.CTkButton(
            controls,
            text="Probar voz",
            command=self._test_voice,
            state="disabled"
        )
        self.test_voice_button.grid(
            row=0,
            column=0,
            padx=10,
            pady=10,
            sticky="ew"
        )

        self.reload_button = ctk.CTkButton(
            controls,
            text="Recargar catálogo",
            command=lambda: self._load_voice_catalog(
                force=True
            )
        )
        self.reload_button.grid(
            row=0,
            column=1,
            padx=10,
            pady=10,
            sticky="ew"
        )

        self.random_voice_switch = ctk.CTkSwitch(
            controls,
            text="Usar una voz aleatoria con estos filtros",
            command=self._change_random_voice
        )
        self.random_voice_switch.grid(
            row=1,
            column=0,
            columnspan=2,
            padx=10,
            pady=(4, 4),
            sticky="w"
        )

        ctk.CTkLabel(
            controls,
            text=(
                "La voz cambiará en cada comentario según el idioma, "
                "región y género seleccionados arriba."
            ),
            text_color=("gray35", "gray70"),
            wraplength=650,
            justify="left"
        ).grid(
            row=2,
            column=0,
            columnspan=2,
            padx=38,
            pady=(0, 10),
            sticky="w"
        )

        if self.config.get("random_voice", False):
            self.random_voice_switch.select()
        else:
            self.random_voice_switch.deselect()

    def _load_voice_catalog(
        self,
        force: bool = False
    ):
        self.voice_status.configure(
            text="Cargando catálogo de voces..."
        )

        self.reload_button.configure(
            state="disabled"
        )

        thread = threading.Thread(
            target=self._voice_loader_worker,
            args=(force,),
            daemon=True
        )
        thread.start()

    def _voice_loader_worker(
        self,
        force: bool
    ):
        voices = self.voice_catalog.load(
            force=force
        )

        self.after(
            0,
            lambda: self._finish_voice_loading(
                voices
            )
        )

    def _finish_voice_loading(
        self,
        voices: list[Voice]
    ):
        languages = self.voice_catalog.get_languages()

        self.language_combo.configure(
            values=languages
        )

        saved_language = self.config.get(
            "random_voice_language",
            "es"
        )
        if saved_language in languages:
            self.language_combo.set(saved_language)
        elif "es" in languages:
            self.language_combo.set("es")
        else:
            self.language_combo.set("Todos")

        self._update_locale_values()

        saved_locale = self.config.get(
            "random_voice_locale",
            "Todos"
        )
        locale_values = self.voice_catalog.get_locales(
            language=self.language_combo.get()
        )
        if saved_locale in locale_values:
            self.locale_combo.set(saved_locale)

        saved_gender = self.config.get(
            "random_voice_gender",
            "Todos"
        )
        if saved_gender in ("Todos", "Female", "Male"):
            self.gender_combo.set(saved_gender)

        self._apply_voice_filters()

        self.voice_status.configure(
            text=f"{len(voices)} voces disponibles."
        )

        self.reload_button.configure(
            state="normal"
        )
        self.test_voice_button.configure(
            state="normal"
        )

    def _on_language_change(
        self,
        _selected: str
    ):
        self._update_locale_values()
        self._apply_voice_filters()

    def _update_locale_values(self):
        language = self.language_combo.get()

        locales = self.voice_catalog.get_locales(
            language=language
        )

        self.locale_combo.configure(
            values=locales
        )

        current_locale = self.locale_combo.get()

        if current_locale not in locales:
            if "es-MX" in locales:
                self.locale_combo.set("es-MX")
            else:
                self.locale_combo.set("Todos")

    def _apply_voice_filters(self):
        language = self.language_combo.get()
        locale = self.locale_combo.get()
        gender = self.gender_combo.get()
        search = self.search_entry.get()

        if self.config.get("random_voice", False):
            self._save_random_voice_filters(
                language=language,
                locale=locale,
                gender=gender
            )

        self.filtered_voices = self.voice_catalog.filter(
            language=language,
            locale=locale,
            gender=gender,
            search=search
        )

        labels = [
            voice.label
            for voice in self.filtered_voices
        ]

        if not labels:
            self.voice_combo.configure(
                values=["No se encontraron voces"]
            )
            self.voice_combo.set(
                "No se encontraron voces"
            )
            self.test_voice_button.configure(
                state="disabled"
            )
            return

        self.voice_combo.configure(
            values=labels
        )

        current_voice_id = self.config.get(
            "voice",
            "es-MX-DaliaNeural"
        )

        current_voice = self.voice_catalog.get_by_id(
            current_voice_id
        )

        if (
            current_voice is not None
            and current_voice.label in labels
        ):
            self.voice_combo.set(
                current_voice.label
            )
        else:
            self.voice_combo.set(
                labels[0]
            )

        self.test_voice_button.configure(
            state="normal"
        )

    def _on_voice_selected(
        self,
        selected_label: str
    ):
        voice = self.voice_catalog.get_by_label(
            selected_label
        )

        if voice is None:
            return

        self.config.set(
            "voice",
            voice.short_name
        )

        self.tts.set_voice(
            voice.short_name
        )

        self.voice_status.configure(
            text=(
                f"Voz activa: {voice.display_name} "
                f"({voice.locale})"
            )
        )

    def _test_voice(self):
        selected_label = self.voice_combo.get()

        voice = self.voice_catalog.get_by_label(
            selected_label
        )

        if voice is None:
            return

        self.config.set(
            "voice",
            voice.short_name
        )

        self.tts.set_voice(
            voice.short_name
        )

        self.tts.speak(
            (
                "Hola Marco. Esta es una prueba "
                f"de la voz {voice.display_name} "
                "en LiveVoice Studio."
            )
        )

    def _change_random_voice(self):
        enabled = bool(self.random_voice_switch.get())
        self.config.set("random_voice", enabled)

        if enabled:
            self._save_random_voice_filters(
                language=self.language_combo.get(),
                locale=self.locale_combo.get(),
                gender=self.gender_combo.get()
            )
            self.voice_status.configure(
                text=(
                    f"Voz aleatoria activa: "
                    f"{len(self.filtered_voices)} voces disponibles."
                )
            )
        else:
            selected = self.voice_catalog.get_by_label(
                self.voice_combo.get()
            )
            if selected is not None:
                self.tts.set_voice(selected.short_name)
            self.voice_status.configure(
                text="Voz aleatoria desactivada."
            )

    def _save_random_voice_filters(
        self,
        language: str,
        locale: str,
        gender: str
    ):
        self.config.set("random_voice_language", language)
        self.config.set("random_voice_locale", locale)
        self.config.set("random_voice_gender", gender)

    # ─────────────────────────────────────
    # LECTURA Y FILTROS
    # ─────────────────────────────────────

    def _build_reading_tab(self):
        self.reading_tab.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            self.reading_tab,
            text="Preferencias de lectura",
            font=("Segoe UI", 18, "bold")
        )
        title.grid(
            row=0,
            column=0,
            padx=20,
            pady=(20, 6),
            sticky="w"
        )

        description = ctk.CTkLabel(
            self.reading_tab,
            text=(
                "Estas opciones se aplican por igual a TikTok y Twitch."
            ),
            text_color=("gray35", "gray70")
        )
        description.grid(
            row=1,
            column=0,
            padx=20,
            pady=(0, 15),
            sticky="w"
        )

        options = ctk.CTkFrame(self.reading_tab)
        options.grid(
            row=2,
            column=0,
            padx=20,
            pady=5,
            sticky="ew"
        )
        options.grid_columnconfigure(0, weight=1)

        self.read_username_switch = ctk.CTkSwitch(
            options,
            text="Decir el nombre del usuario antes del comentario",
            command=self._change_read_username
        )
        self.read_username_switch.grid(
            row=0,
            column=0,
            padx=18,
            pady=(18, 6),
            sticky="w"
        )

        ctk.CTkLabel(
            options,
            text=(
                'Activado: "Marco dice: hola".  '
                'Desactivado: "hola".'
            ),
            text_color=("gray35", "gray70")
        ).grid(
            row=1,
            column=0,
            padx=50,
            pady=(0, 18),
            sticky="w"
        )

        self.emoji_spam_switch = ctk.CTkSwitch(
            options,
            text="Bloquear spam de emojis",
            command=self._change_emoji_spam_filter
        )
        self.emoji_spam_switch.grid(
            row=2,
            column=0,
            padx=18,
            pady=(10, 6),
            sticky="w"
        )

        ctk.CTkLabel(
            options,
            text=(
                "Oculta mensajes llenos de emojis repetidos, pero permite "
                "emojis normales acompañados de texto."
            ),
            text_color=("gray35", "gray70"),
            wraplength=650,
            justify="left"
        ).grid(
            row=3,
            column=0,
            padx=50,
            pady=(0, 18),
            sticky="w"
        )

        if self.config.get("read_username", True):
            self.read_username_switch.select()
        else:
            self.read_username_switch.deselect()

        self.ascii_art_switch = ctk.CTkSwitch(
            options,
            text="Bloquear ASCII art y dibujos con símbolos",
            command=self._change_ascii_art_filter
        )
        self.ascii_art_switch.grid(
            row=4,
            column=0,
            padx=18,
            pady=(10, 6),
            sticky="w"
        )

        ctk.CTkLabel(
            options,
            text=(
                "Oculta dibujos creados con líneas, bloques, caracteres "
                "braille y otros símbolos, sin bloquear puntuación normal."
            ),
            text_color=("gray35", "gray70"),
            wraplength=650,
            justify="left"
        ).grid(
            row=5,
            column=0,
            padx=50,
            pady=(0, 18),
            sticky="w"
        )

        if self.config.get("filter_emoji_spam", True):
            self.emoji_spam_switch.select()
        else:
            self.emoji_spam_switch.deselect()

        if self.config.get("filter_ascii_art", True):
            self.ascii_art_switch.select()
        else:
            self.ascii_art_switch.deselect()

    def _change_read_username(self):
        self.config.set(
            "read_username",
            bool(self.read_username_switch.get())
        )

    def _change_emoji_spam_filter(self):
        self.config.set(
            "filter_emoji_spam",
            bool(self.emoji_spam_switch.get())
        )

    def _change_ascii_art_filter(self):
        self.config.set(
            "filter_ascii_art",
            bool(self.ascii_art_switch.get())
        )

    # ─────────────────────────────────────
    # PALABRAS BLOQUEADAS
    # ─────────────────────────────────────

    def _build_words_tab(self):
        self.words_tab.grid_columnconfigure(
            0,
            weight=1
        )
        self.words_tab.grid_rowconfigure(
            3,
            weight=1
        )

        input_frame = ctk.CTkFrame(
            self.words_tab
        )
        input_frame.grid(
            row=0,
            column=0,
            padx=15,
            pady=(15, 8),
            sticky="ew"
        )
        input_frame.grid_columnconfigure(
            0,
            weight=1
        )

        self.blocked_word_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text=(
                "Escribe una palabra o frase..."
            )
        )
        self.blocked_word_entry.grid(
            row=0,
            column=0,
            padx=10,
            pady=10,
            sticky="ew"
        )
        self.blocked_word_entry.bind(
            "<Return>",
            lambda _: self._add_blocked_word()
        )

        add_button = ctk.CTkButton(
            input_frame,
            text="Agregar",
            width=110,
            command=self._add_blocked_word
        )
        add_button.grid(
            row=0,
            column=1,
            padx=(0, 10),
            pady=10
        )

        mode_frame = ctk.CTkFrame(
            self.words_tab
        )
        mode_frame.grid(
            row=1,
            column=0,
            padx=15,
            pady=8,
            sticky="ew"
        )

        ctk.CTkLabel(
            mode_frame,
            text="Cuando aparezca una palabra bloqueada:"
        ).pack(
            side="left",
            padx=10,
            pady=10
        )

        current_mode = self.config.get(
            "blocked_words_mode",
            "replace"
        )

        self.mode_combo = ctk.CTkComboBox(
            mode_frame,
            values=list(MODE_LABELS.keys()),
            command=self._change_blocked_mode,
            width=220
        )
        self.mode_combo.pack(
            side="right",
            padx=10,
            pady=10
        )
        self.mode_combo.set(
            MODE_VALUES.get(
                current_mode,
                "Reemplazar por ***"
            )
        )

        ctk.CTkLabel(
            self.words_tab,
            text="Palabras y frases bloqueadas"
        ).grid(
            row=2,
            column=0,
            padx=15,
            pady=(10, 4),
            sticky="w"
        )

        self.words_list = ctk.CTkScrollableFrame(
            self.words_tab
        )
        self.words_list.grid(
            row=3,
            column=0,
            padx=15,
            pady=(0, 10),
            sticky="nsew"
        )
        self.words_list.grid_columnconfigure(
            0,
            weight=1
        )

        clear_button = ctk.CTkButton(
            self.words_tab,
            text="Eliminar todas",
            fg_color="#8b2f35",
            hover_color="#a63a42",
            command=self._clear_blocked_words
        )
        clear_button.grid(
            row=4,
            column=0,
            padx=15,
            pady=(5, 15),
            sticky="e"
        )

    def _load_blocked_words(self):
        for widget in self.words_list.winfo_children():
            widget.destroy()

        words = self.blocked_words.get_all()

        if not words:
            ctk.CTkLabel(
                self.words_list,
                text="No hay palabras bloqueadas."
            ).grid(
                row=0,
                column=0,
                padx=10,
                pady=15,
                sticky="w"
            )
            return

        for index, word in enumerate(words):
            row = ctk.CTkFrame(
                self.words_list
            )
            row.grid(
                row=index,
                column=0,
                padx=5,
                pady=4,
                sticky="ew"
            )
            row.grid_columnconfigure(
                0,
                weight=1
            )

            label = ctk.CTkLabel(
                row,
                text=word,
                anchor="w"
            )
            label.grid(
                row=0,
                column=0,
                padx=10,
                pady=8,
                sticky="ew"
            )

            remove_button = ctk.CTkButton(
                row,
                text="Eliminar",
                width=90,
                command=lambda selected_word=word: (
                    self._remove_blocked_word(
                        selected_word
                    )
                )
            )
            remove_button.grid(
                row=0,
                column=1,
                padx=8,
                pady=6
            )

    def _add_blocked_word(self):
        word = self.blocked_word_entry.get()

        if self.blocked_words.add(word):
            self.blocked_word_entry.delete(
                0,
                "end"
            )
            self._load_blocked_words()

    def _remove_blocked_word(
        self,
        word: str
    ):
        if self.blocked_words.remove(word):
            self._load_blocked_words()

    def _clear_blocked_words(self):
        self.blocked_words.clear()
        self._load_blocked_words()

    def _change_blocked_mode(
        self,
        selected_label: str
    ):
        mode = MODE_LABELS[selected_label]

        self.blocked_words.set_mode(
            mode
        )