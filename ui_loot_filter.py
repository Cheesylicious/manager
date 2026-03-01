import tkinter as tk
from tkinter import ttk


class LootFilterMenu(ttk.Frame):
    """
    Ein eigenständiges UI-Modul für "Overlay & Tracker", das alle angelernten
    Items auflistet und Kontrollkästchen zum (De-)Aktivieren des Auto-Loots bietet.
    """

    def __init__(self, parent_widget, db_manager):
        super().__init__(parent_widget)
        self.db_manager = db_manager
        self.checkboxes = {}
        self.setup_ui()

    def setup_ui(self):
        # Header
        header = ttk.Label(
            self,
            text="Angelernte Items (Loot-Filter)",
            font=("Arial", 12, "bold")
        )
        header.pack(pady=(10, 5), anchor="w")

        # Scrollbarer Bereich (optional, aber empfohlen für viele Items)
        self.canvas = tk.Canvas(self, height=200)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.refresh_item_list()

    def refresh_item_list(self):
        """Baut die Kontrollkästchen basierend auf dem aktuellen Datenbank-Cache neu auf."""
        # Alte Widgets entfernen (falls aktualisiert wird)
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        self.checkboxes.clear()

        # Aktuelle Items aus dem RAM-Cache holen
        items = self.db_manager._cache

        if not items:
            ttk.Label(self.scrollable_frame, text="Noch keine Items angelernt.").pack(pady=10)
            return

        for item_name, is_auto_loot in items.items():
            var = tk.BooleanVar(value=is_auto_loot)

            cb = ttk.Checkbutton(
                self.scrollable_frame,
                text=item_name,
                variable=var,
                command=lambda name=item_name, v=var: self._on_checkbox_toggle(name, v)
            )
            cb.pack(anchor="w", padx=5, pady=2)
            self.checkboxes[item_name] = var

    def _on_checkbox_toggle(self, item_name, var):
        """Speichert die Entscheidung des Nutzers direkt asynchron über den Manager."""
        new_status = var.get()
        self.db_manager.update_loot_status(item_name, new_status)