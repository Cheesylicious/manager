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

try:
    from human_input import HumanMouse
except ImportError:
    HumanMouse = None

TEMPLATE_FOLDER = "runes_filter"


class DropWatcher:
    # NEU: drop_callback Parameter hinzugefügt
    def __init__(self, config_data, drop_callback=None):
        self.running = False
        self.thread = None
        self.stop_event = threading.Event()
        self.config = config_data
        self.drop_callback = drop_callback

        self.active = config_data.get("drop_alert_active", False)

        self.last_sound_time = 0
        self.cooldown = 3.0

        self.last_click_time = 0
        self.active_target_name = None
        self.active_target_count = 0

        self.templates = []
        self._load_templates()

    def _load_templates(self):
        self.templates = []

        # Dynamische Pfad-Logik für EXE-Kompatibilität
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
            return

        print(f"[DropWatcher] Lade Filter-Bilder aus '{folder_path}'...")

        allowed_runes = self.config.get("allowed_runes", [])
        allowed_lower = [r.lower() for r in allowed_runes]

        for f in os.listdir(folder_path):
            if f.lower().endswith(('.png', '.jpg', '.bmp')):
                fname_lower = f.lower()
                clean_name = fname_lower.replace('-', ' ').replace('_', ' ').replace('.', ' ')
                words = clean_name.split()

                is_allowed = False
                for r in allowed_lower:
                    if r in words:
                        is_allowed = True
                        break

                if not is_allowed:
                    print(f" -> Ignoriert (Nicht im Filter markiert): {f}")
                    continue

                full_path = os.path.join(folder_path, f)
                tmpl = cv2.imread(full_path)
                if tmpl is not None:

                    # Orange Schrift isolieren
                    b = tmpl[:, :, 0].astype(np.int16)
                    g = tmpl[:, :, 1].astype(np.int16)
                    r = tmpl[:, :, 2].astype(np.int16)
                    mask = (r > 140) & (r > g) & (g > b) & ((r - g) > 20) & ((r - g) < 120)

                    tmpl_binary = (mask.astype(np.uint8) * 255)

                    # Exakt auf die weisse Schrift zuschneiden
                    contours, _ = cv2.findContours(tmpl_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    if contours:
                        x, y, w, h = cv2.boundingRect(np.vstack(contours))
                        tmpl_cropped = tmpl_binary[y:y + h, x:x + w]

                        self.templates.append((f, tmpl_cropped))
                        print(f" -> Geladen & einsatzbereit: {f}")

        if not self.templates:
            print("[DropWatcher] WARNUNG: Alle Bilder wurden durch deinen Filter ignoriert! Alarm nur auf Farbe.")

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

        left_zone = sw * 0.35
        right_zone = sw * 0.65

        if (pt.x < left_zone and match_x < left_zone) or (pt.x > right_zone and match_x > right_zone):
            if abs(pt.x - match_x) < 450 and abs(pt.y - match_y) < 550:
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

    def _check_templates_multi(self, screen_img):
        b = screen_img[:, :, 0].astype(np.int16)
        g = screen_img[:, :, 1].astype(np.int16)
        r = screen_img[:, :, 2].astype(np.int16)

        mask = (r > 140) & (r > g) & (g > b) & ((r - g) > 20) & ((r - g) < 120)

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
            for name, tmpl_bin in self.templates:
                th, tw = tmpl_bin.shape
                if th > roi_img.shape[0] or tw > roi_img.shape[1]: continue

                res = cv2.matchTemplate(roi_img, tmpl_bin, cv2.TM_CCOEFF_NORMED)
                loc = np.where(res >= 0.80)

                for pt in zip(*loc[::-1]):
                    center_x = x1 + pt[0] + tw // 2
                    center_y = y1 + pt[1] + th // 2

                    is_duplicate = False
                    for item in found_items:
                        if math.hypot(center_x - item[0], center_y - item[1]) < 80:
                            is_duplicate = True
                            break

                    if not is_duplicate:
                        found_items.append((center_x, center_y, name))

        return len(found_items) > 0, found_items

    def _check_color_fallback(self, screen_bgr):
        b = screen_bgr[:, :, 0].astype(np.int16)
        g = screen_bgr[:, :, 1].astype(np.int16)
        r = screen_bgr[:, :, 2].astype(np.int16)
        mask = (r > 140) & (r > g) & (g > b) & ((r - g) > 20) & ((r - g) < 120)

        if not np.any(mask): return False, None

        mask_uint8 = mask.astype(np.uint8) * 255
        kernel = np.ones((5, 25), np.uint8)
        dilated = cv2.dilate(mask_uint8, kernel, iterations=1)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w >= 20 and h >= 8:
                return True, (x + w // 2, y + h // 2, "COLOR_MODE")
        return False, None

    def _trigger_alarm(self):
        def sound_worker():
            winsound.Beep(987, 80)
            winsound.Beep(1318, 80)
            winsound.Beep(1567, 80)
            winsound.Beep(2093, 200)

        threading.Thread(target=sound_worker, daemon=True).start()

    def _scan_loop(self):
        from ctypes import windll
        sw = windll.user32.GetSystemMetrics(0)
        sh = windll.user32.GetSystemMetrics(1)
        char_center_x, char_center_y = sw / 2, sh / 2

        monitor = {"top": int(sh * 0.15), "left": int(sw * 0.15), "width": int(sw * 0.70), "height": int(sh * 0.70)}

        with mss.mss() as sct:
            while not self.stop_event.is_set():
                if self.active:
                    try:
                        now = time.time()
                        auto_pickup_on = self.config.get("auto_pickup", False)

                        if not auto_pickup_on and (now - self.last_sound_time < self.cooldown):
                            time.sleep(0.3)
                            continue

                        sct_img = sct.grab(monitor)
                        screen_bgr = np.array(sct_img)[:, :, :3]

                        found_match = False
                        match_locs = []

                        if self.templates:
                            found_match, match_locs = self._check_templates_multi(screen_bgr)
                        else:
                            found_match, single_loc = self._check_color_fallback(screen_bgr)
                            if single_loc:
                                match_locs.append(single_loc)

                        if found_match and match_locs:
                            if self.active_target_name and (now - self.last_click_time < 1.5):
                                current_count = sum(1 for loc in match_locs if loc[2] == self.active_target_name)
                                if current_count >= self.active_target_count:
                                    time.sleep(0.01)
                                    continue
                                else:
                                    self.active_target_name = None
                                    self.active_target_count = 0
                                    continue

                            valid_targets = []
                            for loc in match_locs:
                                abs_x = monitor["left"] + loc[0]
                                abs_y = monitor["top"] + loc[1]
                                name = loc[2]

                                is_safe = False
                                if now - self.last_click_time < 1.5:
                                    is_safe = True
                                elif not self._is_inventory_tooltip(abs_x, abs_y, sw, sh):
                                    is_safe = True

                                if is_safe:
                                    dist = math.hypot(abs_x - char_center_x, abs_y - char_center_y)
                                    valid_targets.append((dist, abs_x, abs_y, name))

                            if valid_targets:
                                # --- NEU: Melde ALLE gefundenen Runen sofort an das Overlay ---
                                if self.drop_callback:
                                    for vt in valid_targets:
                                        t_name = vt[3]
                                        if t_name != "COLOR_MODE":
                                            # Dateiendung abschneiden und schön formatieren (z.B. jah.png -> Jah)
                                            clean_name = t_name.replace(".png", "").replace(".jpg", "").replace(".bmp",
                                                                                                                "").title()
                                            self.drop_callback(clean_name)

                                # Pickup und Alarm immer für das Ziel ausführen, das am nächsten ist
                                valid_targets.sort(key=lambda x: x[0])
                                closest_dist, target_x, target_y, target_name = valid_targets[0]

                                if now - self.last_sound_time >= self.cooldown:
                                    self._trigger_alarm()
                                    self.last_sound_time = now

                                if auto_pickup_on and target_name != "COLOR_MODE":
                                    min_ms = self.config.get("pickup_delay_min", 150)
                                    max_ms = self.config.get("pickup_delay_max", 350)
                                    if max_ms < min_ms: max_ms = min_ms

                                    react_delay = random.uniform(min_ms, max_ms) / 1000.0
                                    if react_delay > 0: time.sleep(react_delay)

                                    if max_ms <= 10:
                                        self._instant_click(target_x, target_y, sw, sh)
                                    else:
                                        if HumanMouse:
                                            hm = HumanMouse()
                                            hm.move_to_humanized(target_x, target_y)
                                            hm.human_click()

                                    self.last_click_time = time.time()
                                    self.active_target_name = target_name
                                    self.active_target_count = sum(1 for t in valid_targets if t[3] == target_name)
                                    continue

                        time.sleep(0.01 if auto_pickup_on else 0.3)

                    except Exception as e:
                        print(f"Drop Watcher Error: {e}")
                        time.sleep(1)
                else:
                    time.sleep(1)