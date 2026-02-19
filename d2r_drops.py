import time
import threading
import math
import winsound
from PIL import ImageGrab


class DropWatcher:
    def __init__(self, config_data):
        self.running = False
        self.thread = None
        self.stop_event = threading.Event()

        # Einstellungen
        self.active = config_data.get("drop_alert_active", False)
        self.last_alert = 0
        self.cooldown = 4.0  # Sekunden Ruhe zwischen Alarmen

        # Farbeinstellungen für High Runes (Orange/Gold)
        # Typisches D2R Orange: R=190-255, G=130-180, B=20-60
        self.min_rgb = (150, 90, 0)

    def update_config(self, is_active):
        self.active = is_active
        if self.active and not self.running:
            self.start()
        elif not self.active and self.running:
            self.stop()

    def start(self):
        if self.active and not self.running:
            self.running = True
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._scan_loop, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        self.stop_event.set()

    def _is_rune_color(self, r, g, b):
        # 1. Muss hell genug sein
        if r < 160: return False

        # 2. Rot muss dominant sein, Grün mittel, Blau wenig
        if not (r > g > b): return False

        # 3. Verhältnis Rot zu Grün (Orange-Bereich)
        # Zu viel Grün = Gelb (Rare Item), Zu wenig Grün = Rot (Health/Feuer)
        rg_diff = r - g
        if not (30 < rg_diff < 100): return False

        # 4. Wenig Blau (Sättigung)
        if b > 100: return False

        return True

    def _scan_loop(self):
        # Wir scannen nur die Mitte des Bildschirms (Performance & Relevanz)
        from ctypes import windll
        user32 = windll.user32
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)

        # Bereich: 20% Rand oben/unten/links/rechts ignorieren
        bbox = (int(sw * 0.2), int(sh * 0.2), int(sw * 0.8), int(sh * 0.8))
        step = 12  # Wir prüfen nur jeden 12. Pixel (schneller)

        while not self.stop_event.is_set():
            if self.active:
                try:
                    now = time.time()
                    if now - self.last_alert > self.cooldown:
                        image = ImageGrab.grab(bbox=bbox)
                        width, height = image.size
                        pixels = image.load()

                        found = 0
                        # Scan
                        for y in range(0, height, step):
                            for x in range(0, width, step):
                                r, g, b = pixels[x, y]
                                if self._is_rune_color(r, g, b):
                                    found += 1
                                    # Wenn wir Cluster finden, Alarm!
                                    if found >= 2:
                                        self._trigger_alarm()
                                        break
                            if found >= 2: break

                    time.sleep(0.3)  # 3x pro Sekunde reicht
                except:
                    time.sleep(1)
            else:
                time.sleep(1)

    def _trigger_alarm(self):
        self.last_alert = time.time()
        # Doppel-Ping Sound
        winsound.Beep(1800, 100)
        time.sleep(0.05)
        winsound.Beep(2200, 150)
        print("DROP ALARM!")