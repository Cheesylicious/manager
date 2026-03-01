import customtkinter as ctk
import ctypes
import winsound
import os
import sys
import time
import cv2
import random
from overlay_config import TrackerConfig

ALL_RUNES = [
    "El", "Eld", "Tir", "Nef", "Eth", "Ith", "Tal", "Ral", "Ort", "Thul", "Amn", "Sol",
    "Shael", "Dol", "Hel", "Io", "Lum", "Ko", "Fal", "Lem", "Pul", "Um", "Mal", "Ist",
    "Gul", "Vex", "Ohm", "Lo", "Sur", "Ber", "Jah", "Cham", "Zod"
]


class RuneVerificationPrompt(ctk.CTkToplevel):
    def __init__(self, parent, predicted_rune, ground_score, inv_score, ground_img, ai_engine, on_confirm, on_correct):
        super().__init__(parent)
        self.parent_overlay = parent
        self.predicted_rune = predicted_rune
        self.ground_score = ground_score
        self.inv_score = inv_score
        self.ground_img = ground_img
        self.ai_engine = ai_engine
        self.on_confirm = on_confirm
        self.on_correct = on_correct

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        if hasattr(parent, 'attributes'):
            try:
                self.attributes("-alpha", parent.attributes("-alpha"))
            except:
                pass

        self.configure(fg_color="#1a1a1a", border_width=2, border_color="#00ccff")

        self.lbl_title = ctk.CTkLabel(self, text=f"Rune erkannt: {predicted_rune.title()}\nKorrekt?",
                                      font=("Roboto", 12, "bold"), text_color="#00ccff")
        self.lbl_title.pack(pady=(10, 2), padx=15)

        g_pct = int(self.ground_score * 100)
        i_pct = int(self.inv_score * 100)

        score_text = f"Boden-Scan: {g_pct}%"
        if i_pct > 0:
            score_text += f" | Inventar: {i_pct}%"
        else:
            score_text += f" | Inventar: Nicht geprüft"

        self.lbl_score = ctk.CTkLabel(self, text=score_text, font=("Roboto", 11, "bold"), text_color="#aaaaaa")
        self.lbl_score.pack(pady=(0, 5))

        self.auto_verify_var = ctk.BooleanVar(value=False)
        self.cb_auto = ctk.CTkCheckBox(self, text="Dauerhaft ausblenden\n(Zukünftig auto-akzeptieren)",
                                       variable=self.auto_verify_var, font=("Roboto", 10),
                                       checkbox_width=16, checkbox_height=16)
        self.cb_auto.pack(pady=(0, 10))

        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.btn_yes = ctk.CTkButton(self.btn_frame, text="✅ Ja", width=55, height=26,
                                     fg_color="#2da44e", hover_color="#238636", command=self.confirm)
        self.btn_yes.pack(side="left", padx=2, expand=True)

        self.btn_no = ctk.CTkButton(self.btn_frame, text="❌ Nein", width=55, height=26,
                                    fg_color="#cf222e", hover_color="#a40e26", command=self.show_correction)
        self.btn_no.pack(side="left", padx=2, expand=True)

        self.correction_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=6)

        self.rune_frame = ctk.CTkFrame(self.correction_frame, fg_color="transparent")
        self.rune_frame.pack(fill="x", pady=(5, 2), padx=10)
        self.correction_var = ctk.StringVar(value="Andere Rune wählen...")
        self.correction_dropdown = ctk.CTkOptionMenu(self.rune_frame, variable=self.correction_var,
                                                     values=ALL_RUNES, width=150, height=24, font=("Roboto", 11),
                                                     command=self.submit_rune_correction)
        self.correction_dropdown.pack(fill="x")

        self.custom_frame = ctk.CTkFrame(self.correction_frame, fg_color="transparent")
        self.custom_frame.pack(fill="x", pady=2, padx=10)
        self.custom_entry = ctk.CTkEntry(self.custom_frame, placeholder_text="Anderes Item (z.B. Amulett)...",
                                         height=24, font=("Roboto", 11))
        self.custom_entry.pack(side="left", fill="x", expand=True, padx=(0, 2))
        self.custom_entry.bind("<Return>", lambda e: self.submit_custom_item())

        self.btn_custom_ok = ctk.CTkButton(self.custom_frame, text="OK", width=30, height=24, fg_color="#1f538d",
                                           hover_color="#1a4577", command=self.submit_custom_item)
        self.btn_custom_ok.pack(side="right")

        self.action_frame = ctk.CTkFrame(self.correction_frame, fg_color="transparent")
        self.action_frame.pack(fill="x", pady=(2, 5), padx=10)

        self.btn_false_alarm = ctk.CTkButton(self.action_frame, text="❌ Falschalarm", height=24, fg_color="#8B0000",
                                             hover_color="#5A0000", command=self.submit_false_alarm)
        self.btn_false_alarm.pack(side="left", fill="x", expand=True, padx=(0, 2))

        self.btn_cancel = ctk.CTkButton(self.action_frame, text="Zurück", height=24, fg_color="#444",
                                        hover_color="#333", command=self.hide_correction)
        self.btn_cancel.pack(side="right", fill="x", expand=True, padx=(2, 0))

        self.after(10, self._position_relative_to_parent)
        self.after(100, self.apply_stealth_mode)
        self._timeout = self.after(10000, self.auto_confirm)

    def _position_relative_to_parent(self):
        try:
            if self.winfo_exists() and hasattr(self, 'parent_overlay') and self.parent_overlay.winfo_exists():
                px = self.parent_overlay.winfo_x()
                py = self.parent_overlay.winfo_y()
                pw = self.parent_overlay.winfo_width()
                target_x = px + pw + 5
                target_y = py
                self.geometry(f"+{target_x}+{target_y}")
                self.after(20, self._position_relative_to_parent)
        except Exception:
            pass

    def apply_stealth_mode(self):
        try:
            hwnd = int(self.wm_frame(), 16)
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x0011)
        except Exception:
            pass

    def show_correction(self):
        if self._timeout:
            self.after_cancel(self._timeout)

        self.cb_auto.pack_forget()
        self.btn_frame.pack_forget()
        self.lbl_title.configure(text=f"Falsch erkannt: {self.predicted_rune.title()}\nWas war es wirklich?")
        self.correction_frame.pack(fill="x", padx=10, pady=(0, 10))
        self._timeout = self.after(15000, self.destroy)

    def hide_correction(self):
        self.correction_frame.pack_forget()
        self.lbl_title.configure(text=f"Rune erkannt: {self.predicted_rune.title()}\nKorrekt?")
        self.cb_auto.pack(pady=(0, 10))
        self.btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.correction_var.set("Andere Rune wählen...")

    def save_false_positive_image(self, reason_prefix):
        if self.ground_img is None: return

        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        fp_folder = os.path.join(base_path, "false_positives")
        os.makedirs(fp_folder, exist_ok=True)

        ts = int(time.time())
        filename = f"fp_{reason_prefix}_{ts}.png"
        save_path = os.path.join(fp_folder, filename)
        try:
            cv2.imwrite(save_path, self.ground_img)
        except:
            pass

    def save_new_rune_template(self, actual_rune_name):
        """Macht ein Foto vom Bodenscan und speichert es als Template für eine noch unbekannte Rune."""
        if self.ground_img is None: return

        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        filter_folder = os.path.join(base_path, "runes_filter")
        os.makedirs(filter_folder, exist_ok=True)

        existing = [f for f in os.listdir(filter_folder) if f.lower().startswith(actual_rune_name.lower())]

        if len(existing) < 3:
            new_idx = len(existing) + 1
        else:
            new_idx = random.randint(1, 3)

        filename = f"{actual_rune_name.lower()}_{new_idx}.png"
        save_path = os.path.join(filter_folder, filename)

        try:
            cv2.imwrite(save_path, self.ground_img)
        except:
            pass

    def submit_rune_correction(self, actual_rune):
        if self._timeout: self.after_cancel(self._timeout)

        # Das ist die Zero-Shot Learning Brücke!
        # Hat er "Eth" gesagt, aber es war eine "Cham", speichert er das Bild sofort als "cham_1.png" in den Filter.
        self.save_new_rune_template(actual_rune)

        if self.ai_engine:
            self.ai_engine.report_misclassification(self.predicted_rune, actual_rune, self.ground_score)
            winsound.Beep(500, 150)

        if self.on_correct:
            self.on_correct(self.predicted_rune, actual_rune, "rune")
        self.destroy()

    def submit_custom_item(self):
        if self._timeout: self.after_cancel(self._timeout)

        custom_item = self.custom_entry.get().strip()
        if not custom_item:
            return

        self.save_false_positive_image("custom_item")

        if self.ai_engine:
            self.ai_engine.report_custom_false_positive(self.predicted_rune, custom_item, self.ground_score)
            winsound.Beep(500, 150)

        if self.on_correct:
            self.on_correct(self.predicted_rune, custom_item, "custom")
        self.destroy()

    def submit_false_alarm(self):
        if self._timeout: self.after_cancel(self._timeout)
        self.save_false_positive_image("false_alarm")

        if self.ai_engine:
            self.ai_engine.report_false_positive(self.predicted_rune, self.ground_score)
            winsound.Beep(500, 150)
        if self.on_correct:
            self.on_correct(self.predicted_rune, "Nichts", "false_alarm")
        self.destroy()

    def confirm(self):
        if self._timeout:
            self.after_cancel(self._timeout)

        if self.auto_verify_var.get():
            cfg = TrackerConfig.load()
            if "auto_verify" not in cfg:
                cfg["auto_verify"] = []
            if self.predicted_rune not in cfg["auto_verify"]:
                cfg["auto_verify"].append(self.predicted_rune)
                TrackerConfig.save(cfg)

        if self.on_confirm:
            self.on_confirm(self.predicted_rune)
        self.destroy()

    def auto_confirm(self):
        if self.on_confirm:
            self.on_confirm(self.predicted_rune)
        self.destroy()