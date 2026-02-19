import time
import threading
import math
import winsound
import os
import sys
import cv2
import numpy as np
from PIL import ImageGrab

# --- CONFIG ---
# Ordnername für die Referenzbilder
TEMPLATE_FOLDER = "runes_filter"


class DropWatcher:
    def __init__(self, config_data):
        self.running = False
        self.thread = None
        self.stop_event = threading.Event()
        self.config = config_data

        self.active = config_data.get("drop_alert_active", False)
        # Cooldown verhindert Spam beim gleichen Drop
        self.last_alert = 0
        self.cooldown = 3.0

        # Templates laden
        self.templates = []
        self._load_templates()

    def _load_templates(self):
        """Lädt alle Bilder aus dem runes_filter Ordner in den RAM."""
        self.templates = []

        # Pfad finden (auch in der EXE oder Dev-Umgebung)
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        folder_path = os.path.join(base_path, TEMPLATE_FOLDER)

        if not os.path.exists(folder_path):
            # Erstelle Ordner, falls er fehlt, damit der User weiß, wo die Bilder hinmüssen
            try:
                os.makedirs(folder_path)
                print(f"[DropWatcher] Ordner '{TEMPLATE_FOLDER}' erstellt. Bitte Bilder hier ablegen!")
            except:
                pass
            return

        print(f"[DropWatcher] Lade Filter-Bilder aus '{folder_path}'...")
        for f in os.listdir(folder_path):
            if f.lower().endswith(('.png', '.jpg', '.bmp')):
                full_path = os.path.join(folder_path, f)
                # cv2.imread lädt Bilder als BGR
                tmpl = cv2.imread(full_path)
                if tmpl is not None:
                    self.templates.append((f, tmpl))
                    print(f" -> Geladen: {f}")

        if not self.templates:
            print("[DropWatcher] WARNUNG: Keine Referenzbilder gefunden! Alarm nur auf Farbe.")

    def update_config(self, is_active):
        self.active = is_active
        if self.active and not self.running:
            self.start()
        elif not self.active and self.running:
            self.stop()

    def start(self):
        if self.active and not self.running:
            # Templates neu laden beim Start (falls User neue Bilder hinzugefügt hat)
            self._load_templates()
            self.running = True
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._scan_loop, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        self.stop_event.set()

    def _is_orange_pixel(self, r, g, b):
        """Schneller Vorab-Check auf Orange/Gold Pixel"""
        if r < 140: return False
        if not (r > g > b): return False
        # D2R Rune Orange Spektrum
        if not (20 < (r - g) < 120): return False
        return True

    def _scan_loop(self):
        from ctypes import windll
        user32 = windll.user32
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)

        # Scan-Bereich (Mitte, ignoriert Ränder für Performance)
        bbox = (int(sw * 0.15), int(sh * 0.15), int(sw * 0.85), int(sh * 0.85))

        while not self.stop_event.is_set():
            if self.active:
                try:
                    now = time.time()
                    if now - self.last_alert > self.cooldown:

                        # 1. Screenshot machen
                        pil_img = ImageGrab.grab(bbox=bbox)
                        # Umwandlung für OpenCV (RGB -> BGR)
                        screen_np = np.array(pil_img)
                        screen_bgr = cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR)

                        found_match = False

                        # A) Wenn wir Templates haben: Präziser Abgleich
                        if self.templates:
                            found_match = self._check_templates(screen_bgr)

                        # B) Fallback: Wenn KEINE Templates da sind, nimm "dumme" Farberkennung
                        # (Damit der User wenigstens irgendeinen Alarm bekommt)
                        else:
                            found_match = self._check_color_fallback(pil_img)

                        if found_match:
                            self._trigger_alarm()

                    time.sleep(0.3)  # 3-4x pro Sekunde reicht völlig
                except Exception as e:
                    print(f"Drop Watcher Error: {e}")
                    time.sleep(1)
            else:
                time.sleep(1)

    def _check_templates(self, screen_img):
        """Prüft das Bild gegen alle geladenen Templates (High Runes)"""
        best_val = 0
        best_name = ""

        for name, tmpl in self.templates:
            # Match Template
            # TM_CCOEFF_NORMED liefert Werte zwischen -1 und 1 (1 = Perfekt)
            res = cv2.matchTemplate(screen_img, tmpl, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

            # Schwellenwert 0.9 = 90% Übereinstimmung (sehr sicher)
            if max_val > 0.90:
                print(f"[DropWatcher] TREFFER: {name} ({round(max_val * 100, 1)}%)")
                return True

        return False

    def _check_color_fallback(self, pil_img):
        """Nur Farbe prüfen (wenn Ordner leer ist)"""
        # Schneller Pixel-Scan (Stride 20)
        pixels = pil_img.load()
        w, h = pil_img.size
        for y in range(0, h, 20):
            for x in range(0, w, 20):
                r, g, b = pixels[x, y]
                if self._is_orange_pixel(r, g, b):
                    # Kurzer Cluster-Check gegen Rauschen
                    count = 0
                    for k in range(1, 5):
                        if x + k < w and self._is_orange_pixel(*pixels[x + k, y]): count += 1

                    if count >= 2:
                        print("[DropWatcher] Unbekanntes oranges Item gefunden (Color-Mode)")
                        return True
        return False

    def _trigger_alarm(self):
        self.last_alert = time.time()
        # Spezieller Sound für High Rune
        winsound.Beep(1500, 80)
        winsound.Beep(1500, 80)
        winsound.Beep(2500, 300)