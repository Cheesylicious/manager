import time
import threading
import os
import sys
import cv2
import numpy as np
import mss
import re

TEMPLATE_FOLDER = "zones_filter"


class ZoneWatcher:
    def __init__(self, config_data):
        self.running = False
        self.thread = None
        self.stop_event = threading.Event()
        self.config = config_data
        self.current_zone = "Unbekannt"

        self.templates = []
        self._load_templates()

    def _load_templates(self):
        self.templates = []
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        folder_path = os.path.join(base_path, TEMPLATE_FOLDER)

        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path)
            except:
                pass
            return

        print(f"[ZoneWatcher] Lade Zonen-Bilder aus '{folder_path}'...")

        for f in os.listdir(folder_path):
            if f.lower().endswith(('.png', '.jpg', '.bmp')):
                base_name = os.path.splitext(f)[0]
                zone_name = re.sub(r'_ref\d+$', '', base_name).replace("_", " ")

                full_path = os.path.join(folder_path, f)

                try:
                    with open(full_path, "rb") as file:
                        file_bytes = np.frombuffer(file.read(), dtype=np.uint8)
                    tmpl = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                except Exception as e:
                    print(f" -> Fehler beim Laden von {f}: {e}")
                    continue

                if tmpl is not None:
                    gray = cv2.cvtColor(tmpl, cv2.COLOR_BGR2GRAY)
                    _, tmpl_binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

                    contours, _ = cv2.findContours(tmpl_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    if contours:
                        x, y, w, h = cv2.boundingRect(np.vstack(contours))
                        tmpl_cropped = tmpl_binary[y:y + h, x:x + w]

                        tmpl_px = cv2.countNonZero(tmpl_cropped)
                        if tmpl_px > 50:
                            self.templates.append((zone_name, tmpl_cropped, tmpl_px))
                            print(f" -> Zone geladen: {zone_name} (aus {f})")
                        else:
                            print(f" -> IGNORIERT: {f} enthält zu wenig Text ({tmpl_px} Px)")

    def start(self):
        if not self.running:
            self._load_templates()
            self.running = True
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._scan_loop, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        self.stop_event.set()

    def _scan_loop(self):
        from ctypes import windll
        sw = windll.user32.GetSystemMetrics(0)
        sh = windll.user32.GetSystemMetrics(1)

        x1 = int(sw * 0.70)
        y1 = int(sh * 0.0)
        x2 = sw
        y2 = int(sh * 0.20)
        monitor = {"top": y1, "left": x1, "width": x2 - x1, "height": y2 - y1}

        # Minimale Breite für einen Zonen-Namen (ca. 5.5% der Bildschirmbreite)
        min_width_threshold = int(sw * 0.055)

        with mss.mss() as sct:
            while not self.stop_event.is_set():
                try:
                    if not self.templates:
                        time.sleep(2)
                        continue

                    sct_img = sct.grab(monitor)
                    screen_bgr = np.array(sct_img)[:, :, :3]

                    gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
                    _, screen_binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

                    # 1. Breiten-Filter (Schützt vor Rauschen bei ausgeschalteter Karte)
                    kernel = np.ones((5, 40), np.uint8)
                    dilated = cv2.dilate(screen_binary, kernel, iterations=1)
                    contours_dilated, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                    has_wide_text = False
                    if contours_dilated:
                        for cnt in contours_dilated:
                            rx, ry, rw, rh = cv2.boundingRect(cnt)
                            if rw > min_width_threshold and rh > 8:
                                has_wide_text = True
                                break

                    if not has_wide_text:
                        # Kein breiter Text = Karte ist aus und kein Menü stört. Gedächtnis behalten.
                        time.sleep(1.0)
                        continue

                    # 2. Anchor-Filter (Der perfekte Inventar-Blocker)
                    contours, _ = cv2.findContours(screen_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    top_right_margin_x = int(sw * 0.08)
                    top_right_margin_y = int(sh * 0.08)

                    anchor_letters = 0
                    if contours:
                        for cnt in contours:
                            rx, ry, rw, rh = cv2.boundingRect(cnt)
                            if 2 <= rw <= 40 and 5 <= rh <= 40:
                                dist_to_right = monitor["width"] - (rx + rw)
                                if dist_to_right < top_right_margin_x and ry < top_right_margin_y:
                                    anchor_letters += 1

                    if anchor_letters < 2:
                        # Breiter Text (z.B. "INVENTAR") ist da, aber die Minimap-Ecke ist leer.
                        # -> Inventar/Menü ist offen! Gedächtnis behalten.
                        time.sleep(1.0)
                        continue

                    # --- Ab hier: Karte ist zu 100% offen und wir können Zonen checken ---
                    best_zone = "Unbekannt"
                    highest_score = 0.0

                    for name, tmpl_bin, tmpl_px in self.templates:
                        th, tw = tmpl_bin.shape
                        if th > screen_binary.shape[0] or tw > screen_binary.shape[1]:
                            continue

                        res = cv2.matchTemplate(screen_binary, tmpl_bin, cv2.TM_CCOEFF_NORMED)
                        loc = np.where(res >= 0.55)

                        for pt in zip(*loc[::-1]):
                            matched_area = screen_binary[pt[1]:pt[1] + th, pt[0]:pt[0] + tw]

                            intersection = cv2.bitwise_and(matched_area, tmpl_bin)
                            overlap_px = cv2.countNonZero(intersection)
                            area_px = cv2.countNonZero(matched_area)

                            if overlap_px < (tmpl_px * 0.85):
                                continue

                            noise_px = area_px - overlap_px
                            if noise_px > (tmpl_px * 0.60):
                                continue

                            score = overlap_px / float(max(1, tmpl_px))
                            if score > highest_score:
                                highest_score = score
                                best_zone = name

                    # Da wir durch unsere Filter sicher sind, dass es sich um die Karte handelt,
                    # können wir unbekannte Zonen auch wieder sicher als "Unbekannt" ausgeben.
                    # Das triggert dann im Overlay sofort das "?" zum Neuanlegen!
                    self.current_zone = best_zone
                    time.sleep(1.0)

                except Exception as e:
                    print(f"Zone Watcher Error: {e}")
                    time.sleep(2)