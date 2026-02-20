import cv2
import numpy as np
import mss
import ctypes
import os
import sys
import time
import math


class InventoryVerifier:
    def __init__(self):
        self.sw = ctypes.windll.user32.GetSystemMetrics(0)
        self.sh = ctypes.windll.user32.GetSystemMetrics(1)

        self.icon_folder = "runes_inventory"
        self._ensure_folder()

        # Region des Inventar-Grids (Standard D2R Position rechts)
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
        """Lädt alle Icons und bereitet sie für den Vergleich vor."""
        self.inventory_templates = {}
        if not os.path.exists(self.icon_folder):
            return
        for f in os.listdir(self.icon_folder):
            if f.lower().endswith(('.png', '.jpg', '.bmp')):
                path = os.path.join(self.icon_folder, f)
                img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    # Wir wenden die gleiche Vorbehandlung wie auf das Live-Bild an
                    self.inventory_templates[f.split('.')[0].title()] = self._preprocess_image(img)

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

            # FIX: Overflow verhindern durch explizite Konvertierung der uint8-Werte in Integer
            bg_pixel = img[2, 2]
            bg_sum = int(bg_pixel[0]) + int(bg_pixel[1]) + int(bg_pixel[2])
            bg_is_dark = bg_sum < 450

            return has_text and bg_is_dark

    def _preprocess_image(self, img_gray):
        """Schärft das Bild und gleicht die Helligkeit an."""
        # Auf vollen Kontrastbereich dehnen
        img_norm = cv2.normalize(img_gray, None, 0, 255, cv2.NORM_MINMAX)
        # CLAHE (Adaptive Histogramm-Egalisierung) macht Gravuren sichtbar
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        return clahe.apply(img_norm)

    def update_baseline(self, force_reset_item=None):
        """Aktualisiert den Zählerstand der Runen im Inventar."""
        self._load_inventory_icons()

        if force_reset_item:
            self.inventory_baseline[force_reset_item] = 0
            return

        with mss.mss() as sct:
            sct_img = sct.grab(self.grid_region)
            inv_gray = cv2.cvtColor(np.array(sct_img)[:, :, :3], cv2.COLOR_BGR2GRAY)
            inv_clean = self._preprocess_image(inv_gray)

        for name, tmpl in self.inventory_templates.items():
            self.inventory_baseline[name] = self._count_template_in_image(tmpl, inv_clean)

    def _count_template_in_image(self, tmpl, inv_img):
        """Zählt, wie oft eine Rune im Inventar zu sehen ist."""
        # 10% Rand vom Template abschneiden (ignoriert unsaubere Snipping-Ränder)
        th, tw = tmpl.shape
        cy, cx = max(1, int(th * 0.10)), max(1, int(tw * 0.10))
        tmpl_core = tmpl[cy:-cy, cx:-cx] if th > 2 * cy and tw > 2 * cx else tmpl

        # Template Matching mit reduzierter Toleranz für schwierige Hintergründe
        res = cv2.matchTemplate(inv_img, tmpl_core, cv2.TM_CCOEFF_NORMED)
        # Schwellenwert leicht gesenkt, um die 0.32er Matches aus deinen Logs zu erfassen
        loc = np.where(res >= 0.38)

        pts = []
        for pt in zip(*loc[::-1]):
            # Dubletten im selben Slot vermeiden
            if not any(math.hypot(pt[0] - p[0], pt[1] - p[1]) < 20 for p in pts):
                pts.append(pt)

        if len(pts) > 0:
            return len(pts)

        # Fallback: Kanten-Erkennung (Canny), falls das normale Bild zu verwaschen ist
        edges_inv = cv2.Canny(inv_img, 50, 150)
        edges_tmpl = cv2.Canny(tmpl_core, 50, 150)
        res_e = cv2.matchTemplate(edges_inv, edges_tmpl, cv2.TM_CCOEFF_NORMED)
        loc_e = np.where(res_e >= 0.15)

        pts_e = []
        for pt in zip(*loc_e[::-1]):
            if not any(math.hypot(pt[0] - p[0], pt[1] - p[1]) < 20 for p in pts_e):
                pts_e.append(pt)

        return len(pts_e)

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
        """Hauptprüfung: Hat sich die Anzahl der Rune seit dem Aufheben erhöht?"""
        self._load_inventory_icons()
        if item_name not in self.inventory_templates:
            return False

        with mss.mss() as sct:
            try:
                sct_img = sct.grab(self.grid_region)
                inv_gray = cv2.cvtColor(np.array(sct_img)[:, :, :3], cv2.COLOR_BGR2GRAY)
                inv_clean = self._preprocess_image(inv_gray)

                current_count = self._count_template_in_image(self.inventory_templates[item_name], inv_clean)
                old_count = self.inventory_baseline.get(item_name, 0)

                self.log_debug(f"Check {item_name}: Baseline {old_count} -> Aktuell {current_count}")

                if current_count > old_count:
                    # Erfolg! Rune gefunden, Baseline wird für das nächste Mal angepasst
                    self.inventory_baseline[item_name] = current_count
                    return True
                return False
            except Exception as e:
                self.log_debug(f"Fehler bei Verifizierung: {e}")
                return False