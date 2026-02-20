import customtkinter as ctk
import time
import threading
import ctypes
import winsound
import cv2
import numpy as np
import os
import sys
import mss


class ZoneCaptureWindow(ctk.CTkToplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("🗺️ Zonen Live-Scanner")
        self.geometry("500x380")
        self.attributes('-topmost', True)
        self.callback = callback

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"+{(sw - 500) // 2}+{(sh - 380) // 2}")

        ctk.CTkLabel(self, text="Neue Zone aufnehmen", font=("Roboto", 18, "bold"), text_color="#00ccff").pack(
            pady=(15, 5))

        desc = ("1. Öffne im Spiel die Minimap.\n"
                "2. Tippe unten den Namen der Zone ein.\n"
                "3. Klicke auf Start. Das Tool macht nun eine Serienaufnahme (5 Bilder in 2 Sekunden).\n"
                "4. Bewege dich während der Aufnahme NICHT und tabbe NICHT aus!")
        ctk.CTkLabel(self, text=desc, font=("Roboto", 12), text_color="#dddddd", justify="left").pack(pady=10, padx=20)

        self.entry_name = ctk.CTkEntry(self, placeholder_text="Name der Zone eingeben...", width=200)
        self.entry_name.pack(pady=10)

        self.lbl_timer = ctk.CTkLabel(self, text="Bereit.", font=("Roboto", 24, "bold"), text_color="#aaaaaa")
        self.lbl_timer.pack(pady=10)

        self.btn_start = ctk.CTkButton(self, text="▶ Aufnahme starten (5 Sek)", command=self.start_capture,
                                       fg_color="#1f538d", height=40)
        self.btn_start.pack(pady=10)

    def _update_ui(self, text, color, reset_btns=False):
        if self.winfo_exists():
            self.lbl_timer.configure(text=text, text_color=color)
            if reset_btns:
                self.btn_start.configure(state="normal")
                self.entry_name.configure(state="normal")

    def start_capture(self):
        zone_name = self.entry_name.get().strip()
        if not zone_name:
            self.lbl_timer.configure(text="❌ Bitte Namen eingeben!", text_color="#cf222e")
            return

        self.btn_start.configure(state="disabled")
        self.entry_name.configure(state="disabled")
        threading.Thread(target=self._capture_logic, args=(zone_name,), daemon=True).start()

    def _capture_logic(self, zone_name):
        for i in range(5, 0, -1):
            if not self.winfo_exists(): return
            self.after(0, self._update_ui, f"Achtung: {i} Sekunden...", "#FF9500")
            winsound.Beep(1000, 100)
            time.sleep(0.9)

        if not self.winfo_exists(): return
        self.after(0, self._update_ui, "📸 SERIENAUFNAHME LÄUFT!", "#2da44e")

        try:
            sw = ctypes.windll.user32.GetSystemMetrics(0)
            sh = ctypes.windll.user32.GetSystemMetrics(1)

            x1 = int(sw * 0.75)
            y1 = int(sh * 0.0)
            x2 = sw
            y2 = int(sh * 0.15)

            # Dynamischer Breiten-Filter: Ignoriert alles, was schmaler als 5.5% der Bildschirmbreite ist (z.B. Uhrzeit)
            min_width_threshold = int(sw * 0.055)

            clean_name = zone_name.replace(" ", "_")

            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))

            folder_path = os.path.join(base_path, "zones_filter")
            os.makedirs(folder_path, exist_ok=True)

            valid_captures = 0

            for i in range(5):
                with mss.mss() as sct:
                    monitor = {"top": y1, "left": x1, "width": x2 - x1, "height": y2 - y1}
                    sct_img = sct.grab(monitor)
                    screen_bgr = np.array(sct_img)[:, :, :3]

                gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
                _, mask_uint8 = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

                kernel = np.ones((5, 40), np.uint8)
                dilated = cv2.dilate(mask_uint8, kernel, iterations=1)
                contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                if contours:
                    rects = []
                    for cnt in contours:
                        rx, ry, rw, rh = cv2.boundingRect(cnt)
                        # Grundlegenden Staub und Mini-Pixel ignorieren
                        if rw > 20 and rh > 8:
                            rects.append((rx, ry, rw, rh))

                    # Sortiere alle Textblöcke strikt von OBEN nach UNTEN
                    rects.sort(key=lambda r: r[1])

                    best_rect = None
                    for r in rects:
                        rx, ry, rw, rh = r
                        # Wir nehmen das ERSTE Element von oben, das breiter ist als die Uhrzeit!
                        if rw > min_width_threshold:
                            best_rect = r
                            break

                    if best_rect:
                        bx, by, bw, bh = best_rect
                        pad = 8
                        crop_y1 = max(0, by - pad)
                        crop_y2 = min(screen_bgr.shape[0], by + bh + pad)
                        crop_x1 = max(0, bx - pad)
                        crop_x2 = min(screen_bgr.shape[1], bx + bw + pad)

                        final_img = screen_bgr[crop_y1:crop_y2, crop_x1:crop_x2]

                        valid_captures += 1
                        save_path = os.path.join(folder_path, f"{clean_name}_ref{valid_captures}.png")

                        is_success, im_buf_arr = cv2.imencode(".png", final_img)
                        if is_success:
                            with open(save_path, "wb") as f:
                                f.write(im_buf_arr.tobytes())

                time.sleep(0.4)

            if valid_captures == 0:
                self.after(0, self._update_ui, "❌ Kein gültiger Text gefunden!", "#cf222e", True)
                winsound.Beep(500, 500)
                return

            winsound.Beep(1500, 150)
            winsound.Beep(2000, 200)

            self.after(0, self._update_ui, f"✅ {valid_captures} Referenzen gespeichert!", "#2da44e")
            self.after(0, self.callback)
            time.sleep(2)

            if self.winfo_exists():
                self.after(0, self.destroy)

        except Exception as e:
            self.after(0, self._update_ui, "❌ Fehler aufgetreten.", "#cf222e", True)
            print(f"Capture Error: {e}")