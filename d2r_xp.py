import time
import math
from PIL import ImageGrab


class XPWatcher:
    def __init__(self, config_data):
        self.config = config_data
        self.session_start_xp = None
        self.current_xp = 0.0

    def _is_xp_gold(self, r, g, b):
        """Prüft extrem präzise, ob ein Pixel das XP-Gold ist."""
        # Gold muss eine gewisse Grundhelligkeit haben
        if r < 130 or g < 100: return False
        # Das Verhältnis muss stimmen: Rot > Grün > Blau
        if not (r > g > b): return False
        # Blau muss bei Gold sehr niedrig sein (Sättigung)
        if b > 80: return False
        # Der Gold-Check: Rot zu Grün Verhältnis (typisch 1.2 - 1.5)
        ratio = r / g if g > 0 else 0
        if not (1.1 < ratio < 1.6): return False
        return True

    def get_current_xp_percent(self):
        start = self.config.get("xp_start")
        end = self.config.get("xp_end")
        if not start or not end: return 0.0

        try:
            # Wir grabben 3 Zeilen um den Klickpunkt, um vertikale Ausreißer zu minimieren
            bbox = (start["x"], start["y"] - 1, end["x"], end["y"] + 2)
            img = ImageGrab.grab(bbox=bbox)
            pixels = img.load()
            width, height = img.size

            fill_point = 0
            # Wir suchen von rechts nach links
            for x in range(width - 3, 0, -1):
                # Wir prüfen den Pixel und seine Nachbarn (Cluster-Check gegen Rauschen)
                count = 0
                for y_off in range(height):
                    r, g, b = pixels[x, y_off]
                    if self._is_xp_gold(r, g, b):
                        count += 1

                # Wenn in der vertikalen Spalte genug Gold gefunden wurde
                if count >= 2:
                    # Sicherheits-Check: Auch der Pixel links davon sollte Gold sein
                    r2, g2, b2 = pixels[x - 1, 1]
                    if self._is_xp_gold(r2, g2, b2):
                        fill_point = x
                        break

            percent = (fill_point / width) * 100
            self.current_xp = round(percent, 2)

            if self.session_start_xp is None and self.current_xp > 0:
                self.session_start_xp = self.current_xp

            return self.current_xp
        except:
            return 0.0

    def estimate_runs_to_level(self, session_run_count):
        if session_run_count < 1 or self.session_start_xp is None:
            return "--"

        total_gained = self.current_xp - self.session_start_xp
        if total_gained <= 0.001:  # Fast kein Fortschritt erkennbar
            return "Warte auf Fortschritt..."

        avg_per_run = total_gained / session_run_count
        remaining = 100.0 - self.current_xp

        if avg_per_run > 0:
            runs_needed = math.ceil(remaining / avg_per_run)
            return str(runs_needed) if runs_needed < 50000 else "> 50k"

        return "--"