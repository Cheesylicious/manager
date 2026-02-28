import time
import threading
import winsound
import os
import sys
import random
import cv2
import numpy as np
import math
import mss
from inventory_verifier import InventoryVerifier
from ai_metrics_engine import AIEngine


def log_debug(msg):
    try:
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        log_file = os.path.join(base_path, "scanner_debug.txt")
        timestamp = time.strftime('%H:%M:%S')
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {msg}\n")
    except:
        pass


log_debug("--- NEUER PROGRAMMSTART ---")

try:
    from rune_snipping_tool import RuneSnippingTool
    from snipping_prompt import SnippingPrompt

    log_debug("Snipping Tools erfolgreich importiert!")
except ImportError as e:
    RuneSnippingTool = None
    SnippingPrompt = None
    log_debug(f"FEHLER: Konnte Snipping Tools nicht laden: {e}")

try:
    from human_input import HumanMouse
except ImportError:
    HumanMouse = None

TEMPLATE_FOLDER = "runes_filter"


class DropWatcher:
    def __init__(self, config_data, drop_callback=None, ui_parent=None):
        self.running = False
        self.thread = None
        self.stop_event = threading.Event()
        self.config = config_data
        self.drop_callback = drop_callback
        self.ui_parent = ui_parent

        self.inv_verifier = InventoryVerifier()
        self.ai = AIEngine()

        self.active = config_data.get("drop_alert_active", False)

        self.last_sound_time = 0
        self.last_ground_log = 0
        self.cooldown = 3.0

        self.last_click_time = 0
        self.active_target_name = None
        self.active_target_count = 0

        self.tracked_items = {}
        self.pending_items = []

        self.active_prompt = None
        self.prompt_active_for_rune = None

        self.templates = []
        self.false_positives_ground = []
        self.false_positives_inv = []

        # --- INNOVATION: Dynamische Farbkalibrierung Variablen ---
        # Werden aus der AI Engine geladen oder haben intelligente Fallbacks
        self.current_r_min = self.ai.data.get("color_calibration", {}).get("r_min", 140)
        self.current_rg_diff_min = self.ai.data.get("color_calibration", {}).get("rg_diff_min", 20)
        # --------------------------------------------------------

        self._load_templates()

    def _get_dynamic_color_mask(self, r, g, b):
        """Erzeugt die Maske basierend auf den von der KI gelernten Lichtverhältnissen."""
        return (r > self.current_r_min) & (r > g) & (g > b) & ((r - g) > self.current_rg_diff_min) & ((r - g) < 120)

    def _calibrate_colors_from_success(self, screen_bgr, abs_x, abs_y, width, height, full_monitor):
        """
        Liest die exakten RGB-Werte an der Stelle aus, an der ein Item WIRKLICH aufgehoben wurde.
        Passt die Schwellenwerte minimal an, um das Umgebungslicht zu kompensieren.
        """
        rel_x = abs_x - full_monitor["left"]
        rel_y = abs_y - full_monitor["top"]

        # Sicherheits-Check, ob die Koordinaten noch im Bild sind
        if rel_y < 0 or rel_x < 0 or rel_y + height > screen_bgr.shape[0] or rel_x + width > screen_bgr.shape[1]:
            return

        # Den Bereich des gefundenen Items ausschneiden
        roi = screen_bgr[rel_y:rel_y + height, rel_x:rel_x + width]

        # Finde den "orangesten" Pixel in diesem Bereich (höchster Rot-Wert mit deutlichem Abstand zu Grün)
        b_roi = roi[:, :, 0].astype(np.int16)
        g_roi = roi[:, :, 1].astype(np.int16)
        r_roi = roi[:, :, 2].astype(np.int16)

        # Wir suchen Pixel, die halbwegs orange sind, um den perfekten zu finden
        potential_oranges = (r_roi > 100) & (r_roi > g_roi) & (g_roi > b_roi)

        if np.any(potential_oranges):
            # Hole den höchsten Rotwert in diesem potentiell orangen Bereich
            max_r = np.max(r_roi[potential_oranges])

            # Finde die Koordinaten dieses Pixels (erster Treffer reicht)
            coords = np.where((r_roi == max_r) & potential_oranges)
            if len(coords[0]) > 0:
                best_y, best_x = coords[0][0], coords[1][0]
                actual_r = r_roi[best_y, best_x]
                actual_g = g_roi[best_y, best_x]

                # Sanfte Annäherung (Erosion) der Kalibrierung an den echten Wert
                target_r_min = max(90, min(180, actual_r - 40))  # 40 Puffer nach unten
                target_rg_diff = max(10, min(50, (actual_r - actual_g) - 10))

                # Wir bewegen unsere aktuellen Schwellenwerte um 1 Einheit in Richtung des Ziels
                if self.current_r_min < target_r_min:
                    self.current_r_min += 1
                elif self.current_r_min > target_r_min:
                    self.current_r_min -= 1

                if self.current_rg_diff_min < target_rg_diff:
                    self.current_rg_diff_min += 1
                elif self.current_rg_diff_min > target_rg_diff:
                    self.current_rg_diff_min -= 1

                # Im Gehirn speichern
                if "color_calibration" not in self.ai.data:
                    self.ai.data["color_calibration"] = {}
                self.ai.data["color_calibration"]["r_min"] = self.current_r_min
                self.ai.data["color_calibration"]["rg_diff_min"] = self.current_rg_diff_min
                self.ai._save_brain()

                log_debug(
                    f"Auto-Color Kalibriert! Neue Thresholds: R_Min={self.current_r_min}, RG_Diff={self.current_rg_diff_min}")

    def _load_templates(self):
        self.templates = []
        self.false_positives_ground = []
        self.false_positives_inv = []

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
        else:
            allowed_runes = self.config.get("allowed_runes", [])
            allowed_clean = [r.lower().replace("-rune", "").strip() for r in allowed_runes]

            for f in os.listdir(folder_path):
                if f.lower().endswith(('.png', '.jpg', '.bmp')):
                    fname_lower = f.lower()
                    clean_name = fname_lower.split('.')[0].replace("-rune", "").replace("_rune", "").strip()

                    if clean_name not in allowed_clean: continue

                    full_path = os.path.join(folder_path, f)
                    tmpl = cv2.imread(full_path)
                    if tmpl is not None:
                        b = tmpl[:, :, 0].astype(np.int16)
                        g = tmpl[:, :, 1].astype(np.int16)
                        r = tmpl[:, :, 2].astype(np.int16)

                        # Nutzen der neuen dynamischen Farbmaske
                        mask = self._get_dynamic_color_mask(r, g, b)

                        tmpl_binary = (mask.astype(np.uint8) * 255)
                        contours, _ = cv2.findContours(tmpl_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        if contours:
                            x, y, w, h = cv2.boundingRect(np.vstack(contours))
                            tmpl_cropped = tmpl_binary[y:y + h, x:x + w]
                            self.templates.append((clean_name.title(), tmpl_cropped))

        fp_folder = os.path.join(base_path, "false_positives")
        if os.path.exists(fp_folder):
            for f in os.listdir(fp_folder):
                if f.lower().endswith(('.png', '.jpg', '.bmp')):
                    full_path = os.path.join(fp_folder, f)
                    tmpl = cv2.imread(full_path)
                    if tmpl is not None:
                        b = tmpl[:, :, 0].astype(np.int16)
                        g = tmpl[:, :, 1].astype(np.int16)
                        r = tmpl[:, :, 2].astype(np.int16)

                        mask = self._get_dynamic_color_mask(r, g, b)

                        if np.any(mask):
                            tmpl_binary = (mask.astype(np.uint8) * 255)
                            contours, _ = cv2.findContours(tmpl_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                            if contours:
                                x, y, w, h = cv2.boundingRect(np.vstack(contours))
                                self.false_positives_ground.append(tmpl_binary[y:y + h, x:x + w])
                        else:
                            gray = cv2.cvtColor(tmpl, cv2.COLOR_BGR2GRAY)
                            self.false_positives_inv.append(gray)

    def update_config(self, is_active):
        self.active = is_active
        if self.active and not self.running:
            self.start()
        elif not self.active and self.running:
            self.stop()

    def start(self):
        if self.active and not self.running:
            self._load_templates()
            self.running = True
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._scan_loop, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        self.stop_event.set()

    def _is_inventory_tooltip(self, match_x, match_y, sw, sh):
        from ctypes import windll, Structure, c_long, byref
        class POINT(Structure):
            _fields_ = [("x", c_long), ("y", c_long)]

        pt = POINT()
        windll.user32.GetCursorPos(byref(pt))

        is_mouse_left = pt.x < (sw / 2)
        is_match_left = match_x < (sw / 2)

        if is_mouse_left == is_match_left:
            if abs(pt.x - match_x) < 550 and abs(pt.y - match_y) < 650:
                return True
        return False

    def _instant_click(self, x, y, sw, sh):
        from ctypes import windll, Structure, c_long, byref, POINTER, c_ulong, sizeof, Union
        class MOUSEINPUT(Structure):
            _fields_ = [("dx", c_long), ("dy", c_long), ("mouseData", c_ulong), ("dwFlags", c_ulong), ("time", c_ulong),
                        ("dwExtraInfo", POINTER(c_ulong))]

        class INPUT_I(Union):
            _fields_ = [("mi", MOUSEINPUT)]

        class INPUT(Structure):
            _fields_ = [("type", c_ulong), ("ii", INPUT_I)]

        nx = int(x * 65535 / sw)
        ny = int(y * 65535 / sh)
        inputs = (INPUT * 3)()
        inputs[0].type = 0
        inputs[0].ii.mi = MOUSEINPUT(nx, ny, 0, 0x0001 | 0x8000, 0, None)
        inputs[1].type = 0
        inputs[1].ii.mi = MOUSEINPUT(nx, ny, 0, 0x0002 | 0x8000, 0, None)
        inputs[2].type = 0
        inputs[2].ii.mi = MOUSEINPUT(nx, ny, 0, 0x0004 | 0x8000, 0, None)

        windll.user32.SendInput(3, inputs, sizeof(INPUT))

    def _check_templates_multi(self, screen_img, abs_offset_x=0, abs_offset_y=0):
        b = screen_img[:, :, 0].astype(np.int16)
        g = screen_img[:, :, 1].astype(np.int16)
        r = screen_img[:, :, 2].astype(np.int16)

        # Nutzen der dynamischen Maske
        mask = self._get_dynamic_color_mask(r, g, b)

        if not np.any(mask):
            return False, []

        screen_binary = (mask.astype(np.uint8) * 255)
        kernel = np.ones((5, 25), np.uint8)
        dilated = cv2.dilate(screen_binary, kernel, iterations=1)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        rois = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w < 10 or h < 5: continue
            pad = 8
            y1 = max(0, y - pad)
            y2 = min(screen_binary.shape[0], y + h + pad)
            x1 = max(0, x - pad)
            x2 = min(screen_binary.shape[1], x + w + pad)
            rois.append((x1, y1, x2, y2))

        if not rois: return False, []

        found_items = []
        for (x1, y1, x2, y2) in rois:
            roi_img = screen_binary[y1:y2, x1:x2]

            is_blacklisted = False
            for fp_bin in self.false_positives_ground:
                fh, fw = fp_bin.shape
                if fh > roi_img.shape[0] or fw > roi_img.shape[1]: continue
                res_fp = cv2.matchTemplate(roi_img, fp_bin, cv2.TM_CCOEFF_NORMED)
                _, max_val_fp, _, _ = cv2.minMaxLoc(res_fp)
                if max_val_fp >= 0.85:
                    is_blacklisted = True
                    break
            if is_blacklisted: continue

            for name, tmpl_bin in self.templates:
                th, tw = tmpl_bin.shape
                if th > roi_img.shape[0] or tw > roi_img.shape[1]: continue

                res = cv2.matchTemplate(roi_img, tmpl_bin, cv2.TM_CCOEFF_NORMED)

                dynamic_threshold = self.ai.get_threshold(name)
                loc = np.where(res >= dynamic_threshold)

                for pt in zip(*loc[::-1]):
                    center_x = abs_offset_x + x1 + pt[0] + tw // 2
                    center_y = abs_offset_y + y1 + pt[1] + th // 2

                    is_duplicate = False
                    for item in found_items:
                        if math.hypot(center_x - item[0], center_y - item[1]) < 80:
                            is_duplicate = True
                            break

                    if not is_duplicate:
                        # Wir speichern nun zusätzlich die Breite/Höhe, um später kalibrieren zu können
                        found_items.append((center_x, center_y, name, tmpl_bin, tw, th))

        return len(found_items) > 0, found_items

    def _trigger_alarm(self):
        def sound_worker():
            winsound.Beep(987, 80)
            winsound.Beep(1318, 80)
            winsound.Beep(1567, 80)
            winsound.Beep(2093, 200)

        threading.Thread(target=sound_worker, daemon=True).start()

    def _open_snipping_prompt(self, rune_name):
        if self.ui_parent: self.ui_parent.after(0, lambda: self._create_prompt_instance(rune_name))

    def _create_prompt_instance(self, rune_name):
        if self.active_prompt is None or not self.active_prompt.winfo_exists():
            self.prompt_active_for_rune = rune_name

            def on_yes(name):
                self.active_prompt = None
                self.prompt_active_for_rune = None
                self.pending_items = [i for i in self.pending_items if i['name'] != name]
                self._open_snipping_tool(name)

            def on_no(name):
                self.active_prompt = None
                self.prompt_active_for_rune = None
                self.pending_items = [i for i in self.pending_items if i['name'] != name]

            self.active_prompt = SnippingPrompt(parent=self.ui_parent, rune_name=rune_name, on_yes_callback=on_yes,
                                                on_no_callback=on_no)

    def _open_snipping_tool(self, rune_name):
        if self.ui_parent: self.ui_parent.after(0, lambda: self._create_snipping_instance(rune_name))

    def _create_snipping_instance(self, rune_name):
        def on_success(learned_name):
            if self.drop_callback: self.drop_callback(learned_name)

        RuneSnippingTool(parent=self.ui_parent, rune_name=rune_name, folder_path=self.inv_verifier.icon_folder,
                         success_callback=on_success)

    def _scan_loop(self):
        from ctypes import windll
        sw = windll.user32.GetSystemMetrics(0)
        sh = windll.user32.GetSystemMetrics(1)
        char_center_x, char_center_y = sw / 2, sh / 2

        full_monitor = {"top": int(sh * 0.15), "left": int(sw * 0.15), "width": int(sw * 0.70),
                        "height": int(sh * 0.70)}

        with mss.mss() as sct:
            while not self.stop_event.is_set():
                if self.active:
                    try:
                        if self.ui_parent and hasattr(self.ui_parent,
                                                      "bound_hwnd") and self.ui_parent.bound_hwnd is not None:
                            current_hwnd = windll.user32.GetForegroundWindow()
                            if current_hwnd != self.ui_parent.bound_hwnd:
                                time.sleep(0.5);
                                continue

                        now = time.time()
                        auto_pickup_on = self.config.get("auto_pickup", False)

                        sct_img = sct.grab(full_monitor)
                        full_bgr = np.array(sct_img)[:, :, :3]

                        # Wir merken uns das Bild für die spätere Kalibrierung
                        self.last_full_bgr = full_bgr.copy()

                        found_match = False
                        match_locs = []

                        ai_roi = self.ai.get_optimal_roi(sw, sh, char_center_x, char_center_y)

                        if ai_roi and self.templates:
                            rel_top = ai_roi["top"] - full_monitor["top"]
                            rel_left = ai_roi["left"] - full_monitor["left"]
                            if rel_top >= 0 and rel_left >= 0:
                                hotspot_bgr = full_bgr[
                                    rel_top:rel_top + ai_roi["height"], rel_left:rel_left + ai_roi["width"]]
                                found_match, match_locs = self._check_templates_multi(hotspot_bgr, ai_roi["left"],
                                                                                      ai_roi["top"])

                        if not found_match and self.templates:
                            found_match, match_locs = self._check_templates_multi(full_bgr, full_monitor["left"],
                                                                                  full_monitor["top"])

                        current_scan_items = {}
                        if found_match and match_locs:
                            for loc in match_locs:
                                abs_x, abs_y, name, tmpl_bin, tw, th = loc[0], loc[1], loc[2], loc[3], loc[4], loc[5]

                                if self._is_inventory_tooltip(abs_x, abs_y, sw, sh): continue

                                current_scan_items[(abs_x, abs_y)] = (name, tmpl_bin, tw, th)

                                if now - self.last_ground_log >= 2.0:
                                    log_debug(f"RUNE AM BODEN GESEHEN: {name}")
                                    self.last_ground_log = now

                            if current_scan_items and (now - self.last_sound_time >= self.cooldown):
                                self._trigger_alarm()
                                self.last_sound_time = now

                        for (old_x, old_y), (name, tmpl_bin, tw, th) in self.tracked_items.items():
                            is_still_there = False
                            for (new_x, new_y), (new_name, _, _, _) in current_scan_items.items():
                                if name == new_name and math.hypot(old_x - new_x, old_y - new_y) < 50:
                                    is_still_there = True;
                                    break

                            if not is_still_there:
                                dist_to_char = math.hypot(old_x - char_center_x, old_y - char_center_y)
                                if dist_to_char < 400:
                                    clean_name = name.replace("-Rune", "").replace("_Rune", "").replace(".png",
                                                                                                        "").replace(
                                        ".jpg", "").strip().title()
                                    is_already_pending = any(p['name'] == clean_name for p in self.pending_items)
                                    if not is_already_pending:
                                        self.pending_items.append({
                                            'name': clean_name, 'tmpl': tmpl_bin, 'time': now, 'inv_timer': None,
                                            'ground_x': old_x, 'ground_y': old_y, 'width': tw, 'height': th
                                        })
                                        self.inv_verifier.update_baseline(force_reset_item=clean_name)
                                        winsound.Beep(400, 150)

                        self.tracked_items = current_scan_items.copy()

                        inv_open = self.inv_verifier.is_inventory_open()

                        if inv_open and not self.pending_items:
                            self.inv_verifier.update_baseline()

                        elif inv_open and self.pending_items:
                            for p_item in list(self.pending_items):
                                rune_name = p_item['name']

                                if self.inv_verifier.verify_item_in_inventory(rune_name):
                                    self.ai.report_pickup_success(True)
                                    self.ai.report_drop_location(char_center_x, char_center_y, p_item['ground_x'],
                                                                 p_item['ground_y'])

                                    # --- INNOVATION: Farbkalibrierung anstoßen ---
                                    # Da wir wissen, dass das Item *wirklich* dort lag, lernen wir nun aus dem Licht
                                    if hasattr(self, 'last_full_bgr'):
                                        self._calibrate_colors_from_success(
                                            self.last_full_bgr,
                                            p_item['ground_x'], p_item['ground_y'],
                                            p_item['width'], p_item['height'],
                                            full_monitor
                                        )
                                    # ---------------------------------------------

                                    if self.drop_callback: self.drop_callback(rune_name)
                                    self.pending_items.remove(p_item)
                                    continue

                                if p_item['inv_timer'] is None: p_item['inv_timer'] = now
                                if now - p_item['inv_timer'] > 3.5:
                                    if auto_pickup_on: self.ai.report_pickup_success(False)

                                    is_fp_inv = False
                                    if self.false_positives_inv:
                                        inv_monitor = {"top": 0, "left": int(sw * 0.5), "width": int(sw * 0.5),
                                                       "height": sh}
                                        inv_img = np.array(sct.grab(inv_monitor))[:, :, :3]
                                        inv_gray = cv2.cvtColor(inv_img, cv2.COLOR_BGR2GRAY)

                                        for fp_inv in self.false_positives_inv:
                                            res_fp = cv2.matchTemplate(inv_gray, fp_inv, cv2.TM_CCOEFF_NORMED)
                                            _, max_val_fp, _, _ = cv2.minMaxLoc(res_fp)
                                            if max_val_fp >= 0.85:
                                                is_fp_inv = True;
                                                break

                                    if is_fp_inv:
                                        self.pending_items.remove(p_item);
                                        break

                                    if SnippingPrompt is not None and self.prompt_active_for_rune != rune_name:
                                        self._open_snipping_prompt(rune_name);
                                        break

                                if now - p_item['time'] > 60: self.pending_items.remove(p_item)

                        elif not inv_open and self.pending_items:
                            for p_item in self.pending_items:
                                if p_item['inv_timer'] is not None: p_item['inv_timer'] = None

                        if auto_pickup_on and match_locs:
                            valid_targets = []
                            for loc in match_locs:
                                abs_x, abs_y, name = loc[0], loc[1], loc[2]
                                is_safe = now - self.last_click_time < 1.5 or not self._is_inventory_tooltip(abs_x,
                                                                                                             abs_y, sw,
                                                                                                             sh)
                                if is_safe:
                                    dist = math.hypot(abs_x - char_center_x, abs_y - char_center_y)
                                    valid_targets.append((dist, abs_x, abs_y, name))

                            if valid_targets:
                                valid_targets.sort(key=lambda x: x[0])
                                _, target_x, target_y, target_name = valid_targets[0]

                                if now - self.last_click_time > 1.2:
                                    react_delay = self.ai.get_pickup_delay()
                                    time.sleep(react_delay)

                                    if HumanMouse:
                                        hm = HumanMouse()
                                        hm.move_to_humanized(target_x, target_y)
                                        hm.human_click()
                                    else:
                                        self._instant_click(target_x, target_y, sw, sh)

                                    self.last_click_time = time.time()
                                    self.active_target_name = target_name
                                    self.active_target_count = sum(1 for t in valid_targets if t[3] == target_name)

                        time.sleep(0.01 if auto_pickup_on else 0.3)

                    except Exception as e:
                        log_debug(f"Drop Watcher Error: {e}")
                        time.sleep(1)
                else:
                    time.sleep(1)