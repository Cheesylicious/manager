import cv2
import numpy as np
import mss
import ctypes
import os
import sys
import time
import math
import re


class InventoryVerifier:
    def __init__(self):
        self.sw = ctypes.windll.user32.GetSystemMetrics(0)
        self.sh = ctypes.windll.user32.GetSystemMetrics(1)

        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        self.icon_folder = os.path.join(base_path, "runes_inventory")
        self._ensure_folder()

        self.grid_region = {
            "top": int(self.sh * 0.55),
            "left": int(self.sw * 0.66),
            "width": int(self.sw * 0.28),
            "height": int(self.sh * 0.38)
        }

        self.cols = 10
        self.rows = 4
        self.slot_w = self.grid_region["width"] / self.cols
        self.slot_h = self.grid_region["height"] / self.rows

        self.inventory_templates = {}
        self.inventory_baseline = {}
        self.last_baseline_time = 0

        self.last_best_matches = {}

        self._load_inventory_icons()

        self.last_log_time = 0
        self.last_hovered_slot = None
        self.hover_start_time = 0

    def log_debug(self, msg):
        try:
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))

            log_file = os.path.join(base_path, "scanner_debug.txt")
            timestamp = time.strftime('%H:%M:%S')
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] [INV-CHECK] {msg}\n")
        except:
            pass

    def _ensure_folder(self):
        if not os.path.exists(self.icon_folder):
            os.makedirs(self.icon_folder, exist_ok=True)

    def _load_inventory_icons(self):
        self.inventory_templates = {}
        if not os.path.exists(self.icon_folder):
            return
        for f in os.listdir(self.icon_folder):
            if f.lower().endswith(('.png', '.jpg', '.bmp')):
                raw_name = f.split('.')[0]
                base_name = re.split(r'_', raw_name)[0].title()

                if base_name not in self.inventory_templates:
                    self.inventory_templates[base_name] = []

                path = os.path.join(self.icon_folder, f)
                img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    self.inventory_templates[base_name].append(self._preprocess_image(img))

    def get_mouse_pos(self):
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    def is_inventory_open(self, ignored_screen_bgr=None):
        with mss.mss() as sct:
            title_region = {
                "top": int(self.sh * 0.02),
                "left": int(self.sw * 0.73),
                "width": int(self.sw * 0.18),
                "height": int(self.sh * 0.06)
            }
            sct_img = sct.grab(title_region)
            img = np.array(sct_img)[:, :, :3]

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 140, 255, cv2.THRESH_BINARY)

            kernel = np.ones((3, 15), np.uint8)
            dilated = cv2.dilate(binary, kernel, iterations=1)
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            has_text = any(cv2.boundingRect(cnt)[2] > 50 for cnt in contours)

            bg_pixel = img[2, 2]
            bg_sum = int(bg_pixel[0]) + int(bg_pixel[1]) + int(bg_pixel[2])
            bg_is_dark = bg_sum < 450

            return has_text and bg_is_dark

    def _preprocess_image(self, img_gray):
        img_norm = cv2.normalize(img_gray, None, 0, 255, cv2.NORM_MINMAX)
        _, thresh = cv2.threshold(img_norm, 50, 255, cv2.THRESH_TOZERO)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        return clahe.apply(thresh)

    def update_baseline(self, force_reset_item=None):
        self._load_inventory_icons()

        if force_reset_item:
            self.inventory_baseline[force_reset_item] = 0
            return

        with mss.mss() as sct:
            sct_img = sct.grab(self.grid_region)
            inv_gray = cv2.cvtColor(np.array(sct_img)[:, :, :3], cv2.COLOR_BGR2GRAY)
            inv_clean = self._preprocess_image(inv_gray)

        for name, tmpl_list in self.inventory_templates.items():
            res = self._count_template_in_image(tmpl_list, inv_clean)
            count = res[0] if isinstance(res, tuple) else res
            self.inventory_baseline[name] = count

    def _count_template_in_image(self, tmpl_list, inv_img):
        best_pts = []
        best_max_val = 0.0
        best_max_loc = None
        best_cx, best_cy, best_th, best_tw = 0, 0, 0, 0

        for tmpl in tmpl_list:
            th, tw = tmpl.shape
            cy, cx = max(1, int(th * 0.25)), max(1, int(tw * 0.25))
            tmpl_core = tmpl[cy:-cy, cx:-cx] if th > 2 * cy and tw > 2 * cx else tmpl

            res = cv2.matchTemplate(inv_img, tmpl_core, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)

            # Immer den besten Wert für die Anzeige speichern
            if max_val > best_max_val:
                best_max_val = max_val
                best_max_loc = max_loc
                best_cx, best_cy, best_th, best_tw = cx, cy, th, tw

            loc = np.where(res >= 0.32)
            for pt in zip(*loc[::-1]):
                if not any(math.hypot(pt[0] - p[0], pt[1] - p[1]) < 20 for p in best_pts):
                    best_pts.append(pt)

        if len(best_pts) > 0:
            return len(best_pts), best_max_val, best_max_loc, best_cx, best_cy, best_th, best_tw

        # Canny Fallback
        best_pts_e = []
        best_max_val_e = 0.0

        for tmpl in tmpl_list:
            th, tw = tmpl.shape
            cy, cx = max(1, int(th * 0.25)), max(1, int(tw * 0.25))
            tmpl_core = tmpl[cy:-cy, cx:-cx] if th > 2 * cy and tw > 2 * cx else tmpl

            edges_inv = cv2.Canny(inv_img, 50, 150)
            edges_tmpl = cv2.Canny(tmpl_core, 50, 150)
            res_e = cv2.matchTemplate(edges_inv, edges_tmpl, cv2.TM_CCOEFF_NORMED)
            _, max_val_e, _, max_loc_e = cv2.minMaxLoc(res_e)

            if max_val_e > best_max_val_e:
                best_max_val_e = max_val_e

            loc_e = np.where(res_e >= 0.12)
            for pt in zip(*loc_e[::-1]):
                if not any(math.hypot(pt[0] - p[0], pt[1] - p[1]) < 20 for p in best_pts_e):
                    best_pts_e.append(pt)

        if len(best_pts_e) > 0:
            return len(best_pts_e), best_max_val_e, best_max_loc, best_cx, best_cy, best_th, best_tw

        # Wenn beides nicht den Schwellenwert knackt, geben wir trotzdem das Bild mit dem besten Score zurück
        return 0, best_max_val, best_max_loc, best_cx, best_cy, best_th, best_tw

    def get_hovered_slot_icon(self):
        mx, my = self.get_mouse_pos()
        if not (self.grid_region["left"] <= mx <= self.grid_region["left"] + self.grid_region["width"] and
                self.grid_region["top"] <= my <= self.grid_region["top"] + self.grid_region["height"]):
            self.last_hovered_slot = None
            return None

        rel_x, rel_y = mx - self.grid_region["left"], my - self.grid_region["top"]
        col, row = int(rel_x / self.slot_w), int(rel_y / self.slot_h)
        current_slot = (col, row)

        if current_slot != self.last_hovered_slot:
            self.last_hovered_slot, self.hover_start_time = current_slot, time.time()
            return None

        if time.time() - self.hover_start_time < 0.8:
            return None

        slot_center_x = self.grid_region["left"] + (col * self.slot_w) + (self.slot_w / 2)
        slot_center_y = self.grid_region["top"] + (row * self.slot_h) + (self.slot_h / 2)

        capture_size = 34
        icon_region = {"top": int(slot_center_y - capture_size / 2), "left": int(slot_center_x - capture_size / 2),
                       "width": capture_size, "height": capture_size}

        with mss.mss() as sct:
            icon_bgr = np.array(sct.grab(icon_region))[:, :, :3]

        gray = cv2.cvtColor(icon_bgr, cv2.COLOR_BGR2GRAY)
        if np.max(gray) < 90 or np.std(gray) < 15:
            return None

        self.hover_start_time = time.time() + 3.0
        return icon_bgr

    def verify_item_in_inventory(self, item_name):
        self._load_inventory_icons()
        if item_name not in self.inventory_templates:
            return False, 0.0

        with mss.mss() as sct:
            try:
                sct_img = sct.grab(self.grid_region)
                inv_bgr = np.array(sct_img)[:, :, :3]
                inv_gray = cv2.cvtColor(inv_bgr, cv2.COLOR_BGR2GRAY)
                inv_clean = self._preprocess_image(inv_gray)

                res = self._count_template_in_image(self.inventory_templates[item_name], inv_clean)
                current_count = res[0] if isinstance(res, tuple) else res
                best_score = res[1] if isinstance(res, tuple) else 0.0
                max_loc = res[2] if isinstance(res, tuple) and len(res) > 2 else None
                cx = res[3] if isinstance(res, tuple) and len(res) > 3 else 0
                cy = res[4] if isinstance(res, tuple) and len(res) > 4 else 0
                th = res[5] if isinstance(res, tuple) and len(res) > 5 else 0
                tw = res[6] if isinstance(res, tuple) and len(res) > 6 else 0

                if max_loc is not None and th > 0 and tw > 0:
                    x_full = max(0, max_loc[0] - cx)
                    y_full = max(0, max_loc[1] - cy)
                    crop = inv_gray[y_full:y_full + th, x_full:x_full + tw]

                    if crop.shape[0] == th and crop.shape[1] == tw:
                        self.last_best_matches[item_name] = crop

                old_count = self.inventory_baseline.get(item_name, 0)

                self.log_debug(
                    f"Check {item_name}: Baseline {old_count} -> Aktuell {current_count} (Score: {best_score:.2f})")

                if current_count > old_count:
                    self.inventory_baseline[item_name] = current_count
                    return True, best_score

                return False, best_score
            except Exception as e:
                self.log_debug(f"Fehler bei Verifizierung: {e}")
                return False, 0.0

    def learn_confirmed_icon(self, item_name, inv_score):
        """Speichert das Bild nur, wenn der Score hoch genug war, um Falschmeldungen (z.B. Würfel) zu vermeiden."""

        # SICHERHEITS-NETZ: Alles unter 55% ist Müll und wird nicht gelernt!
        if inv_score < 0.55:
            self.log_debug(
                f"[{item_name}] Score zu niedrig ({inv_score:.2f}). Ignoriere Bild, um falsche Items zu vermeiden.")
            return

        if hasattr(self, 'last_best_matches') and item_name in self.last_best_matches:
            new_icon = self.last_best_matches[item_name]

            existing = [f for f in os.listdir(self.icon_folder) if f.lower().startswith(item_name.lower())]

            if len(existing) < 3:
                new_idx = len(existing) + 1
            else:
                import random
                new_idx = random.randint(1, 3)

            filename = f"{item_name.lower()}_{new_idx}.png"
            save_path = os.path.join(self.icon_folder, filename)

            try:
                cv2.imwrite(save_path, new_icon)
                self.log_debug(f"[{item_name}] Neues, hochwertiges Icon gelernt und gespeichert.")
                self._load_inventory_icons()
            except Exception as e:
                self.log_debug(f"Fehler beim Speichern: {e}")