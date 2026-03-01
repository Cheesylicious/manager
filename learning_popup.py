import customtkinter as ctk
import cv2
import os
import ctypes
import time
import sys
import winsound
from PIL import Image

# INNOVATION: KI Engine für den selbstlernenden Prozess einbinden
try:
    from ai_metrics_engine import AIEngine
except ImportError:
    AIEngine = None


class LearningPopup(ctk.CTkToplevel):
    def __init__(self, parent, rune_name, icon_image, folder_path, success_callback, later_callback=None):
        """
        Ein Overlay-Popup, das rechts am Haupt-Overlay haftet.
        """
        super().__init__(parent)

        # Speichere die explizite Referenz auf das Haupt-Overlay
        self.parent_overlay = parent
        self.rune_name = rune_name
        self.icon_image = icon_image
        self.folder_path = folder_path
        self.success_callback = success_callback
        self.later_callback = later_callback

        # KI-Engine initialisieren
        self.ai_engine = AIEngine() if AIEngine else None

        # Fenster-Konfiguration
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
        self.lbl_title = ctk.CTkLabel(self, text=f"Rune erkannt:\n{rune_name.upper()}",
                                      font=("Roboto", 14, "bold"), text_color="#FFD700")
        self.lbl_title.pack(pady=(10, 5), padx=10)

        if self.icon_image is not None:
            rgb_image = cv2.cvtColor(self.icon_image, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_image)
            pil_img = pil_img.resize((64, 64), Image.NEAREST)
            self.ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(64, 64))
            self.lbl_img = ctk.CTkLabel(self, text="", image=self.ctk_img)
            self.lbl_img.pack(pady=5)

        # Standard-Buttons Frame
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=10, pady=5)

        # Kompakte Buttons, um Platz für das Fehler-Reporting zu machen
        self.btn_yes = ctk.CTkButton(self.btn_frame, text="✅ Ja", width=45, height=30,
                                     fg_color="#2da44e", hover_color="#238636", command=self.save_icon)
        self.btn_yes.pack(side="left", padx=2)

        self.btn_later = ctk.CTkButton(self.btn_frame, text="🕒 Später", width=55, height=30,
                                       fg_color="#1f538d", hover_color="#1a4577", command=self.mark_later)
        self.btn_later.pack(side="left", padx=2)

        # Falschmeldung Button
        self.btn_false = ctk.CTkButton(self.btn_frame, text="⚠️ Falsch", width=60, height=30,
                                       fg_color="#d97706", hover_color="#b45309",
                                       command=self.show_false_positive_options)
        self.btn_false.pack(side="left", padx=2)

        self.btn_no = ctk.CTkButton(self.btn_frame, text="❌", width=30, height=30,
                                    fg_color="#cf222e", hover_color="#a40e26", command=self.destroy)
        self.btn_no.pack(side="left", padx=2)

        # Verstecktes Menü für die Fehlerkategorisierung
        self.fp_frame = ctk.CTkFrame(self, fg_color="transparent")

        self.btn_fp_none = ctk.CTkButton(self.fp_frame, text="Gar keine Rune gedroppt", height=25,
                                         command=lambda: self.save_false_positive("keine_rune"))
        self.btn_fp_none.pack(fill="x", pady=2, padx=10)

        self.btn_fp_wrong = ctk.CTkButton(self.fp_frame, text="Anderes Item / Falsche Rune", height=25,
                                          command=lambda: self.save_false_positive("falsches_item"))
        self.btn_fp_wrong.pack(fill="x", pady=2, padx=10)

        self.btn_fp_cancel = ctk.CTkButton(self.fp_frame, text="Zurück", height=25, fg_color="#444444",
                                           command=self.hide_false_positive_options)
        self.btn_fp_cancel.pack(fill="x", pady=(5, 2), padx=10)

        # Positionierung sofort starten und Ghosting anwenden
        self.after(10, self._position_relative_to_parent)
        self.after(100, self.apply_stealth_mode)

    def show_false_positive_options(self):
        """Versteckt die normalen Buttons und zeigt die Fehler-Kategorien."""
        self.btn_frame.pack_forget()
        self.lbl_title.configure(text="Grund der Falschmeldung:")
        self.fp_frame.pack(fill="x", pady=5)

    def hide_false_positive_options(self):
        """Kehrt zum normalen Menü zurück."""
        self.fp_frame.pack_forget()
        self.lbl_title.configure(text=f"Rune erkannt:\n{self.rune_name.upper()}")
        self.btn_frame.pack(fill="x", padx=10, pady=5)

    def save_false_positive(self, reason):
        """Speichert das erkannte Bild als Negativ-Beispiel für den Scanner ab und meldet es der KI."""
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        fp_folder = os.path.join(base_path, "false_positives")

        if not os.path.exists(fp_folder):
            try:
                os.makedirs(fp_folder)
            except Exception:
                pass

        timestamp = int(time.time())
        filename = f"{reason}_{self.rune_name.lower()}_{timestamp}.png"
        save_path = os.path.join(fp_folder, filename)

        try:
            if self.icon_image is not None:
                # Das Original-Farbbild speichern, um später bessere Analysen zu ermöglichen
                cv2.imwrite(save_path, self.icon_image)
        except Exception as e:
            print(f"[LearningPopup] Fehler beim Speichern der Falschmeldung: {e}")

        # --- NEU: KI Integration ---
        if self.ai_engine:
            # KI über Fehler informieren, um Schwellenwerte anzupassen
            self.ai_engine.report_false_positive(self.rune_name, 0.85)

            try:
                winsound.Beep(500, 150)
            except Exception:
                pass

            # Feedback an das Haupt-Overlay senden
            if hasattr(self.parent_overlay, 'lbl_live_loot'):
                try:
                    msg = f"KI lernt: {self.rune_name} Bild geblockt"
                    if reason == "falsches_item":
                        msg = f"KI: Form-Scan für {self.rune_name} korrigiert"
                    self.parent_overlay.lbl_live_loot.configure(text=msg, text_color="#ffaa00")
                except Exception:
                    pass
        # ---------------------------

        self.destroy()

    def _position_relative_to_parent(self):
        """Platziert das Popup exakt rechts neben dem Parent-Fenster und klebt daran fest."""
        try:
            # Nutze die explizite Referenz anstatt self.master
            if self.winfo_exists() and hasattr(self, 'parent_overlay') and self.parent_overlay.winfo_exists():
                px = self.parent_overlay.winfo_x()
                py = self.parent_overlay.winfo_y()
                pw = self.parent_overlay.winfo_width()

                # 5 Pixel Abstand zum Haupt-Overlay
                target_x = px + pw + 5
                target_y = py

                self.geometry(f"+{target_x}+{target_y}")

                # Wiederhole den Aufruf, damit das Popup wie magnetisch am Haupt-Overlay klebt,
                # falls das Haupt-Overlay mit der Maus verschoben wird.
                self.after(20, self._position_relative_to_parent)
        except Exception:
            pass

    def apply_stealth_mode(self):
        try:
            hwnd = int(self.wm_frame(), 16)
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x0011)
        except Exception:
            pass

    def mark_later(self):
        """Gibt die Rune zurück an das Overlay zur späteren Bearbeitung."""
        if self.later_callback:
            self.later_callback(self.rune_name)
        # Falls der Callback vom Scanner nicht durchgereicht wurde,
        # rufen wir die neue Funktion im Haupt-Overlay direkt und zwingend auf.
        elif hasattr(self, 'parent_overlay') and hasattr(self.parent_overlay, 'add_pending_rune'):
            self.parent_overlay.add_pending_rune(self.rune_name)

        self.destroy()

    def save_icon(self):
        if not os.path.exists(self.folder_path):
            try:
                os.makedirs(self.folder_path)
            except Exception:
                pass

        filename = f"{self.rune_name.lower()}.png"
        save_path = os.path.join(self.folder_path, filename)

        try:
            gray_img = cv2.cvtColor(self.icon_image, cv2.COLOR_BGR2GRAY)
            cv2.imwrite(save_path, gray_img)
            if self.success_callback:
                self.success_callback(self.rune_name)
        except Exception as e:
            print(f"[LearningPopup] Fehler: {e}")

        self.destroy()