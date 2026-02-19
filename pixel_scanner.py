import time
import threading
import winsound
import os
import sys
import random
import cv2
import numpy as np
import math
from PIL import ImageGrab

try:
    from human_input import HumanMouse
except ImportError:
    HumanMouse = None

# --- CONFIG ---
TEMPLATE_FOLDER = "runes_filter"


class DropWatcher:
    def __init__(self, config_data):
        self.running = False
        self.thread = None
        self.stop_event = threading.Event()
        self.config = config_data

        self.active = config_data.get("drop_alert_active", False)

        self.last_sound_time = 0
        self.cooldown = 3.0

        # CLOSED-LOOP TRACKING (Echtzeit-Optik)
        self.last_click_time = 0
        self.active_target_name = None

        self.templates = []
        self._load_templates()

    def _load_templates(self):
        """Lädt alle Bilder aus dem runes_filter Ordner in den RAM."""
        self.templates = []
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        folder_path = os.path.join(base_path, TEMPLATE_FOLDER)

        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path)
            except:
                pass
            return

        print(f"[DropWatcher] Lade Filter-Bilder aus '{folder_path}'...")
        for f in os.listdir(folder_path):
            if f.lower().endswith(('.png', '.jpg', '.bmp')):
                full_path = os.path.join(folder_path, f)
                tmpl = cv2.imread(full_path)
                if tmpl is not None:
                    self.templates.append((f, tmpl))
                    print(f" -> Geladen: {f}")

        if not self.templates:
            print("[DropWatcher] WARNUNG: Keine Referenzbilder gefunden! Alarm nur auf Farbe.")

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

    def _is_orange_pixel(self, r, g, b):
        if r < 140: return False
        if not (r > g > b): return False
        if not (20 < (r - g) < 120): return False
        return True

    def _is_inventory_tooltip(self, match_x, match_y, sw, sh):
        from ctypes import windll, Structure, c_long, byref
        class POINT(Structure):
            _fields_ = [("x", c_long), ("y", c_long)]

        pt = POINT()
        windll.user32.GetCursorPos(byref(pt))

        left_zone = sw * 0.40
        right_zone = sw * 0.60

        is_mouse_left = pt.x < left_zone
        is_match_left = match_x < left_zone
        is_mouse_right = pt.x > right_zone
        is_match_right = match_x > right_zone

        if (is_mouse_left and is_match_left) or (is_mouse_right and is_match_right):
            if abs(pt.x - match_x) < 450 and abs(pt.y - match_y) < 550:
                return True
        return False

    def _instant_click(self, x, y, sw, sh):
        """ESPORT-MODUS: Low-Level Hardware-Snap. 0ms Ausführung."""
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

        # 1. Snap Bewegen
        mi_move = MOUSEINPUT(nx, ny, 0, 0x0001 | 0x8000, 0, None)
        windll.user32.SendInput(1, byref(INPUT(0, INPUT_I(mi=mi_move))), sizeof(INPUT))
        time.sleep(0.01)  # Minimalster Puffer für die Engine

        # 2. Klick Down
        mi_down = MOUSEINPUT(0, 0, 0, 0x0002, 0, None)
        windll.user32.SendInput(1, byref(INPUT(0, INPUT_I(mi=mi_down))), sizeof(INPUT))
        time.sleep(0.02)

        # 3. Klick Up
        mi_up = MOUSEINPUT(0, 0, 0, 0x0004, 0, None)
        windll.user32.SendInput(1, byref(INPUT(0, INPUT_I(mi=mi_up))), sizeof(INPUT))

    def _scan_loop(self):
        from ctypes import windll
        user32 = windll.user32
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)

        char_center_x = sw / 2
        char_center_y = sh / 2

        bbox = (int(sw * 0.15), int(sh * 0.15), int(sw * 0.85), int(sh * 0.85))

        while not self.stop_event.is_set():
            if self.active:
                try:
                    now = time.time()
                    auto_pickup_on = self.config.get("auto_pickup", False)

                    if not auto_pickup_on and (now - self.last_sound_time < self.cooldown):
                        time.sleep(0.3)
                        continue

                    pil_img = ImageGrab.grab(bbox=bbox)
                    screen_np = np.array(pil_img)
                    screen_bgr = cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR)

                    found_match = False
                    match_locs = []

                    # CPU SCHONUNG: Wenn der Charakter gerade auf ein Item zurennt,
                    # scannen wir NICHT mehr das ganze Bild nach allen Runen, sondern warten nur darauf,
                    # dass das aktuell anvisierte Item vom Boden verschwindet.
                    is_running_to_target = False
                    if self.active_target_name and (now - self.last_click_time < 1.2):
                        is_running_to_target = True

                        # Wir suchen nur noch nach dem EINEN Template, zu dem wir gerade rennen!
                        for name, tmpl in self.templates:
                            if name == self.active_target_name:
                                res = cv2.matchTemplate(screen_bgr, tmpl, cv2.TM_CCOEFF_NORMED)
                                if np.max(res) >= 0.90:
                                    found_match = True
                                break

                        if found_match:
                            # Das Item liegt noch auf dem Boden. Charakter ist noch nicht angekommen.
                            time.sleep(0.02)
                            continue
                        else:
                            # Item wurde aufgesammelt! Bot ist sofort wieder frei für den nächsten Scan.
                            print(f"[DropWatcher] Rune aufgesammelt! Bot wieder frei.")
                            self.active_target_name = None
                            continue

                    # NORMALER VOLL-SCAN (Wenn der Bot nicht gerade auf ein Item zurennt)
                    if self.templates:
                        found_match, match_locs = self._check_templates_multi(screen_bgr)
                    else:
                        found_match, single_loc = self._check_color_fallback(pil_img)
                        if single_loc:
                            match_locs.append(single_loc)

                    if found_match and match_locs:
                        valid_targets = []
                        for loc in match_locs:
                            abs_x = bbox[0] + loc[0]
                            abs_y = bbox[1] + loc[1]
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
                            valid_targets.sort(key=lambda x: x[0])
                            closest_dist, target_x, target_y, target_name = valid_targets[0]

                            if now - self.last_sound_time >= self.cooldown:
                                self._trigger_alarm()
                                self.last_sound_time = now

                            if auto_pickup_on:
                                min_ms = self.config.get("pickup_delay_min", 150)
                                max_ms = self.config.get("pickup_delay_max", 350)
                                if max_ms < min_ms: max_ms = min_ms

                                react_delay = random.uniform(min_ms, max_ms) / 1000.0
                                if react_delay > 0:
                                    time.sleep(react_delay)

                                # ESPORT-MODUS VS HUMAN-MODUS
                                if max_ms <= 10:
                                    self._instant_click(target_x, target_y, sw, sh)
                                    print(f"[DropWatcher] 0ms SNAP ausgeführt auf: {target_name}")
                                else:
                                    if HumanMouse:
                                        hm = HumanMouse()
                                        hm.move_to_humanized(target_x, target_y)
                                        hm.human_click()
                                        print(f"[DropWatcher] Human-Click ausgeführt auf: {target_name}")

                                # Ziel setzen, damit der Bot im nächsten Frame pausiert, bis das Item weg ist
                                self.last_click_time = time.time()
                                self.active_target_name = target_name

                                continue

                                # Entfesselter CPU-Takt für maximal schnelle Reaktionen
                    time.sleep(0.02 if auto_pickup_on else 0.3)

                except Exception as e:
                    print(f"Drop Watcher Error: {e}")
                    time.sleep(1)
            else:
                time.sleep(1)

    def _check_templates_multi(self, screen_img):
        found_items = []
        for name, tmpl in self.templates:
            res = cv2.matchTemplate(screen_img, tmpl, cv2.TM_CCOEFF_NORMED)
            loc = np.where(res >= 0.90)
            h, w = tmpl.shape[:2]

            for pt in zip(*loc[::-1]):
                center_x = pt[0] + w // 2
                center_y = pt[1] + h // 2

                is_duplicate = False
                for item in found_items:
                    if math.hypot(center_x - item[0], center_y - item[1]) < 80:
                        is_duplicate = True
                        break

                if not is_duplicate:
                    found_items.append((center_x, center_y, name))

        if found_items:
            return True, found_items
        return False, []

    def _check_color_fallback(self, pil_img):
        pixels = pil_img.load()
        w, h = pil_img.size
        for y in range(0, h, 20):
            for x in range(0, w, 20):
                r, g, b = pixels[x, y]
                if self._is_orange_pixel(r, g, b):
                    count = 0
                    for k in range(1, 5):
                        if x + k < w and self._is_orange_pixel(*pixels[x + k, y]): count += 1

                    if count >= 2:
                        return True, (x, y, "COLOR_MODE")
        return False, None

    def _trigger_alarm(self):
        """Spielt den Sound im Hintergrund ab, OHNE das Script für eine halbe Sekunde einzufrieren!"""

        def sound_worker():
            winsound.Beep(1500, 80)
            winsound.Beep(1500, 80)
            winsound.Beep(2500, 300)

        threading.Thread(target=sound_worker, daemon=True).start()