import os
import json
import time
import math
import sys


class AIEngine:
    def __init__(self):
        if getattr(sys, 'frozen', False):
            self.base_path = os.path.dirname(sys.executable)
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))

        self.brain_file = os.path.join(self.base_path, "ai_brain.json")
        self.data = self._load_brain()

    def _load_brain(self):
        # Hier werden die grundlegenden "Instinkte" des Programms festgelegt,
        # falls noch keine Erfahrungswerte (ai_brain.json) vorliegen.
        default_data = {
            "heatmap_coords": [],  # Speichert die letzten X/Y Offsets von Drops
            "pickup_delay_ms": 250,  # Startwert für den Klick-Delay
            "consecutive_success": 0,  # Zählt erfolgreiche Pickups am Stück
            "thresholds": {},  # Dynamische Schwellenwerte pro Rune (z.B. {"Ber": 0.81})

            # --- INNOVATION: Feature 5 (Auto-Color Masking) ---
            "color_calibration": {
                "r_min": 140,  # Standard-Rot-Schwellenwert
                "rg_diff_min": 20  # Standard-Abstand zwischen Rot und Grün
            }
        }
        if os.path.exists(self.brain_file):
            try:
                with open(self.brain_file, 'r') as f:
                    loaded = json.load(f)
                    # Überprüft, ob das geladene Gehirn alle neuen Features hat.
                    # Falls nicht, werden sie nahtlos hinzugefügt.
                    for k, v in default_data.items():
                        if k not in loaded:
                            loaded[k] = v
                    return loaded
            except:
                pass
        return default_data

    def _save_brain(self):
        try:
            with open(self.brain_file, 'w') as f:
                json.dump(self.data, f, indent=4)
        except:
            pass

    # --- 1. DYNAMIC ROI (Heatmap) ---
    def report_drop_location(self, char_x, char_y, drop_x, drop_y):
        """Speichert die relative Position eines Drops zur Spielfigur."""
        offset_x = drop_x - char_x
        offset_y = drop_y - char_y

        self.data["heatmap_coords"].append({"x": offset_x, "y": offset_y})
        # Wir merken uns nur die letzten 30 Drops, damit die KI sich an neue Farm-Routen anpasst
        if len(self.data["heatmap_coords"]) > 30:
            self.data["heatmap_coords"].pop(0)
        self._save_brain()

    def get_optimal_roi(self, sw, sh, char_x, char_y):
        """Berechnet einen extrem kleinen, optimierten Scan-Bereich basierend auf der Historie."""
        if len(self.data["heatmap_coords"]) < 5:
            return None  # Zu wenig Daten, nutze Standard-Bereich

        min_x, max_x = 0, 0
        min_y, max_y = 0, 0

        for coord in self.data["heatmap_coords"]:
            if coord["x"] < min_x: min_x = coord["x"]
            if coord["x"] > max_x: max_x = coord["x"]
            if coord["y"] < min_y: min_y = coord["y"]
            if coord["y"] > max_y: max_y = coord["y"]

        # Gebe eine Bounding-Box (mit 100px Sicherheits-Padding) zurück
        pad = 100
        roi_left = max(0, int(char_x + min_x - pad))
        roi_top = max(0, int(char_y + min_y - pad))
        roi_width = min(sw - roi_left, int((max_x - min_x) + (pad * 2)))
        roi_height = min(sh - roi_top, int((max_y - min_y) + (pad * 2)))

        return {"top": roi_top, "left": roi_left, "width": roi_width, "height": roi_height}

    # --- 2. ADAPTIVE DELAY (Ping Optimierung) ---
    def report_pickup_success(self, success):
        """Passt den Klick-Delay basierend auf dem Erfolg an."""
        current_delay = self.data["pickup_delay_ms"]

        if success:
            self.data["consecutive_success"] += 1
            # Wenn wir 3x am Stück erfolgreich waren, machen wir das Tool 5ms schneller (aggressiver)
            if self.data["consecutive_success"] >= 3:
                self.data["pickup_delay_ms"] = max(50, current_delay - 5)
                self.data["consecutive_success"] = 0
        else:
            self.data["consecutive_success"] = 0
            # Wenn wir verfehlt haben (z.B. Server-Lag), machen wir das Tool 20ms langsamer (sicherer)
            self.data["pickup_delay_ms"] = min(600, current_delay + 20)

        self._save_brain()

    def get_pickup_delay(self):
        """Gibt den perfekten Klick-Delay in Sekunden zurück (inkl. minimaler Humanisierung)."""
        base_ms = self.data["pickup_delay_ms"]
        # Schwankt leicht um +- 10%, um nicht wie ein Bot auszusehen
        import random
        humanized_ms = random.uniform(base_ms * 0.9, base_ms * 1.1)
        return humanized_ms / 1000.0

    # --- 3. DYNAMIC THRESHOLDS (Fehlalarm-Prävention) ---
    def get_threshold(self, rune_name):
        """Gibt die benötigte Übereinstimmungs-Genauigkeit für ein Item zurück."""
        clean_name = rune_name.lower().strip()
        # 0.80 ist der Standard. Falls die KI gelernt hat, wird dieser Wert genutzt.
        return self.data["thresholds"].get(clean_name, 0.80)

    def report_false_positive(self, rune_name, reported_confidence):
        """
        Hebt die Genauigkeitsschwelle für ein Item an, wenn es oft zu Fehlalarmen führt.
        Wird später aufgerufen, wenn über das Popup eine Falschmeldung reinkommt.
        """
        clean_name = rune_name.lower().strip()
        current_thresh = self.get_threshold(clean_name)

        # Erhöhe die Schwelle minimal über den Wert, der den Fehlalarm ausgelöst hat
        # Maximiere bei 0.92, da das Item sonst evtl. gar nicht mehr gefunden wird
        new_thresh = min(0.92, max(current_thresh, reported_confidence + 0.02))

        self.data["thresholds"][clean_name] = round(new_thresh, 3)
        self._save_brain()

    # --- 4. COLOR CALIBRATION HELPER ---
    def update_color_calibration(self, new_r_min, new_rg_diff):
        """Sicheres Speichern der vom Scanner berechneten Lichtverhältnisse."""
        if "color_calibration" not in self.data:
            self.data["color_calibration"] = {}

        self.data["color_calibration"]["r_min"] = new_r_min
        self.data["color_calibration"]["rg_diff_min"] = new_rg_diff
        self._save_brain()