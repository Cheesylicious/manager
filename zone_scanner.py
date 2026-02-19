import time
import threading
import os
import sys
import cv2
import numpy as np
import mss

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
                zone_name = os.path.splitext(f)[0].replace("_", " ")
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
                    _, tmpl_binary = cv2.threshold(gray, 170, 255, cv2.THRESH_BINARY)

                    contours, _ = cv2.findContours(tmpl_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    if contours:
                        x, y, w, h = cv2.boundingRect(np.vstack(contours))
                        tmpl_cropped = tmpl_binary[y:y + h, x:x + w]

                        tmpl_px = cv2.countNonZero(tmpl_cropped)
                        if tmpl_px > 10:
                            # Wir speichern jetzt wieder die exakte Pixelanzahl des Wortes ab
                            self.templates.append((zone_name, tmpl_cropped, tmpl_px))
                            print(f" -> Zone geladen: {zone_name} ({tmpl_px} Px)")

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

        with mss.mss() as sct:
            while not self.stop_event.is_set():
                try:
                    if not self.templates:
                        time.sleep(2)
                        continue

                    sct_img = sct.grab(monitor)
                    screen_bgr = np.array(sct_img)[:, :, :3]

                    gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
                    _, screen_binary = cv2.threshold(gray, 170, 255, cv2.THRESH_BINARY)

                    best_zone = "Unbekannt"
                    highest_score = 0.0

                    for name, tmpl_bin, tmpl_px in self.templates:
                        th, tw = tmpl_bin.shape
                        if th > screen_binary.shape[0] or tw > screen_binary.shape[1]:
                            continue

                        # Grober Suchlauf
                        res = cv2.matchTemplate(screen_binary, tmpl_bin, cv2.TM_CCOEFF_NORMED)
                        loc = np.where(res >= 0.35)

                        for pt in zip(*loc[::-1]):
                            matched_area = screen_binary[pt[1]:pt[1] + th, pt[0]:pt[0] + tw]

                            intersection = cv2.bitwise_and(matched_area, tmpl_bin)
                            overlap_px = cv2.countNonZero(intersection)
                            area_px = cv2.countNonZero(matched_area)

                            # REGEL 1: Mindestens 75% des Textes müssen sichtbar sein
                            if overlap_px < (tmpl_px * 0.75):
                                continue

                            # REGEL 2: Der Bereich darf nicht viel mehr weiße Pixel enthalten als das Template.
                            # (Das verhindert, dass Eishochland als Teil von Harrogath gewertet wird!)
                            if area_px > (tmpl_px * 1.35):
                                continue

                            # Punkte berechnen
                            score = overlap_px / float(max(1, tmpl_px))
                            if score > highest_score:
                                highest_score = score
                                best_zone = name

                    self.current_zone = best_zone
                    time.sleep(1.0)

                except Exception as e:
                    print(f"Zone Watcher Error: {e}")
                    time.sleep(2)