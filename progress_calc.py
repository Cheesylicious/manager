import time
import math
from PIL import ImageGrab

try:
    from d2_exp_data import get_exp_needed_for_next_level, format_exp
except ImportError:
    get_exp_needed_for_next_level = None
    format_exp = None


class XPWatcher:
    def __init__(self, config_data):
        self.config = config_data
        self.reset()

    def reset(self):
        """Setzt alle Session-Daten für die EXP-Berechnung zurück."""
        self.session_start_xp = None
        self.session_start_time = None
        self.current_xp_percent = 0.0
        self.current_xph_display = "0.0"
        self.xph_history = []  # Für gleitenden Durchschnitt zur Glättung

    def get_current_xp_percent(self, current_level=None):
        start = self.config.get("xp_start")
        end = self.config.get("xp_end")

        if not start or not end:
            return self.current_xp_percent, self.current_xph_display

        try:
            x1, x2 = sorted([int(start["x"]), int(end["x"])])
            y1, y2 = sorted([int(start["y"]), int(end["y"])])

            y_mid = (y1 + y2) // 2

            # Scan-Bereich (10 Pixel Höhe), um leicht ungenaue Klicks zu verzeihen.
            bbox = (x1, max(0, y_mid - 5), x2, y_mid + 5)
            img = ImageGrab.grab(bbox=bbox)
            pixels = img.load()
            width, height = img.size

            if width < 10: return self.current_xp_percent, self.current_xph_display

            last_filled_x = 0
            found_any_gold = False

            # Tolerantere Farberkennung der XP-Leiste
            for x in range(width):
                is_filled = False
                for y in range(height):
                    r, g, b = pixels[x, y]
                    if r > 80 and g > 65 and (int(r) - int(b)) > 20 and (int(g) - int(b)) > 15:
                        is_filled = True
                        found_any_gold = True
                        break

                if is_filled:
                    last_filled_x = x
                elif found_any_gold and x > last_filled_x + 5:
                    break

            # Anti-Blackout Schutz
            if not found_any_gold and self.current_xp_percent > 5.0:
                return self.current_xp_percent, self.current_xph_display

            percent = (last_filled_x / float(max(1, width - 1))) * 100.0
            self.current_xp_percent = round(percent, 2)

            if self.session_start_xp is None and self.current_xp_percent > 0:
                self.session_start_xp = self.current_xp_percent
                self.session_start_time = time.time()

            if self.session_start_xp is not None and self.session_start_time is not None:
                gained_percent = self.current_xp_percent - self.session_start_xp
                elapsed_sec = time.time() - self.session_start_time

                # Erst nach 5 Sekunden stabilen Werten anzeigen
                if gained_percent > 0 and elapsed_sec > 5:
                    percent_per_sec = gained_percent / elapsed_sec
                    instant_percent_ph = percent_per_sec * 3600

                    self.xph_history.append(instant_percent_ph)
                    if len(self.xph_history) > 10:
                        self.xph_history.pop(0)

                    avg_percent_ph = sum(self.xph_history) / len(self.xph_history)

                    # INNOVATION: Wenn das Level bekannt ist, rechne in echte Zahlen um!
                    if current_level and get_exp_needed_for_next_level:
                        try:
                            lvl = int(current_level)
                            exp_needed = get_exp_needed_for_next_level(lvl)
                            if exp_needed > 0:
                                # Reale XP pro Stunde berechnen
                                real_exp_ph = exp_needed * (avg_percent_ph / 100.0)
                                self.current_xph_display = f"{format_exp(real_exp_ph)}"
                            else:
                                self.current_xph_display = f"{round(avg_percent_ph, 2)}%"
                        except ValueError:
                            self.current_xph_display = f"{round(avg_percent_ph, 2)}%"
                    else:
                        self.current_xph_display = f"{round(avg_percent_ph, 2)}%"

            return self.current_xp_percent, self.current_xph_display

        except Exception as e:
            print(f"XP Tracker Fehler: {e}")
            return self.current_xp_percent, self.current_xph_display

    def estimate_runs_to_level(self, session_run_count):
        if session_run_count < 1 or self.session_start_xp is None:
            return "--"

        gained_percent = self.current_xp_percent - self.session_start_xp

        # Automatischer Reset bei Tod (EXP-Verlust)
        if gained_percent < 0:
            self.reset()
            return "Tod! Reset."

        if gained_percent <= 0.005:
            return "..."

        avg_percent_per_run = gained_percent / session_run_count
        remaining_percent = 100.0 - self.current_xp_percent

        if avg_percent_per_run > 0:
            runs_needed = math.ceil(remaining_percent / avg_percent_per_run)
            return str(runs_needed) if runs_needed <= 9999 else "> 9k"

        return "--"