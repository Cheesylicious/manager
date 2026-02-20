import customtkinter as ctk
import ctypes

class SnippingPrompt(ctk.CTkToplevel):
    def __init__(self, parent, rune_name, on_yes_callback, on_no_callback):
        """
        Ein kleines, unaufdringliches Popup, das abfragt, ob das Vollbild-Snipping-Tool
        jetzt gestartet werden darf (um Störungen in Kämpfen zu vermeiden).
        """
        super().__init__(parent)
        self.rune_name = rune_name
        self.on_yes_callback = on_yes_callback
        self.on_no_callback = on_no_callback

        # Fenster als reines Overlay konfigurieren
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color="#1a1a1a", border_width=2, border_color="#FFD700")

        # UI Layout
        lbl_title = ctk.CTkLabel(self, text=f"Unbekannte Rune '{rune_name}'!\nTemplate jetzt ausschneiden?",
                                 font=("Roboto", 13, "bold"), text_color="#FFD700")
        lbl_title.pack(pady=(15, 10), padx=20)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(0, 15))

        # Button für JA (Startet das Vollbild-Tool)
        btn_yes = ctk.CTkButton(btn_frame, text="✂️ Ja", width=70,
                                fg_color="#2da44e", hover_color="#238636", command=self.click_yes)
        btn_yes.pack(side="left", padx=5, expand=True)

        # Button für NEIN (Bricht den Vorgang ab)
        btn_no = ctk.CTkButton(btn_frame, text="❌ Später", width=70,
                               fg_color="#cf222e", hover_color="#a40e26", command=self.click_no)
        btn_no.pack(side="right", padx=5, expand=True)

        # Position an der Maus
        self._position_at_mouse()

    def _position_at_mouse(self):
        """Setzt das Prompt leicht versetzt zur aktuellen Mausposition."""
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        self.geometry(f"+{pt.x + 20}+{pt.y + 20}")

    def click_yes(self):
        if self.on_yes_callback:
            self.on_yes_callback(self.rune_name)
        self.destroy()

    def click_no(self):
        if self.on_no_callback:
            self.on_no_callback(self.rune_name)
        self.destroy()