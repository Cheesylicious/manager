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
        default_data = {
            "heatmap_coords": [],
            "pickup_delay_ms": 250,
            "consecutive_success": 0,
            "thresholds": {},
            "color_calibration": {
                "r_min": 140,
                "rg_diff_min": 20
            },
            "fp_sources": {}
        }
        if os.path.exists(self.brain_file):
            try:
                with open(self.brain_file, 'r') as f:
                    loaded = json.load(f)
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

    def report_drop_location(self, char_x, char_y, drop_x, drop_y):
        offset_x = drop_x - char_x
        offset_y = drop_y - char_y
        self.data["heatmap_coords"].append({"x": offset_x, "y": offset_y})
        if len(self.data["heatmap_coords"]) > 30:
            self.data["heatmap_coords"].pop(0)
        self._save_brain()

    def get_optimal_roi(self, sw, sh, char_x, char_y):
        if len(self.data["heatmap_coords"]) < 5:
            return None

        min_x, max_x = 0, 0
        min_y, max_y = 0, 0

        for coord in self.data["heatmap_coords"]:
            if coord["x"] < min_x: min_x = coord["x"]
            if coord["x"] > max_x: max_x = coord["x"]
            if coord["y"] < min_y: min_y = coord["y"]
            if coord["y"] > max_y: max_y = coord["y"]

        pad = 100
        roi_left = max(0, int(char_x + min_x - pad))
        roi_top = max(0, int(char_y + min_y - pad))
        roi_width = min(sw - roi_left, int((max_x - min_x) + (pad * 2)))
        roi_height = min(sh - roi_top, int((max_y - min_y) + (pad * 2)))

        return {"top": roi_top, "left": roi_left, "width": roi_width, "height": roi_height}

    def report_pickup_success(self, success):
        current_delay = self.data["pickup_delay_ms"]
        if success:
            self.data["consecutive_success"] += 1
            if self.data["consecutive_success"] >= 3:
                self.data["pickup_delay_ms"] = max(50, current_delay - 5)
                self.data["consecutive_success"] = 0
        else:
            self.data["consecutive_success"] = 0
            self.data["pickup_delay_ms"] = min(600, current_delay + 20)
        self._save_brain()

    def get_pickup_delay(self):
        base_ms = self.data["pickup_delay_ms"]
        import random
        humanized_ms = random.uniform(base_ms * 0.9, base_ms * 1.1)
        return humanized_ms / 1000.0

    def get_threshold(self, rune_name):
        clean_name = rune_name.lower().strip()
        base_thresh = 0.86 if len(clean_name) <= 3 else 0.80
        return self.data["thresholds"].get(clean_name, base_thresh)

    def report_false_positive(self, rune_name, reported_confidence):
        clean_name = rune_name.lower().strip()
        current_thresh = self.get_threshold(clean_name)

        penalty = 0.05 if len(clean_name) <= 3 else 0.03
        new_thresh = min(0.98, max(current_thresh, reported_confidence + penalty))
        self.data["thresholds"][clean_name] = round(new_thresh, 3)

        current_r = self.data["color_calibration"].get("r_min", 140)
        current_rg = self.data["color_calibration"].get("rg_diff_min", 20)

        self.data["color_calibration"]["r_min"] = min(190, current_r + 4)
        self.data["color_calibration"]["rg_diff_min"] = min(60, current_rg + 3)

        self._save_brain()

    def report_misclassification(self, predicted_rune, actual_rune, reported_confidence):
        pred_clean = predicted_rune.lower().strip()
        act_clean = actual_rune.lower().strip()

        # ANPASSUNG: Wir setzen den Threshold der FALSCH erkannten Rune garantiert über die gemessene Konfidenz
        current_pred_thresh = self.get_threshold(pred_clean)
        new_pred_thresh = min(0.99, max(current_pred_thresh, reported_confidence + 0.015))
        self.data["thresholds"][pred_clean] = round(new_pred_thresh, 3)

        # Die tatsächliche (richtige) Rune machen wir toleranter
        current_act_thresh = self.get_threshold(act_clean)
        new_act_thresh = max(0.65, current_act_thresh - 0.01)
        self.data["thresholds"][act_clean] = round(new_act_thresh, 3)

        self._save_brain()

    def report_custom_false_positive(self, predicted_rune, actual_item, reported_confidence):
        clean_pred = predicted_rune.lower().strip()
        actual_item = actual_item.strip()

        current_thresh = self.get_threshold(clean_pred)
        penalty = 0.04 if len(clean_pred) <= 3 else 0.02
        new_thresh = min(0.98, max(current_thresh, reported_confidence + penalty))
        self.data["thresholds"][clean_pred] = round(new_thresh, 3)

        if "fp_sources" not in self.data:
            self.data["fp_sources"] = {}
        if actual_item not in self.data["fp_sources"]:
            self.data["fp_sources"][actual_item] = 0

        self.data["fp_sources"][actual_item] += 1
        self._save_brain()

    def update_color_calibration(self, new_r_min, new_rg_diff):
        if "color_calibration" not in self.data:
            self.data["color_calibration"] = {}
        self.data["color_calibration"]["r_min"] = new_r_min
        self.data["color_calibration"]["rg_diff_min"] = new_rg_diff
        self._save_brain()