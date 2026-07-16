import shutil
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.paths import data_path
from models.command import Command
from services.plugins.command_service import CommandService


class CommandsWindow(ctk.CTkToplevel):
    def __init__(self, parent, container):
        super().__init__(parent)
        self.container = container
        self.service = container.get(CommandService)
        self.selected_name: str | None = None
        self.sound_source = ""

        self.title("Comandos personalizados")
        self.geometry("900x610")
        self.minsize(820, 560)
        self.transient(parent)

        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        title = ctk.CTkLabel(
            self,
            text="Comandos personalizados",
            font=("Segoe UI", 24, "bold"),
        )
        title.grid(row=0, column=0, columnspan=2, padx=24, pady=(20, 14), sticky="w")

        self.list_frame = ctk.CTkFrame(self)
        self.list_frame.grid(row=1, column=0, padx=(20, 10), pady=(0, 20), sticky="nsew")
        self.list_frame.grid_columnconfigure(0, weight=1)
        self.list_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self.list_frame,
            text="Comandos",
            font=("Segoe UI", 17, "bold"),
        ).grid(row=0, column=0, padx=14, pady=14, sticky="w")

        self.command_list = ctk.CTkScrollableFrame(self.list_frame)
        self.command_list.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.command_list.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            self.list_frame,
            text="+ Nuevo comando",
            command=self._new_command,
        ).grid(row=2, column=0, padx=12, pady=(2, 12), sticky="ew")

        form = ctk.CTkFrame(self)
        form.grid(row=1, column=1, padx=(10, 20), pady=(0, 20), sticky="nsew")
        form.grid_columnconfigure(1, weight=1)

        row = 0
        ctk.CTkLabel(form, text="Nombre", font=("Segoe UI", 13, "bold")).grid(
            row=row, column=0, padx=(18, 10), pady=(20, 8), sticky="w"
        )
        self.name_entry = ctk.CTkEntry(form, placeholder_text="!susto")
        self.name_entry.grid(row=row, column=1, padx=(0, 18), pady=(20, 8), sticky="ew")

        row += 1
        ctk.CTkLabel(form, text="Sonido", font=("Segoe UI", 13, "bold")).grid(
            row=row, column=0, padx=(18, 10), pady=8, sticky="w"
        )
        sound_row = ctk.CTkFrame(form, fg_color="transparent")
        sound_row.grid(row=row, column=1, padx=(0, 18), pady=8, sticky="ew")
        sound_row.grid_columnconfigure(0, weight=1)
        self.sound_label = ctk.CTkLabel(
            sound_row,
            text="Ningún archivo seleccionado",
            anchor="w",
            text_color="#a8a8a8",
        )
        self.sound_label.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        ctk.CTkButton(
            sound_row,
            text="Elegir",
            width=85,
            command=self._choose_sound,
        ).grid(row=0, column=1)

        row += 1
        ctk.CTkLabel(form, text="Cooldown", font=("Segoe UI", 13, "bold")).grid(
            row=row, column=0, padx=(18, 10), pady=8, sticky="w"
        )
        cooldown_row = ctk.CTkFrame(form, fg_color="transparent")
        cooldown_row.grid(row=row, column=1, padx=(0, 18), pady=8, sticky="ew")
        cooldown_row.grid_columnconfigure(0, weight=1)
        self.cooldown_slider = ctk.CTkSlider(
            cooldown_row,
            from_=0,
            to=300,
            number_of_steps=300,
            command=self._update_cooldown_label,
        )
        self.cooldown_slider.grid(row=0, column=0, sticky="ew")
        self.cooldown_label = ctk.CTkLabel(cooldown_row, text="30 s", width=55)
        self.cooldown_label.grid(row=0, column=1, padx=(10, 0))

        row += 1
        ctk.CTkLabel(form, text="Permisos", font=("Segoe UI", 13, "bold")).grid(
            row=row, column=0, padx=(18, 10), pady=8, sticky="w"
        )
        self.permission_menu = ctk.CTkOptionMenu(
            form,
            values=["Todos", "Usuarios permitidos"],
            command=self._permission_changed,
        )
        self.permission_menu.grid(row=row, column=1, padx=(0, 18), pady=8, sticky="ew")

        row += 1
        self.allowed_label = ctk.CTkLabel(
            form,
            text="Usuarios",
            font=("Segoe UI", 13, "bold"),
        )
        self.allowed_label.grid(row=row, column=0, padx=(18, 10), pady=8, sticky="w")
        self.allowed_entry = ctk.CTkEntry(
            form,
            placeholder_text="usuario1, usuario2",
        )
        self.allowed_entry.grid(row=row, column=1, padx=(0, 18), pady=8, sticky="ew")

        row += 1
        self.enabled_switch = ctk.CTkSwitch(form, text="Comando activado")
        self.enabled_switch.grid(row=row, column=1, padx=(0, 18), pady=(12, 8), sticky="w")

        row += 1
        help_text = (
            "El cooldown se aplica por usuario. Los comandos no serán leídos por el TTS. "
            "Formatos compatibles: MP3, WAV y OGG."
        )
        ctk.CTkLabel(
            form,
            text=help_text,
            wraplength=480,
            justify="left",
            text_color="#999999",
        ).grid(row=row, column=0, columnspan=2, padx=18, pady=(10, 16), sticky="w")

        row += 1
        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=row, column=0, columnspan=2, padx=18, pady=(8, 18), sticky="ew")
        buttons.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(buttons, text="Guardar", command=self._save).grid(
            row=0, column=0, padx=(0, 6), sticky="ew"
        )
        ctk.CTkButton(buttons, text="Probar", command=self._test).grid(
            row=0, column=1, padx=6, sticky="ew"
        )
        ctk.CTkButton(
            buttons,
            text="Eliminar",
            fg_color="#9e3131",
            hover_color="#7c2626",
            command=self._delete,
        ).grid(row=0, column=2, padx=(6, 0), sticky="ew")

        self._new_command()

    def _refresh_list(self):
        for child in self.command_list.winfo_children():
            child.destroy()

        commands = self.service.list_commands()
        if not commands:
            ctk.CTkLabel(
                self.command_list,
                text="Todavía no hay comandos.",
                text_color="#999999",
            ).grid(row=0, column=0, padx=8, pady=12)
            return

        for row, command in enumerate(commands):
            state = "●" if command.enabled else "○"
            button = ctk.CTkButton(
                self.command_list,
                text=f"{state}  {command.name}",
                anchor="w",
                command=lambda name=command.name: self._load_command(name),
            )
            button.grid(row=row, column=0, padx=4, pady=4, sticky="ew")

    def _new_command(self):
        self.selected_name = None
        self.sound_source = ""
        self.name_entry.delete(0, "end")
        self.sound_label.configure(text="Ningún archivo seleccionado")
        self.cooldown_slider.set(30)
        self._update_cooldown_label(30)
        self.permission_menu.set("Todos")
        self.allowed_entry.delete(0, "end")
        self.enabled_switch.select()
        self._permission_changed("Todos")

    def _load_command(self, name: str):
        command = self.service.get(name)
        if command is None:
            return

        self.selected_name = command.name
        self.sound_source = command.sound_path
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, command.name)
        self.sound_label.configure(text=Path(command.sound_path).name)
        self.cooldown_slider.set(command.cooldown_seconds)
        self._update_cooldown_label(command.cooldown_seconds)
        permission = "Todos" if command.permission == "everyone" else "Usuarios permitidos"
        self.permission_menu.set(permission)
        self.allowed_entry.delete(0, "end")
        self.allowed_entry.insert(0, ", ".join(command.allowed_users))
        self.enabled_switch.select() if command.enabled else self.enabled_switch.deselect()
        self._permission_changed(permission)

    def _choose_sound(self):
        filename = filedialog.askopenfilename(
            parent=self,
            title="Seleccionar sonido",
            filetypes=[
                ("Archivos de audio", "*.mp3 *.wav *.ogg"),
                ("MP3", "*.mp3"),
                ("WAV", "*.wav"),
                ("OGG", "*.ogg"),
            ],
        )
        if filename:
            self.sound_source = filename
            self.sound_label.configure(text=Path(filename).name)

    def _save(self):
        try:
            name = Command.normalize_name(self.name_entry.get())
            if name == "!":
                raise ValueError("Escribe un nombre, por ejemplo !susto.")
            if not self.sound_source:
                raise ValueError("Selecciona un archivo de sonido.")

            stored_sound = self._store_sound(name, self.sound_source)
            permission = (
                "everyone"
                if self.permission_menu.get() == "Todos"
                else "allowlist"
            )
            allowed_users = [
                item.strip()
                for item in self.allowed_entry.get().split(",")
                if item.strip()
            ]
            if permission == "allowlist" and not allowed_users:
                raise ValueError("Agrega al menos un usuario permitido.")

            command = Command(
                name=name,
                sound_path=str(stored_sound),
                enabled=bool(self.enabled_switch.get()),
                cooldown_seconds=int(self.cooldown_slider.get()),
                permission=permission,
                allowed_users=allowed_users,
            )
            self.service.save(command, previous_name=self.selected_name)
            self.selected_name = command.name
            self.sound_source = command.sound_path
            self._refresh_list()
            messagebox.showinfo("LiveVoice Studio", f"{command.name} guardado correctamente.", parent=self)
        except Exception as error:
            messagebox.showerror("No se pudo guardar", str(error), parent=self)

    def _test(self):
        try:
            if self.selected_name:
                self.service.test(self.selected_name)
            elif self.sound_source:
                self.service.sound_action.execute(self.sound_source)
            else:
                raise ValueError("Selecciona un sonido primero.")
        except Exception as error:
            messagebox.showerror("No se pudo reproducir", str(error), parent=self)

    def _delete(self):
        if not self.selected_name:
            return
        confirmed = messagebox.askyesno(
            "Eliminar comando",
            f"¿Eliminar {self.selected_name}?",
            parent=self,
        )
        if not confirmed:
            return
        self.service.delete(self.selected_name)
        self._refresh_list()
        self._new_command()

    def _store_sound(self, command_name: str, source: str) -> Path:
        source_path = Path(source).resolve()
        if not source_path.is_file():
            raise FileNotFoundError("El archivo seleccionado ya no existe.")

        sounds_dir = data_path("sounds", "commands")
        sounds_dir.mkdir(parents=True, exist_ok=True)
        safe_name = command_name.lstrip("!").replace(" ", "_") or "command"
        destination = sounds_dir / f"{safe_name}{source_path.suffix.lower()}"

        if source_path != destination.resolve():
            shutil.copy2(source_path, destination)
        return destination

    def _update_cooldown_label(self, value):
        self.cooldown_label.configure(text=f"{int(float(value))} s")

    def _permission_changed(self, value: str):
        state = "normal" if value == "Usuarios permitidos" else "disabled"
        self.allowed_entry.configure(state=state)
