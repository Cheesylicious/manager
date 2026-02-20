import customtkinter as ctk
import cv2
import os
import ctypes
from PIL import Image


class LearningPopup(ctk.CTkToplevel):
    def __init__(self, parent, rune_name, icon_image, folder_path, success_callback):
        """
        Ein Overlay-Popup, das an der Mausposition auftaucht.
        Zeigt das ausgeschnittene Bild an und speichert es nach Bestätigung.
        """
        super().__init__(parent)
        self.rune_name = rune_name
        self.icon_image = icon_image
        self.folder_path = folder_path
        self.success_callback = success_callback

        # Fenster als reines Overlay konfigurieren (wie der Tracker)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color="#1a1a1a", border_width=2, border_color="#FFD700")

        # UI Layout
        self.lbl_title = ctk.CTkLabel(self, text=f"Ist das eine\n{rune_name}?",
                                      font=("Roboto", 14, "bold"), text_color="#FFD700")
        self.lbl_title.pack(pady=(10, 5))

        # Das ausgeschnittene Bild anzeigen
        if self.icon_image is not None:
            # OpenCV nutzt BGR, PIL nutzt RGB. Wir müssen für die UI konvertieren.
            rgb_image = cv2.cvtColor(self.icon_image, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_image)

            # Bild etwas vergrößern, damit man es besser erkennt (NEAREST verhindert Verschwimmen)
            pil_img = pil_img.resize((64, 64), Image.NEAREST)

            self.ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(64, 64))
            self.lbl_img = ctk.CTkLabel(self, text="", image=self.ctk_img)
            self.lbl_img.pack(pady=5)

        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=10, pady=10)

        # Grüner Haken zum Speichern
        self.btn_yes = ctk.CTkButton(self.btn_frame, text="✅ Ja", width=60,
                                     fg_color="#2da44e", hover_color="#238636", command=self.save_icon)
        self.btn_yes.pack(side="left", padx=5)

        # Rotes X zum Abbrechen
        self.btn_no = ctk.CTkButton(self.btn_frame, text="❌ Nein", width=60,
                                    fg_color="#cf222e", hover_color="#a40e26", command=self.destroy)
        self.btn_no.pack(side="right", padx=5)

        # Position berechnen und Stealth-Modus anwenden
        self._position_at_mouse()
        self.after(100, self.apply_stealth_mode)

    def apply_stealth_mode(self):
        """Versteckt das Popup vor OBS/Streaming-Software."""
        try:
            hwnd = int(self.wm_frame(), 16)
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x0011)
        except:
            pass

    def _position_at_mouse(self):
        """Setzt das Popup leicht versetzt zur aktuellen Mausposition."""

        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))

        # 20 Pixel nach rechts unten versetzt, damit der Mauszeiger das UI nicht verdeckt
        self.geometry(f"+{pt.x + 20}+{pt.y + 20}")

    def save_icon(self):
        """Speichert das Icon in Graustufen und meldet den Erfolg zurück."""
        if not os.path.exists(self.folder_path):
            try:
                os.makedirs(self.folder_path)
            except:
                pass

        # Dateiname: z.B. "runes_inventory/ber.png"
        filename = f"{self.rune_name.lower()}.png"
        save_path = os.path.join(self.folder_path, filename)

        try:
            # WICHTIG: Für den Inventar-Scanner speichern wir es als Graustufen-Bild!
            # Graustufen sind bei Inventar-Icons deutlich zuverlässiger als Farben.
            gray_img = cv2.cvtColor(self.icon_image, cv2.COLOR_BGR2GRAY)
            cv2.imwrite(save_path, gray_img)

            if self.success_callback:
                self.success_callback(self.rune_name)
        except Exception as e:
            print(f"[LearningPopup] Fehler beim Speichern: {e}")

        self.destroy()