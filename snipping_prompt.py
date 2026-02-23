import customtkinter as ctk
import ctypes


class SnippingPrompt(ctk.CTkToplevel):
    def __init__(self, parent, rune_name, on_yes_callback, on_no_callback):
        """
        Ein kleines, unaufdringliches Popup, das abfragt, ob das Vollbild-Snipping-Tool
        jetzt gestartet werden darf (um Störungen in Kämpfen zu vermeiden).
        Haftet rechts am Haupt-Overlay.
        """
        super().__init__(parent)

        # Speichere die explizite Referenz auf das Haupt-Overlay (RunTrackerOverlay)
        self.parent_overlay = parent
        self.rune_name = rune_name
        self.on_yes_callback = on_yes_callback
        self.on_no_callback = on_no_callback

        # Fenster als reines Overlay konfigurieren
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        # Übernehme Transparenz vom Haupt-Overlay
        if hasattr(parent, 'attributes'):
            try:
                alpha = parent.attributes("-alpha")
                self.attributes("-alpha", alpha)
            except:
                pass

        self.configure(fg_color="#1a1a1a", border_width=2, border_color="#FFD700")

        # UI Layout
        lbl_title = ctk.CTkLabel(self, text=f"Rune '{rune_name.upper()}' bereit!\nIcon jetzt ausschneiden?",
                                 font=("Roboto", 13, "bold"), text_color="#FFD700")
        lbl_title.pack(pady=(15, 10), padx=20)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(0, 15))

        # Button für JA (Startet das Vollbild-Tool)
        btn_yes = ctk.CTkButton(btn_frame, text="✂️ Ja", width=70,
                                fg_color="#2da44e", hover_color="#238636", command=self.click_yes)
        btn_yes.pack(side="left", padx=5, expand=True)

        # Button für NEIN/Später (Bricht den Vorgang ab und leitet an Dropdown weiter)
        btn_no = ctk.CTkButton(btn_frame, text="🕒 Später", width=70,
                               fg_color="#1f538d", hover_color="#1a4577", command=self.click_no)
        btn_no.pack(side="right", padx=5, expand=True)

        # Positionierung rechts vom Haupt-Overlay starten und Ghosting anwenden
        self.after(10, self._position_relative_to_parent)
        self.after(100, self.apply_stealth_mode)

    def _position_relative_to_parent(self):
        """Platziert das Popup exakt rechts neben dem Parent-Fenster und klebt daran fest."""
        try:
            # Nutze die explizite Referenz auf das Haupt-Overlay
            if self.winfo_exists() and hasattr(self, 'parent_overlay') and self.parent_overlay.winfo_exists():
                px = self.parent_overlay.winfo_x()
                py = self.parent_overlay.winfo_y()
                pw = self.parent_overlay.winfo_width()

                # 5 Pixel Abstand zum Haupt-Overlay
                target_x = px + pw + 5
                target_y = py

                self.geometry(f"+{target_x}+{target_y}")

                # Endlosschleife, damit das Popup wie magnetisch am Haupt-Overlay klebt,
                # falls das Haupt-Overlay mit der Maus verschoben wird.
                self.after(20, self._position_relative_to_parent)
        except Exception:
            pass

    def apply_stealth_mode(self):
        try:
            hwnd = int(self.wm_frame(), 16)
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x0011)
        except:
            pass

    def click_yes(self):
        if self.on_yes_callback:
            self.on_yes_callback(self.rune_name)
        self.destroy()

    def click_no(self):
        # 1. Melde dem Scanner, dass der Vorgang abgebrochen wurde
        if self.on_no_callback:
            self.on_no_callback(self.rune_name)

        # 2. Leite die Rune an das "Später"-Dropdown im Haupt-Overlay weiter
        if hasattr(self, 'parent_overlay') and hasattr(self.parent_overlay, 'add_pending_rune'):
            self.parent_overlay.add_pending_rune(self.rune_name)

        self.destroy()