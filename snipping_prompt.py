import customtkinter as ctk
import ctypes
import winsound

try:
    from ai_metrics_engine import AIEngine
except ImportError:
    AIEngine = None


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

        # KI-Engine für die Fehler-Rückmeldung laden
        self.ai_engine = AIEngine() if AIEngine else None

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

        # --- UI Layout ---
        self.lbl_title = ctk.CTkLabel(self, text=f"Rune '{rune_name.upper()}' bereit!\nIcon jetzt ausschneiden?",
                                      font=("Roboto", 13, "bold"), text_color="#FFD700")
        self.lbl_title.pack(pady=(15, 10), padx=20)

        # 1. Standard Button Frame (Ja, Später, Falsch)
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=10, pady=(0, 15))

        # Button für JA (Startet das Vollbild-Tool)
        self.btn_yes = ctk.CTkButton(self.btn_frame, text="✂️ Ja", width=55, height=28,
                                     fg_color="#2da44e", hover_color="#238636", command=self.click_yes)
        self.btn_yes.pack(side="left", padx=3, expand=True)

        # Button für NEIN/Später (Bricht den Vorgang ab und leitet an Dropdown im Overlay weiter)
        self.btn_no = ctk.CTkButton(self.btn_frame, text="🕒 Später", width=65, height=28,
                                    fg_color="#1f538d", hover_color="#1a4577", command=self.click_no)
        self.btn_no.pack(side="left", padx=3, expand=True)

        # INNOVATION: Button für die Falschmeldung direkt im aktiven Prompt
        self.btn_false = ctk.CTkButton(self.btn_frame, text="⚠️ Falsch", width=65, height=28,
                                       fg_color="#8B0000", hover_color="#5A0000", command=self.show_fp_options)
        self.btn_false.pack(side="left", padx=3, expand=True)

        # 2. Options Frame für Falschmeldung (Versteckt bis zum Klick auf "Falsch")
        self.fp_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=6)
        self.fp_var = ctk.StringVar(value="Grund wählen...")
        self.fp_dropdown = ctk.CTkOptionMenu(self.fp_frame, variable=self.fp_var,
                                             values=["Nichts gedroppt", "Falsches Item", "Chat/Text gelesen",
                                                     "Abbrechen"],
                                             width=150, height=24, font=("Roboto", 11),
                                             command=self.submit_fp)
        self.fp_dropdown.pack(pady=5, padx=10)

        # Positionierung rechts vom Haupt-Overlay starten und Ghosting anwenden
        self.after(10, self._position_relative_to_parent)
        self.after(100, self.apply_stealth_mode)

    def show_fp_options(self):
        """Versteckt die normalen Buttons und zeigt das Feedback-Dropdown für die KI."""
        self.btn_frame.pack_forget()
        self.lbl_title.configure(text=f"Warum Falschmeldung\nfür {self.rune_name.upper()}?")
        self.fp_frame.pack(fill="x", padx=10, pady=(0, 15))

    def submit_fp(self, reason):
        """Sendet die Falschmeldung an die KI und schließt das Popup restlos."""
        if reason == "Abbrechen":
            # Zurück zur normalen 3-Button Ansicht
            self.fp_frame.pack_forget()
            self.lbl_title.configure(text=f"Rune '{self.rune_name.upper()}' bereit!\nIcon jetzt ausschneiden?")
            self.btn_frame.pack(fill="x", padx=10, pady=(0, 15))
            self.fp_var.set("Grund wählen...")
            return

        if self.ai_engine:
            # KI Engine mit der Falschmeldung füttern
            self.ai_engine.report_false_positive(self.rune_name, 0.85)
            winsound.Beep(500, 150)

            # Direktes visuelles Feedback im Haupt-Overlay, sofern vorhanden
            if hasattr(self.parent_overlay, 'lbl_live_loot'):
                try:
                    msg = f"KI lernt: {self.rune_name} ignoriert"
                    if reason == "Chat/Text gelesen":
                        msg = f"KI: Chat-Filter für {self.rune_name} anpassen"
                    elif reason == "Falsches Item":
                        msg = f"KI: Form-Scan für {self.rune_name} korrigieren"

                    self.parent_overlay.lbl_live_loot.configure(text=msg, text_color="#ffaa00")
                except Exception:
                    pass

        # Dem Scanner mitteilen, dass der Drop verworfen wurde.
        # WICHTIG: Das Item darf bei Falschmeldung NICHT an das "Später"-Dropdown im Overlay gesendet werden!
        if self.on_no_callback:
            self.on_no_callback(self.rune_name)

        self.destroy()

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
        """Verhindert, dass das Fenster auf Screenshots oder in Stream-Captures auftaucht (OBS/Discord)."""
        try:
            hwnd = int(self.wm_frame(), 16)
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x0011)
        except Exception:
            pass

    def click_yes(self):
        """Nutzer will das Icon sofort ausschneiden."""
        if self.on_yes_callback:
            self.on_yes_callback(self.rune_name)
        self.destroy()

    def click_no(self):
        """Nutzer hat den Drop gesehen, will ihn aber später ausschneiden."""
        # 1. Melde dem Scanner, dass das Live-Popup beendet ist.
        if self.on_no_callback:
            self.on_no_callback(self.rune_name)

        # 2. Leite die Rune zwingend an das "Später"-Dropdown im Haupt-Overlay weiter.
        if hasattr(self, 'parent_overlay') and hasattr(self.parent_overlay, 'add_pending_rune'):
            # Hier greift die Logik aus der PendingRunesMixin
            self.parent_overlay.add_pending_rune(self.rune_name)

        self.destroy()