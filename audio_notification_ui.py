import customtkinter as ctk
import ctypes
import winsound
import threading
import time


class AudioNotificationWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_overlay = parent

        self.overrideredirect(True)
        self.attributes("-topmost", True)

        # Transparenz vom Haupt-Overlay übernehmen, falls vorhanden
        if hasattr(parent, 'attributes'):
            try:
                self.attributes("-alpha", parent.attributes("-alpha"))
            except:
                pass

        self.configure(fg_color="#1a1a1a", border_width=2, border_color="#FFD700")

        self.lbl_title = ctk.CTkLabel(self, text="🎵 Runen-Sound erkannt!",
                                      font=("Roboto", 13, "bold"), text_color="#FFD700")
        self.lbl_title.pack(pady=(10, 2), padx=15)

        self.lbl_info = ctk.CTkLabel(self, text="Vergiss nicht, ALT zu drücken,\num den Drop zu prüfen!",
                                     font=("Roboto", 11), text_color="#aaaaaa")
        self.lbl_info.pack(pady=(0, 10), padx=15)

        self.after(10, self._position_relative_to_parent)
        self.after(100, self.apply_stealth_mode)

        # Startet den dezenten Hinweiston asynchron, ohne die GUI zu blockieren
        threading.Thread(target=self._play_notification_sound, daemon=True).start()

        # Schließt sich nach 4 Sekunden automatisch
        self.after(4000, self.destroy)

    def _play_notification_sound(self):
        # Ein kurzes, ansteigendes und dezentes "Klingeln",
        # das sich von HP, Mana und der KI-Erkennung deutlich unterscheidet.
        winsound.Beep(1200, 80)
        time.sleep(0.05)
        winsound.Beep(1600, 120)

    def _position_relative_to_parent(self):
        try:
            if self.winfo_exists() and hasattr(self, 'parent_overlay') and self.parent_overlay.winfo_exists():
                px = self.parent_overlay.winfo_x()
                py = self.parent_overlay.winfo_y()
                ph = self.parent_overlay.winfo_height()

                # Positionierung exakt unterhalb des Haupt-Trackers mit 5 Pixeln Abstand
                target_x = px
                target_y = py + ph + 5
                self.geometry(f"+{target_x}+{target_y}")
                self.after(50, self._position_relative_to_parent)
        except Exception:
            pass

    def apply_stealth_mode(self):
        try:
            hwnd = int(self.wm_frame(), 16)
            # Verhindert, dass das Fenster von Streaming-Tools aufgenommen wird (Stealth-Modus)
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x0011)
        except Exception:
            pass