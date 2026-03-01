import customtkinter as ctk


class PopupManagerWindow(ctk.CTkToplevel):
    """
    Verwaltet alle Items/Runen, bei denen der Nutzer angeklickt hat,
    dass sie in Zukunft automatisch akzeptiert (nicht mehr gefragt) werden sollen.
    """

    def __init__(self, parent_widget, config_data, on_close_callback=None):
        super().__init__(parent_widget)

        self.config_data = config_data
        self.on_close_callback = on_close_callback
        self.checkboxes = {}

        self.title("Stummgeschaltete Pop-ups")
        self.geometry("400x450")
        self.attributes('-topmost', True)
        self.grab_set()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        self.setup_ui()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 10))

        ctk.CTkLabel(
            header_frame,
            text="Automatisch akzeptierte Items",
            font=("Roboto", 18, "bold"),
            text_color="#8B008B"
        ).pack(anchor="w")

        ctk.CTkLabel(
            header_frame,
            text="Entferne den Haken, wenn du bei diesen Items wieder\nein Bestätigungs-Popup der KI sehen möchtest.",
            font=("Roboto", 12),
            text_color="#aaaaaa",
            justify="left"
        ).pack(anchor="w", pady=(5, 0))

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="#1a1a1a", corner_radius=8)
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=5)

        self.refresh_item_list()

        btn_close = ctk.CTkButton(
            self, text="Speichern & Schließen", command=self._on_closing,
            fg_color="#333333", hover_color="#444444"
        )
        btn_close.grid(row=2, column=0, pady=15)

    def refresh_item_list(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        self.checkboxes.clear()

        # Liste der stummgeschalteten Items aus der Config holen
        hidden_items = self.config_data.get("auto_verify", [])

        if not hidden_items:
            ctk.CTkLabel(
                self.scroll_frame,
                text="Es sind aktuell keine Pop-ups stummgeschaltet.",
                text_color="#aaaaaa"
            ).pack(pady=20)
            return

        for item_name in hidden_items:
            var = ctk.BooleanVar(value=True)  # Standardmäßig an, weil sie in der Liste stehen

            cb = ctk.CTkCheckBox(
                self.scroll_frame,
                text=item_name.title(),
                variable=var,
                command=lambda name=item_name, v=var: self._on_checkbox_toggle(name, v)
            )
            cb.pack(anchor="w", padx=10, pady=8)
            self.checkboxes[item_name] = var

    def _on_checkbox_toggle(self, item_name, var):
        """Entfernt oder fügt das Item dynamisch zur Liste hinzu."""
        hidden_list = self.config_data.get("auto_verify", [])

        if var.get() and item_name not in hidden_list:
            hidden_list.append(item_name)
        elif not var.get() and item_name in hidden_list:
            hidden_list.remove(item_name)

        self.config_data["auto_verify"] = hidden_list

    def _on_closing(self):
        if self.on_close_callback:
            self.on_close_callback(self.config_data)
        self.destroy()