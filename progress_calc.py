import time
import math
from PIL import ImageGrab


class XPWatcher:
    def __init__(self, config_data):
        self.config = config_data
        self.reset()

    def reset(self):
        """Setzt alle Session-Daten zurück."""
        self.session_start_xp = None
        self.session_start_time = None
        self.current_xp = 0.0
        self.current_xph = "0.0"
        self.history_xph = []  # Für gleitenden Durchschnitt

    def get_current_xp_percent(self):
        start = self.config.get("xp_start")
        end = self.config.get("xp_end")

        if not start or not end:
            return self.current_xp, self.current_xph

        try:
            x1, x2 = sorted([int(start["x"]), int(end["x"])])
            y1, y2 = sorted([int(start["y"]), int(end["y"])])

            y_mid = (y1 + y2) // 2
            # Kleinerer vertikaler Scanbereich für mehr Performance
            bbox = (x1, max(0, y_mid - 2), x2, y_mid + 2)
            img = ImageGrab.grab(bbox=bbox)
            pixels = img.load()
            width, height = img.size

            if width < 10: return self.current_xp, self.current_xph

            last_filled_x = 0
            found_any_gold = False

            # Präziserer Scan der Gold-Pixel der XP-Leiste
            for x in range(width):
                is_filled = False
                for y in range(height):
                    r, g, b = pixels[x, y]
                    # Optimierte Farberkennung für die XP-Leiste
                    if r > 90 and g > 75 and (int(r) - int(b)) > 25:
                        is_filled = True
                        found_any_gold = True
                        break
                if is_filled:
                    last_filled_x = x
                elif found_any_gold and x > last_filled_x + 5:  # Lücke gefunden
                    break

            if not found_any_gold and self.current_xp > 5.0:
                return self.current_xp, self.current_xph

            percent = (last_filled_x / float(max(1, width - 1))) * 100.0
            self.current_xp = round(percent, 2)

            if self.session_start_xp is None and self.current_xp > 0:
                self.session_start_xp = self.current_xp
                self.session_start_time = time.time()

            if self.session_start_xp is not None and self.session_start_time is not None:
                gained = self.current_xp - self.session_start_xp
                elapsed_sec = time.time() - self.session_start_time

                if gained > 0 and elapsed_sec > 5:
                    per_sec = gained / elapsed_sec
                    instant_xph = per_sec * 3600

                    # Moving Average über die letzten 5 Messungen für Stabilität
                    self.history_xph.append(instant_xph)
                    if len(self.history_xph) > 5: self.history_xph.pop(0)

                    avg_xph = sum(self.history_xph) / len(self.history_xph)
                    self.current_xph = str(round(avg_xph, 1))

            return self.current_xp, self.current_xph

        except Exception as e:
            print(f"XP Tracker Fehler: {e}")
            return self.current_xp, self.current_xph

    def estimate_runs_to_level(self, session_run_count):
        if session_run_count < 1 or self.session_start_xp is None:
            return "--"

        gained = self.current_xp - self.session_start_xp

        if gained < 0:  # Tod-Schutz
            self.session_start_xp = self.current_xp
            self.session_start_time = time.time()
            self.current_xph = "0.0"
            return "Reset"

        if gained <= 0.005:
            return "..."

        avg_per_run = gained / session_run_count
        remaining_xp = 100.0 - self.current_xp

        if avg_per_run > 0:
            runs_needed = math.ceil(remaining_xp / avg_per_run)
            return str(runs_needed) if runs_needed <= 9999 else ">9k"

        return "--"