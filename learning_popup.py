import customtkinter as ctk
import cv2
import os
import ctypes
from PIL import Image


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

        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=10, pady=5)

        # Buttons
        self.btn_yes = ctk.CTkButton(self.btn_frame, text="✅ Ja", width=50, height=30,
                                     fg_color="#2da44e", hover_color="#238636", command=self.save_icon)
        self.btn_yes.pack(side="left", padx=2)

        self.btn_later = ctk.CTkButton(self.btn_frame, text="🕒 Später", width=60, height=30,
                                       fg_color="#1f538d", hover_color="#1a4577", command=self.mark_later)
        self.btn_later.pack(side="left", padx=2)

        self.btn_no = ctk.CTkButton(self.btn_frame, text="❌", width=30, height=30,
                                    fg_color="#cf222e", hover_color="#a40e26", command=self.destroy)
        self.btn_no.pack(side="left", padx=2)

        # Positionierung sofort starten und Ghosting anwenden
        self.after(10, self._position_relative_to_parent)
        self.after(100, self.apply_stealth_mode)

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
        except:
            pass

    def mark_later(self):
        """Gibt die Rune zurück an das Overlay zur späteren Bearbeitung."""
        if self.later_callback:
            self.later_callback(self.rune_name)
        # NEU: Falls der Callback vom Scanner nicht durchgereicht wurde,
        # rufen wir die neue Funktion im Haupt-Overlay direkt und zwingend auf.
        elif hasattr(self, 'parent_overlay') and hasattr(self.parent_overlay, 'add_pending_rune'):
            self.parent_overlay.add_pending_rune(self.rune_name)

        self.destroy()

    def save_icon(self):
        if not os.path.exists(self.folder_path):
            try:
                os.makedirs(self.folder_path)
            except:
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