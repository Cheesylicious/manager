import customtkinter as ctk
import time
import threading
import ctypes
import mss
import cv2
import numpy as np
import os
import sys
import winsound

try:
    from zone_data import get_zones_for_act
except ImportError:
    def get_zones_for_act(act):
        return []


class ZoneCaptureMixin:
    def open_inline_capture(self):
        if self.is_capturing_zone: return
        self.inline_capture_expanded = True

        self.btn_capture_zone.pack_forget()
        self.lbl_zone.configure(text="📍 Zone:", text_color="#00ccff")

        self.manual_zone_entry.pack(side="left", padx=(5, 2))
        self.btn_manual_capture.pack(side="left")

        # NEU: Elegante Checkbox, um dem Skript zu sagen, wo der Zonen-Name steht!
        if not hasattr(self, "cb_has_gamename"):
            self.has_gamename_var = ctk.BooleanVar(value=True)  # Standard: An (Online)
            self.cb_has_gamename = ctk.CTkCheckBox(self.zone_top_frame, text="Mit Spielname?",
                                                   variable=self.has_gamename_var,
                                                   font=("Roboto", 11), checkbox_width=16, checkbox_height=16)
        self.cb_has_gamename.pack(side="left", padx=(5, 0))

        self.selection_container.pack(pady=(2, 0), anchor="center")
        self.zone_dropdown.pack_forget()
        self.act_btn_frame.pack(anchor="center")

    def show_zone_dropdown(self, act_name):
        zones = get_zones_for_act(act_name)
        if not zones:
            zones = ["Keine Daten"]

        zones.insert(0, "- Abbrechen -")
        self.dropdown_var.set("Gebiet wählen...")
        self.zone_dropdown.configure(values=zones)

        self.act_btn_frame.pack_forget()
        self.zone_dropdown.pack(anchor="center")

    def start_manual_capture(self):
        zone_name = self.manual_zone_entry.get().strip()
        if not zone_name:
            self.close_inline_capture()
            return

        self.manual_zone_entry.delete(0, 'end')
        self._initiate_capture(zone_name)

    def start_inline_capture_dropdown(self, zone_name):
        if zone_name == "- Abbrechen -" or zone_name == "Gebiet wählen..." or zone_name == "Keine Daten":
            self.close_inline_capture()
            return

        self._initiate_capture(zone_name)

    def _initiate_capture(self, zone_name):
        self.is_capturing_zone = True
        self.inline_capture_expanded = False

        self.selection_container.pack_forget()
        self.zone_dropdown.pack_forget()
        self.manual_zone_entry.pack_forget()
        self.btn_manual_capture.pack_forget()

        # Checkbox wieder verstecken
        if hasattr(self, "cb_has_gamename"):
            self.cb_has_gamename.pack_forget()

        self.btn_capture_zone.pack(side="left", padx=(5, 0))

        # Den Zustand der Checkbox an die Hintergrund-Logik übergeben
        has_name = self.has_gamename_var.get() if hasattr(self, "has_gamename_var") else False
        threading.Thread(target=self._headless_capture_logic, args=(zone_name, has_name), daemon=True).start()

    def close_inline_capture(self):
        self.inline_capture_expanded = False

        self.selection_container.pack_forget()
        self.act_btn_frame.pack_forget()
        self.zone_dropdown.pack_forget()
        self.manual_zone_entry.pack_forget()
        self.btn_manual_capture.pack_forget()

        if hasattr(self, "cb_has_gamename"):
            self.cb_has_gamename.pack_forget()

        self.lbl_zone.configure(text="📍 Zone: Unbekannt")
        self.btn_capture_zone.pack(side="left", padx=(5, 0))
        self.last_zone_check = ""

    def _headless_capture_logic(self, zone_name, has_gamename=False):
        if self.winfo_exists():
            self.btn_capture_zone.configure(fg_color="#FF9500", text_color="black", state="disabled")

        for i in range(3, 0, -1):
            if not self.winfo_exists(): return
            winsound.Beep(1000, 100)
            time.sleep(0.9)

        if not self.winfo_exists(): return
        self.btn_capture_zone.configure(fg_color="#cf222e", text_color="white")

        try:
            sw = ctypes.windll.user32.GetSystemMetrics(0)
            sh = ctypes.windll.user32.GetSystemMetrics(1)
            x1 = int(sw * 0.75)
            y1 = int(sh * 0.0)
            x2 = sw
            y2 = int(sh * 0.25)  # Wir bleiben bei 25%, damit alle Zeilen erfasst werden

            min_width_threshold = int(sw * 0.055)
            clean_name = zone_name.replace(" ", "_")

            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))

            folder_path = os.path.join(base_path, "zones_filter")
            os.makedirs(folder_path, exist_ok=True)
            valid_captures = 0

            for i in range(5):
                with mss.mss() as sct:
                    monitor = {"top": y1, "left": x1, "width": x2 - x1, "height": y2 - y1}
                    sct_img = sct.grab(monitor)
                    screen_bgr = np.array(sct_img)[:, :, :3]

                gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
                # Wieder auf saubere 180 gesetzt! Ignoriert das Map-Rauschen komplett.
                _, mask_uint8 = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

                kernel = np.ones((3, 40), np.uint8)
                dilated = cv2.dilate(mask_uint8, kernel, iterations=1)
                contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                if contours:
                    rects = []
                    for cnt in contours:
                        rx, ry, rw, rh = cv2.boundingRect(cnt)
                        if rw > 20 and rh > 8:
                            rects.append((rx, ry, rw, rh))

                    valid_rects = [r for r in rects if r[2] > min_width_threshold]
                    best_rect = None
                    if valid_rects:
                        # Sortiert von oben nach unten (anhand der Y-Achse)
                        valid_rects.sort(key=lambda r: r[1])

                        # EXAKT DEINE LOGIK:
                        if has_gamename and len(valid_rects) > 1:
                            # Mit Spielname -> Nimm die 2. Zeile
                            best_rect = valid_rects[1]
                        else:
                            # Ohne Spielname -> Nimm die 1. Zeile
                            best_rect = valid_rects[0]

                    if best_rect:
                        bx, by, bw, bh = best_rect
                        pad = 8
                        crop_y1 = max(0, by - pad)
                        crop_y2 = min(screen_bgr.shape[0], by + bh + pad)
                        crop_x1 = max(0, bx - pad)
                        crop_x2 = min(screen_bgr.shape[1], bx + bw + pad)

                        final_img = screen_bgr[crop_y1:crop_y2, crop_x1:crop_x2]
                        valid_captures += 1
                        save_path = os.path.join(folder_path, f"{clean_name}_ref{valid_captures}.png")

                        is_success, im_buf_arr = cv2.imencode(".png", final_img)
                        if is_success:
                            with open(save_path, "wb") as f:
                                f.write(im_buf_arr.tobytes())
                time.sleep(0.4)

            if valid_captures == 0:
                winsound.Beep(500, 500)
                self.btn_capture_zone.configure(text="❌", fg_color="#cf222e")
            else:
                winsound.Beep(1500, 150)
                winsound.Beep(2000, 200)
                self.btn_capture_zone.configure(text="✅", fg_color="#2da44e")
                self.reload_zone_templates()

        except Exception as e:
            print(f"Inline Capture Error: {e}")
            self.btn_capture_zone.configure(text="❌", fg_color="#cf222e")

        time.sleep(2)
        self.is_capturing_zone = False

        if self.winfo_exists() and not getattr(self, "inline_capture_expanded", False):
            self.btn_capture_zone.pack_forget()
            self.btn_capture_zone.configure(text="?", state="normal", fg_color="#444444")
            self.last_zone_check = ""

    def reload_zone_templates(self):
        if hasattr(self, "zone_watcher") and self.zone_watcher:
            self.zone_watcher._load_templates()