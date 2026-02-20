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
        self._load_templates()

    def _load_templates(self):
        """Lädt Templates und bereinigt Namen von Suffixen wie '-Rune'."""
        self.templates = []

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

        log_debug(f"Lade Filter-Bilder aus '{folder_path}'...")

        allowed_runes = self.config.get("allowed_runes", [])
        # Wir bereinigen auch die Config-Einträge für den Vergleich
        allowed_clean = [r.lower().replace("-rune", "").strip() for r in allowed_runes]

        for f in os.listdir(folder_path):
            if f.lower().endswith(('.png', '.jpg', '.bmp')):
                fname_lower = f.lower()
                # Namen radikal bereinigen: Dateiendung weg, "-rune" weg
                clean_name = fname_lower.split('.')[0].replace("-rune", "").replace("_rune", "").strip()

                if clean_name not in allowed_clean:
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

                    contours, _ = cv2.findContours(tmpl_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    if contours:
                        x, y, w, h = cv2.boundingRect(np.vstack(contours))
                        tmpl_cropped = tmpl_binary[y:y + h, x:x + w]
                        # Wir speichern das Template mit dem sauberen Kurznamen (z.B. "Tal")
                        self.templates.append((clean_name.title(), tmpl_cropped))

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
                        found_items.append((center_x, center_y, name, tmpl_bin))

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
                return True, (x + w // 2, y + h // 2, "COLOR_MODE", None)
        return False, None

    def _trigger_alarm(self):
        def sound_worker():
            winsound.Beep(987, 80)
            winsound.Beep(1318, 80)
            winsound.Beep(1567, 80)
            winsound.Beep(2093, 200)

        threading.Thread(target=sound_worker, daemon=True).start()

    def _open_snipping_prompt(self, rune_name):
        if self.ui_parent:
            log_debug(f"_open_snipping_prompt aufgerufen für {rune_name}")
            self.ui_parent.after(0, lambda: self._create_prompt_instance(rune_name))

    def _create_prompt_instance(self, rune_name):
        if self.active_prompt is None or not self.active_prompt.winfo_exists():
            log_debug(f"Zeige Nachfrage-Popup für: {rune_name}")
            self.prompt_active_for_rune = rune_name

            def on_yes(name):
                log_debug(f"Nutzer hat JA geklickt für {name}. Starte Vollbild-Tool...")
                self.active_prompt = None
                self.prompt_active_for_rune = None
                self.pending_items = [i for i in self.pending_items if i['name'] != name]
                self._open_snipping_tool(name)

            def on_no(name):
                log_debug(f"Nutzer hat NEIN geklickt. Breche ab für {name}.")
                self.active_prompt = None
                self.prompt_active_for_rune = None
                self.pending_items = [i for i in self.pending_items if i['name'] != name]

            self.active_prompt = SnippingPrompt(
                parent=self.ui_parent,
                rune_name=rune_name,
                on_yes_callback=on_yes,
                on_no_callback=on_no
            )

    def _open_snipping_tool(self, rune_name):
        if self.ui_parent:
            self.ui_parent.after(0, lambda: self._create_snipping_instance(rune_name))

    def _create_snipping_instance(self, rune_name):
        def on_success(learned_name):
            log_debug(f"Snipping-Erfolg: {learned_name} wurde gelernt.")
            if self.drop_callback:
                self.drop_callback(learned_name)

        RuneSnippingTool(
            parent=self.ui_parent,
            rune_name=rune_name,
            folder_path=self.inv_verifier.icon_folder,
            success_callback=on_success
        )

    def _scan_loop(self):
        from ctypes import windll
        sw = windll.user32.GetSystemMetrics(0)
        sh = windll.user32.GetSystemMetrics(1)
        char_center_x, char_center_y = sw / 2, sh / 2

        monitor = {"top": int(sh * 0.15), "left": int(sw * 0.15), "width": int(sw * 0.70), "height": int(sh * 0.70)}
        log_debug(f"Scan-Loop gestartet. Monitor: {sw}x{sh}")

        with mss.mss() as sct:
            while not self.stop_event.is_set():
                if self.active:
                    try:
                        now = time.time()
                        auto_pickup_on = self.config.get("auto_pickup", False)

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

                        current_scan_items = {}
                        if found_match and match_locs:
                            for loc in match_locs:
                                abs_x = monitor["left"] + loc[0]
                                abs_y = monitor["top"] + loc[1]

                                if self._is_inventory_tooltip(abs_x, abs_y, sw, sh):
                                    continue

                                name = loc[2]
                                tmpl_bin = loc[3]
                                current_scan_items[(abs_x, abs_y)] = (name, tmpl_bin)

                                if now - self.last_ground_log >= 2.0:
                                    log_debug(f"RUNE AM BODEN GESEHEN: {name}")
                                    self.last_ground_log = now

                            if current_scan_items and (now - self.last_sound_time >= self.cooldown):
                                self._trigger_alarm()
                                self.last_sound_time = now

                        # --- PICKUP VERIFIKATION ---
                        for (old_x, old_y), (name, tmpl_bin) in self.tracked_items.items():
                            is_still_there = False
                            for (new_x, new_y), (new_name, _) in current_scan_items.items():
                                if name == new_name and math.hypot(old_x - new_x, old_y - new_y) < 50:
                                    is_still_there = True
                                    break

                            if not is_still_there:
                                dist_to_char = math.hypot(old_x - char_center_x, old_y - char_center_y)

                                if dist_to_char < 400:
                                    if name != "COLOR_MODE":
                                        # INNOVATION: Suffix-Bereinigung bei Pickup (z.B. "Tal-Rune" -> "Tal")
                                        clean_name = name.replace("-Rune", "").replace("_Rune", "").replace(".png",
                                                                                                            "").replace(
                                            ".jpg", "").strip().title()

                                        is_already_pending = any(p['name'] == clean_name for p in self.pending_items)
                                        if not is_already_pending:
                                            self.pending_items.append({
                                                'name': clean_name,
                                                'tmpl': tmpl_bin,
                                                'time': now,
                                                'inv_timer': None
                                            })

                                            self.inv_verifier.update_baseline(force_reset_item=clean_name)

                                            winsound.Beep(400, 150)
                                            log_debug(
                                                f"Rune verschwunden! '{clean_name}' in die Warteliste aufgenommen.")

                        self.tracked_items = current_scan_items.copy()

                        # --- INVENTAR-CHECK & BASELINE LOGIK ---
                        inv_open = self.inv_verifier.is_inventory_open()

                        if inv_open and not self.pending_items:
                            self.inv_verifier.update_baseline()

                        elif inv_open and self.pending_items:
                            for p_item in list(self.pending_items):
                                rune_name = p_item['name']

                                if self.inv_verifier.verify_item_in_inventory(rune_name):
                                    log_debug(f"Bekanntes Icon '{rune_name}' im Inventar bestaetigt.")
                                    if self.drop_callback:
                                        self.drop_callback(rune_name)
                                    self.pending_items.remove(p_item)
                                    continue

                                if p_item['inv_timer'] is None:
                                    p_item['inv_timer'] = now
                                    log_debug(f"Inventar offen. Starte 3.5s Grace-Period fuer '{rune_name}'...")

                                if now - p_item['inv_timer'] > 3.5:
                                    if SnippingPrompt is not None and self.prompt_active_for_rune != rune_name:
                                        log_debug(f"Grace-Period abgelaufen. Triggere Prompt fuer '{rune_name}'.")
                                        self._open_snipping_prompt(rune_name)
                                        break

                                if now - p_item['time'] > 60:
                                    log_debug(f"Timeout fuer '{rune_name}'. Aus Warteliste entfernt.")
                                    self.pending_items.remove(p_item)

                        elif not inv_open and self.pending_items:
                            for p_item in self.pending_items:
                                if p_item['inv_timer'] is not None:
                                    p_item['inv_timer'] = None

                        # AUTO-PICKUP LOGIK
                        if auto_pickup_on and match_locs:
                            valid_targets = []
                            for loc in match_locs:
                                abs_x = monitor["left"] + loc[0]
                                abs_y = monitor["top"] + loc[1]
                                name = loc[2]
                                is_safe = now - self.last_click_time < 1.5 or not self._is_inventory_tooltip(abs_x,
                                                                                                             abs_y, sw,
                                                                                                             sh)

                                if is_safe:
                                    dist = math.hypot(abs_x - char_center_x, abs_y - char_center_y)
                                    valid_targets.append((dist, abs_x, abs_y, name))

                            if valid_targets:
                                valid_targets.sort(key=lambda x: x[0])
                                _, target_x, target_y, target_name = valid_targets[0]

                                if target_name != "COLOR_MODE" and now - self.last_click_time > 1.2:
                                    min_ms = self.config.get("pickup_delay_min", 150)
                                    max_ms = self.config.get("pickup_delay_max", 350)
                                    react_delay = random.uniform(min_ms, max_ms) / 1000.0
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