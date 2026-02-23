import customtkinter as ctk
import ctypes

class RuneFilterWindow(ctk.CTkToplevel):
    def __init__(self, parent, config_data, callback):
        super().__init__(parent)
        self.title("Individueller Runen-Filter")
        self.geometry("520x450")
        self.attributes('-topmost', True)
        self.config_data = config_data
        self.callback = callback

        # Zentrieren
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"+{(sw - 520) // 2}+{(sh - 450) // 2}")

        self.all_runes = [
            "El", "Eld", "Tir", "Nef", "Eth", "Ith", "Tal", "Ral", "Ort", "Thul", "Amn", "Sol", "Shael", "Dol", "Hel",
            "Io", "Lum", "Ko", "Fal", "Lem", "Pul", "Um", "Mal", "Ist", "Gul", "Vex", "Ohm", "Lo", "Sur", "Ber",
            "Jah", "Cham", "Zod"
        ]

        # Wenn noch keine Liste existiert, nehmen wir standardmäßig alle
        self.allowed = self.config_data.get("allowed_runes", self.all_runes)

        ctk.CTkLabel(self, text="Welche Runen sollen alarmiert / aufgehoben werden?", font=("Roboto", 16, "bold"),
                     text_color="#FFD700").pack(pady=(15, 5))
        ctk.CTkLabel(self, text="Nur die hier angehakten Runen werden vom Scanner gesucht.", font=("Roboto", 12),
                     text_color="#aaaaaa").pack(pady=(0, 15))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=5)
        ctk.CTkButton(btn_frame, text="Alle auswählen", command=self.select_all, fg_color="#1f538d", height=35).pack(
            side="left", expand=True, padx=5)
        ctk.CTkButton(btn_frame, text="Keine auswählen", command=self.select_none, fg_color="#8B0000", height=35).pack(
            side="left", expand=True, padx=5)

        self.grid_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", border_width=1, border_color="#333333")
        self.grid_frame.pack(fill="both", expand=True, padx=15, pady=15)

        self.vars = {}
        for i, r in enumerate(self.all_runes):
            var = ctk.BooleanVar(value=(r in self.allowed))
            self.vars[r] = var
            cb = ctk.CTkCheckBox(self.grid_frame, text=r, variable=var, command=self.update_config, font=("Roboto", 13))

            # Schönes Grid-Layout (4 Spalten)
            cb.grid(row=i // 4, column=i % 4, padx=15, pady=8, sticky="w")

        # Stealth Mode aktivieren
        self.after(200, self.apply_stealth_mode)

    def apply_stealth_mode(self):
        """Macht das Fenster für OBS und Screen-Captures (Warden) unsichtbar."""
        try:
            WDA_EXCLUDEFROMCAPTURE = 0x0011
            hwnd = int(self.wm_frame(), 16)
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
        except Exception:
            pass

    def select_all(self):
        for var in self.vars.values():
            var.set(True)
        self.update_config()

    def select_none(self):
        for var in self.vars.values():
            var.set(False)
        self.update_config()

    def update_config(self):
        self.config_data["allowed_runes"] = [r for r, var in self.vars.items() if var.get()]
        self.callback()