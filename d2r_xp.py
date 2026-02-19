import time
import math
from PIL import ImageGrab


class XPWatcher:
    def __init__(self, config_data):
        self.config = config_data
        self.session_start_xp = None
        self.current_xp = 0.0

    def _is_xp_gold(self, r, g, b):
        """
        Verbesserte Heuristik für D2R XP-Gold.
        Toleranter gegenüber Helligkeitsschwankungen, aber streng bei der Farbe (Orange-Gold).
        """
        # 1. Grundhelligkeit prüfen (darf nicht schwarz sein)
        if r < 50: return False

        # 2. Kanal-Hierarchie für Gold/Orange: Rot > Grün > Blau
        if not (r > g and g > b): return False

        # 3. Farbton-Check über Verhältnisse (Ratio)
        # Rot zu Grün: Gold liegt meist zwischen 1.1 (Gelb) und 1.6 (Orange)
        if g == 0: return False  # Division durch Null verhindern
        rg_ratio = r / g

        # D2R XP Balken ist ein sattes Gold-Orange
        if not (1.05 < rg_ratio < 1.8): return False

        # 4. Sättigungs-Check (Blau muss deutlich niedriger sein als Rot)
        # Wenn Blau zu nah an Rot ist, ist es Grau/Weiß
        if b > (r * 0.7): return False

        return True

    def get_current_xp_percent(self):
        start = self.config.get("xp_start")
        end = self.config.get("xp_end")

        # Sicherheitscheck: Konfiguration vorhanden?
        if not start or not end:
            return 0.0

        try:
            # Koordinaten normalisieren (falls User von rechts nach links geklickt hat)
            x1, x2 = sorted([int(start["x"]), int(end["x"])])
            y1, y2 = sorted([int(start["y"]), int(end["y"])])

            # Bereich etwas erweitern (Buffer), aber mindestens 1px hoch/breit
            # Wir nehmen die Y-Mitte und scannen +/- 2 Pixel
            y_mid = (y1 + y2) // 2
            bbox = (x1, y_mid - 2, x2, y_mid + 3)

            # Bildbereich erfassen
            img = ImageGrab.grab(bbox=bbox)
            pixels = img.load()
            width, height = img.size

            if width < 5: return 0.0  # Zu schmal für Analyse

            fill_point = 0
            found_bar = False

            # Scan von RECHTS nach LINKS um das Ende des Balkens zu finden
            # Wir überspringen die allerletzten Pixel rechts, um Rauschen am Rand zu meiden
            for x in range(width - 2, 0, -1):
                gold_pixels_in_column = 0

                # Vertikaler Scan an Position x (Rauschunterdrückung)
                for y in range(height):
                    try:
                        r, g, b = pixels[x, y]
                        if self._is_xp_gold(r, g, b):
                            gold_pixels_in_column += 1
                    except IndexError:
                        continue

                # Wenn mehr als 30% der vertikalen Linie Gold sind, haben wir den Balken gefunden
                if gold_pixels_in_column >= 2:
                    # Doppel-Check: Ist der Pixel links davon auch Gold? (Vermeidet einzelne Artefakte)
                    check_x = max(0, x - 2)
                    check_gold = 0
                    for check_y in range(height):
                        r, g, b = pixels[check_x, check_y]
                        if self._is_xp_gold(r, g, b):
                            check_gold += 1

                    if check_gold >= 1:
                        fill_point = x
                        found_bar = True
                        break

            # Prozentberechnung
            if found_bar:
                percent = (fill_point / width) * 100
                # Glättung: Runden auf 2 Nachkommastellen
                self.current_xp = round(percent, 2)
            else:
                # Wenn gar kein Gold gefunden wurde, ist der Balken wohl leer (oder Anfang)
                # Wir setzen es nur auf 0, wenn wir sicher sind, dass es kein Fehler war
                pass

                # Session Startwert setzen (für "Runs to Level")
            if self.session_start_xp is None and self.current_xp > 0:
                self.session_start_xp = self.current_xp

            return self.current_xp

        except Exception as e:
            print(f"XP Watcher Fehler: {e}")
            return 0.0

    def estimate_runs_to_level(self, session_run_count):
        """Berechnet verbleibende Runs basierend auf dem Fortschritt der Session."""
        if session_run_count < 1 or self.session_start_xp is None:
            return "--"

        # Fortschritt seit Start des Trackers
        gained = self.current_xp - self.session_start_xp

        # Abfangen von negativen Werten (z.B. Tod oder Messfehler)
        if gained < 0:
            self.session_start_xp = self.current_xp  # Reset bei Tod
            return "Reset"

        if gained <= 0.01:  # Zu wenig Daten
            return "Warte..."

        avg_per_run = gained / session_run_count
        remaining_xp = 100.0 - self.current_xp

        if avg_per_run > 0:
            runs_needed = math.ceil(remaining_xp / avg_per_run)
            # Begrenzung der Anzeige
            if runs_needed > 9999: return "> 9k"
            return str(runs_needed)

        return "--"