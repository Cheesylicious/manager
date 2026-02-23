import customtkinter as ctk
import ctypes
from overlay_config import STEPS_INFO
from calibration_snipping_tool import CalibrationSnippingTool


class CalibrationOverlay(ctk.CTkToplevel):
    def __init__(self, parent, keys_to_calibrate, callback):
        super().__init__(parent)
        self.callback = callback
        self.keys = keys_to_calibrate
        self.current_index = 0
        self.results = {}

        self.title("Overlay Einrichtung")
        self.geometry("650x580")
        self.attributes('-topmost', True)

        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - 650) // 2}+{(sh - 580) // 2}")

        self.lbl_step = ctk.CTkLabel(self, text="...", font=("Roboto", 22, "bold"), text_color="#FFD700")
        self.lbl_step.pack(pady=(25, 5))

        self.lbl_title_step = ctk.CTkLabel(self, text="...", font=("Roboto", 18, "bold"), text_color="white")
        self.lbl_title_step.pack(pady=(0, 15))

        self.lbl_desc = ctk.CTkLabel(self, text="...", font=("Roboto", 15), text_color="#dddddd", wraplength=550,
                                     justify="center")
        self.lbl_desc.pack(pady=10, padx=20)

        self.lbl_count = ctk.CTkLabel(self, text="Bist du bereit?", font=("Roboto", 32, "bold"), text_color="#888888")
        self.lbl_count.pack(pady=20)

        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=10)

        self.btn_action = ctk.CTkButton(self.btn_frame, text="Starten", command=self.start_tool,
                                        fg_color="#1f538d", height=50, font=("Roboto", 14, "bold"))
        self.btn_action.pack(side="left", padx=10)

        self.btn_skip = ctk.CTkButton(self.btn_frame, text="Überspringen ⏭", command=self.skip_step,
                                      fg_color="transparent", border_width=1, text_color="#aaaaaa", height=50)
        self.btn_skip.pack(side="left", padx=10)

        self.setup_step()
        self.after(200, self.apply_stealth_mode)

    def apply_stealth_mode(self):
        try:
            WDA_EXCLUDEFROMCAPTURE = 0x0011
            hwnd = int(self.wm_frame(), 16)
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
        except Exception:
            pass

    def setup_step(self):
        if self.current_index >= len(self.keys):
            self.finish()
            return

        current_key = self.keys[self.current_index]
        name, desc, _ = STEPS_INFO[current_key]

        self.lbl_step.configure(text=f"Schritt {self.current_index + 1} von {len(self.keys)}")
        self.lbl_title_step.configure(text=name)
        self.lbl_desc.configure(text=desc)
        self.lbl_count.configure(text="Bist du bereit?", text_color="#888888")
        self.btn_action.configure(state="normal", text="Auswählen ✂️")
        self.btn_skip.configure(state="normal")

    def skip_step(self):
        self.current_index += 1
        self.setup_step()

    def start_tool(self):
        self.btn_action.configure(state="disabled")
        self.btn_skip.configure(state="disabled")
        self.lbl_count.configure(text="Snipping Tool aktiv...", text_color="#00ccff")

        current_key = self.keys[self.current_index]
        name, desc, _ = STEPS_INFO[current_key]

        # Startet das neue Snipping-Tool für den aktuellen Schritt (current_key wird übergeben)
        CalibrationSnippingTool(self, current_key, name, desc, lambda res: self.on_snipping_success(current_key, res))

    def on_snipping_success(self, key, result_data):
        # Wichtig für Kompatibilität: Ladebildschirm erwartete in der alten Version eine Liste.
        if key == "loading_screen":
            self.results[key] = [result_data]
        else:
            self.results[key] = result_data

        self.current_index += 1
        self.after(500, self.setup_step)

    def finish(self):
        self.callback(self.results)
        self.destroy()