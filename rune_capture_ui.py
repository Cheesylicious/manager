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

        ctk.CTkLabel(self, text="Neues Runen-Bild aufnehmen", font=("Roboto", 18, "bold"), text_color="#FFD700").pack(
            pady=(15, 5))

        desc = ("1. Tippe unten den Namen der Rune ein, die du aufnehmen möchtest.\n"
                "2. Wirf die Rune im Spiel auf den Boden.\n"
                "3. Klicke auf Start (das Fenster verschwindet) und lege die Maus\n"
                "   auf das Item (am besten direkt auf den Text '-Rune').\n"
                "4. Nach 5 Sekunden (Beep-Töne) wird das Item automatisch gescannt.")
        ctk.CTkLabel(self, text=desc, font=("Roboto", 12), text_color="#dddddd", justify="left").pack(pady=10, padx=20)

        self.rune_entry = ctk.CTkEntry(self, width=150, placeholder_text="Name (z.B. Ber)")
        self.rune_entry.pack(pady=10)

        self.lbl_timer = ctk.CTkLabel(self, text="Bereit.", font=("Roboto", 24, "bold"), text_color="#aaaaaa")
        self.lbl_timer.pack(pady=10)

        self.btn_start = ctk.CTkButton(self, text="▶ Aufnahme starten (5 Sek)", command=self.start_capture,
                                       fg_color="#1f538d", height=40)
        self.btn_start.pack(pady=10)

        self.after(200, self.apply_stealth_mode)

    def apply_stealth_mode(self):
        try:
            WDA_EXCLUDEFROMCAPTURE = 0x0011
            hwnd = int(self.wm_frame(), 16)
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
        except Exception:
            pass

    def start_capture(self):
        if not self.rune_entry.get().strip():
            self.lbl_timer.configure(text="❌ Bitte Namen eingeben!", text_color="#cf222e")
            return

        self.withdraw()
        threading.Thread(target=self._capture_logic, daemon=True).start()

    def _safe_destroy(self):
        """Zerstört das Fenster absolut sicher über den Main-Thread."""
        if self.winfo_exists():
            self.destroy()

    def _safe_success(self):
        """Führt den Callback aus und zerstört das Fenster sicher über den Main-Thread."""
        if self.callback:
            self.callback()
        self._safe_destroy()

    def _capture_logic(self):
        # Akustischer Countdown
        for i in range(5, 0, -1):
            winsound.Beep(1000, 100)
            time.sleep(0.9)

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
                winsound.Beep(500, 500)
                self.after(0, self._safe_destroy)
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
                winsound.Beep(500, 500)
                self.after(0, self._safe_destroy)
                return

            bx, by, bw, bh = best_rect

            tag_mask = mask_uint8[by:by + bh, bx:bx + bw]
            inner_contours, _ = cv2.findContours(tag_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            inner_contours = sorted(inner_contours, key=lambda c: cv2.boundingRect(c)[0])

            split_x = bw
            for cnt_in in inner_contours:
                ix, iy, iw, ih = cv2.boundingRect(cnt_in)
                if iw > ih * 1.2 and ix > bw * 0.2:
                    split_x = ix - 3
                    break

            pad = 5
            crop_y1 = max(0, by - pad)
            crop_y2 = min(screen_bgr.shape[0], by + bh + pad)
            crop_x1 = max(0, bx - pad)
            crop_x2 = min(screen_bgr.shape[1], bx + split_x)

            final_img = screen_bgr[crop_y1:crop_y2, crop_x1:crop_x2]

            raw_name = self.rune_entry.get()
            rune_name = raw_name.replace("-Rune", "").replace("-rune", "").strip().lower()

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

            # Anweisung zum Beenden und Weitergeben sicher an den Main-Thread senden
            self.after(0, self._safe_success)

        except Exception as e:
            print(f"Capture Error: {e}")
            winsound.Beep(500, 500)
            self.after(0, self._safe_destroy)