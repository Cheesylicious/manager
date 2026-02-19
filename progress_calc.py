import time
import math
from PIL import ImageGrab


class XPWatcher:
    def __init__(self, config_data):
        self.config = config_data
        self.session_start_xp = None
        self.session_start_time = None
        self.current_xp = 0.0
        self.current_xph = "0.0"

    def get_current_xp_percent(self):
        start = self.config.get("xp_start")
        end = self.config.get("xp_end")

        if not start or not end:
            return self.current_xp, self.current_xph

        try:
            x1, x2 = sorted([int(start["x"]), int(end["x"])])
            y1, y2 = sorted([int(start["y"]), int(end["y"])])

            y_mid = (y1 + y2) // 2

            bbox = (x1, max(0, y_mid - 3), x2, y_mid + 4)
            img = ImageGrab.grab(bbox=bbox)
            pixels = img.load()
            width, height = img.size

            if width < 10: return self.current_xp, self.current_xph

            last_filled_x = 0
            consecutive_empty = 0
            found_any_gold = False

            for x in range(width):
                is_filled = False

                for y in range(height):
                    r, g, b = pixels[x, y]

                    if r > 80 and g > 70 and (int(r) - int(b)) > 20 and (int(g) - int(b)) > 15:
                        is_filled = True
                        found_any_gold = True
                        break

                if is_filled:
                    last_filled_x = x
                    consecutive_empty = 0
                else:
                    consecutive_empty += 1

                if consecutive_empty > 25:
                    break

            # ANTI-BLACKOUT SCHUTZ
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

                # OPTIMIERT: Zeigt jetzt schon nach 5 Sekunden (statt 30) die ersten EXP/h Werte an!
                if gained > 0 and elapsed_sec > 5:
                    per_sec = gained / elapsed_sec
                    self.current_xph = str(round(per_sec * 3600, 1))

            return self.current_xp, self.current_xph

        except Exception as e:
            print(f"XP Tracker Fehler: {e}")
            return self.current_xp, self.current_xph

    def estimate_runs_to_level(self, session_run_count):
        if session_run_count < 1 or self.session_start_xp is None:
            return "--"

        gained = self.current_xp - self.session_start_xp

        # Reset falls Spieler in Hell stirbt und EXP verliert
        if gained < 0:
            self.session_start_xp = self.current_xp
            self.session_start_time = time.time()
            self.current_xph = "0.0"
            return "Tod! Reset."

        if gained <= 0.01:
            return "Warte..."

        avg_per_run = gained / session_run_count
        remaining_xp = 100.0 - self.current_xp

        if avg_per_run > 0:
            runs_needed = math.ceil(remaining_xp / avg_per_run)
            if runs_needed > 9999: return "> 9k"
            return str(runs_needed)

        return "--"