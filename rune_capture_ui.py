import customtkinter as ctk
import time
import threading
import ctypes
import winsound
import cv2
import numpy as np
import os
import sys
import math
import mss


class RuneCaptureWindow(ctk.CTkToplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("📸 Rune Live-Scanner")
        self.geometry("500x380")
        self.attributes('-topmost', True)
        self.callback = callback

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"+{(sw - 500) // 2}+{(sh - 380) // 2}")

        self.all_runes = [
            "El", "Eld", "Tir", "Nef", "Eth", "Ith", "Tal", "Ral", "Ort", "Thul", "Amn", "Sol", "Shael", "Dol", "Hel",
            "Io", "Lum", "Ko", "Fal", "Lem", "Pul", "Um", "Mal", "Ist", "Gul", "Vex", "Ohm", "Lo", "Sur", "Ber",
            "Jah", "Cham", "Zod"
        ]

        ctk.CTkLabel(self, text="Neues Runen-Bild aufnehmen", font=("Roboto", 18, "bold"), text_color="#FFD700").pack(
            pady=(15, 5))

        desc = ("1. Wähle unten die Rune aus, die du aufnehmen möchtest.\n"
                "2. Wirf die Rune im Spiel auf den Boden.\n"
                "3. Klicke auf Start und bewege die Maus DANEBEN (nicht darauf!).\n"
                "4. Das Tool erkennt den Namen und schneidet '-Rune' automatisch ab.")
        ctk.CTkLabel(self, text=desc, font=("Roboto", 12), text_color="#dddddd", justify="left").pack(pady=10, padx=20)

        self.rune_combo = ctk.CTkOptionMenu(self, values=self.all_runes, width=150)
        self.rune_combo.set("Pul")
        self.rune_combo.pack(pady=10)

        self.lbl_timer = ctk.CTkLabel(self, text="Bereit.", font=("Roboto", 24, "bold"), text_color="#aaaaaa")
        self.lbl_timer.pack(pady=10)

        self.btn_start = ctk.CTkButton(self, text="▶ Aufnahme starten (5 Sek)", command=self.start_capture,
                                       fg_color="#1f538d", height=40)
        self.btn_start.pack(pady=10)

    def start_capture(self):
        self.btn_start.configure(state="disabled")
        threading.Thread(target=self._capture_logic, daemon=True).start()

    def _capture_logic(self):
        for i in range(5, 0, -1):
            self.lbl_timer.configure(text=f"Achtung: {i} Sekunden...", text_color="#FF9500")
            winsound.Beep(1000, 100)
            time.sleep(0.9)

        self.lbl_timer.configure(text="📸 SCANNT!", text_color="#2da44e")

        try:
            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            mx, my = pt.x, pt.y

            sw = ctypes.windll.user32.GetSystemMetrics(0)
            sh = ctypes.windll.user32.GetSystemMetrics(1)

            box_size = 250
            x1 = max(0, mx - box_size)
            y1 = max(0, my - box_size)
            x2 = min(sw, mx + box_size)
            y2 = min(sh, my + box_size)

            with mss.mss() as sct:
                monitor = {"top": y1, "left": x1, "width": x2 - x1, "height": y2 - y1}
                sct_img = sct.grab(monitor)
                screen_bgr = np.array(sct_img)[:, :, :3]

            b = screen_bgr[:, :, 0].astype(np.int16)
            g = screen_bgr[:, :, 1].astype(np.int16)
            r = screen_bgr[:, :, 2].astype(np.int16)
            mask = (r > 140) & (r > g) & (g > b) & ((r - g) > 20) & ((r - g) < 120)

            mask_uint8 = mask.astype(np.uint8) * 255
            kernel = np.ones((5, 25), np.uint8)
            dilated = cv2.dilate(mask_uint8, kernel, iterations=1)
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if not contours:
                self.lbl_timer.configure(text="❌ Nichts gefunden!", text_color="#cf222e")
                winsound.Beep(500, 500)
                self.btn_start.configure(state="normal")
                return

            cx = mx - x1
            cy = my - y1
            best_dist = float('inf')
            best_rect = None

            for cnt in contours:
                rx, ry, rw, rh = cv2.boundingRect(cnt)
                if rw < 15 or rh < 5:
                    continue
                rect_center_x = rx + rw // 2
                rect_center_y = ry + rh // 2
                dist = math.hypot(rect_center_x - cx, rect_center_y - cy)

                if dist < best_dist:
                    best_dist = dist
                    best_rect = (rx, ry, rw, rh)

            if not best_rect:
                self.lbl_timer.configure(text="❌ Keine gültige Schrift gefunden.", text_color="#cf222e")
                self.btn_start.configure(state="normal")
                return

            bx, by, bw, bh = best_rect

            # --- INNOVATION: Automatisches Entfernen von "-Rune" ---
            # Wir analysieren die Maske innerhalb des gefundenen Rechtecks
            tag_mask = mask_uint8[by:by + bh, bx:bx + bw]
            inner_contours, _ = cv2.findContours(tag_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            # Sortieren von links nach rechts
            inner_contours = sorted(inner_contours, key=lambda c: cv2.boundingRect(c)[0])

            split_x = bw  # Standardmäßig volle Breite
            for cnt_in in inner_contours:
                ix, iy, iw, ih = cv2.boundingRect(cnt_in)
                # D2R Bindestrich-Logik: Er ist flach (iw > ih) und trennt Name von Suffix
                if iw > ih * 1.2 and ix > bw * 0.2:
                    split_x = ix - 3  # Schnittpunkt 3 Pixel vor dem Bindestrich
                    break

            pad = 5
            crop_y1 = max(0, by - pad)
            crop_y2 = min(screen_bgr.shape[0], by + bh + pad)
            crop_x1 = max(0, bx - pad)
            # Nutze den berechneten split_x für den Crop
            crop_x2 = min(screen_bgr.shape[1], bx + split_x)

            final_img = screen_bgr[crop_y1:crop_y2, crop_x1:crop_x2]

            # Dateinamen-Bereinigung (Falls im Dropdown "-Rune" stehen sollte)
            rune_name = self.rune_combo.get().replace("-Rune", "").replace("-rune", "").strip().lower()

            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))

            folder_path = os.path.join(base_path, "runes_filter")
            os.makedirs(folder_path, exist_ok=True)

            save_path = os.path.join(folder_path, f"{rune_name}.png")
            cv2.imwrite(save_path, final_img)

            winsound.Beep(1500, 150)
            winsound.Beep(2000, 200)
            self.lbl_timer.configure(text=f"✅ {rune_name.upper()} gespeichert!", text_color="#2da44e")
            self.callback()
            time.sleep(2)
            self.destroy()

        except Exception as e:
            self.lbl_timer.configure(text="❌ Fehler aufgetreten.", text_color="#cf222e")
            print(f"Capture Error: {e}")
            self.btn_start.configure(state="normal")