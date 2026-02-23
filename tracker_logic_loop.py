import time
import threading
import math
import ctypes
import winsound
import mss
import cv2
import numpy as np
import os
import sys

try:
    import sys_hooks
except ImportError:
    try:
        import d2r_input as sys_hooks
    except ImportError:
        sys_hooks = None


class PotionLogicMixin:
    def _eval_state(self, key1, key2=None):
        cfg1 = self.sensors.get(key1)
        cfg2 = self.sensors.get(key2) if key2 else None
        if not cfg1 and not cfg2: return False

        match1, _ = self._check_color(cfg1) if cfg1 else (True, None)
        match2, _ = self._check_color(cfg2) if cfg2 else (True, None)
        return match1 and match2

    def _is_d2r_foreground(self):
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd: return False

            # Berücksichtigung des Multiboxing-Bindings
            if getattr(self, "bound_hwnd", None) is not None:
                return hwnd == self.bound_hwnd

            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length == 0: return False
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)

            if "Diablo" in buff.value:
                self.bound_hwnd = hwnd
                return True
            return False
        except:
            return False

    def _update_sensor_ui(self, key, assigned_key, is_full, color_tuple):
        if color_tuple:
            hex_color = f"#{color_tuple[0]:02x}{color_tuple[1]:02x}{color_tuple[2]:02x}"
            self.sensors_ui[key]["indicator"].configure(fg_color=hex_color)

        if assigned_key == "Aus":
            self.sensors_ui[key]["status"].configure(text="AUS", text_color="#555555")
        else:
            if is_full:
                self.sensors_ui[key]["status"].configure(text=f"OK [{assigned_key}]",
                                                         text_color=self.sensors_ui[key]["color"])
            else:
                self.sensors_ui[key]["status"].configure(text=f"LOW [{assigned_key}]", text_color="#FF3333")

    def _logic_loop(self):
        # Initialisierung der Multiboxing-Timer Variablen
        self.is_tabbed_out = False
        self.tabbed_out_at = 0

        while not self.stop_event.is_set():
            ctrl = ctypes.windll.user32.GetAsyncKeyState(0x11) & 0x8000
            alt = ctypes.windll.user32.GetAsyncKeyState(0x12) & 0x8000
            g_key = ctypes.windll.user32.GetAsyncKeyState(0x47) & 0x8000
            if ctrl and alt and g_key:
                self.toggle_ghost_hotkey()

            if self.paused: time.sleep(0.5); continue

            try:
                is_active_window = self._is_d2r_foreground()

                if is_active_window:
                    # MULTIBOXING TIMER LOGIC: Wir sind zurück im gebundenen Spiel
                    if self.is_tabbed_out:
                        self.is_tabbed_out = False
                        if getattr(self, "in_game", False) and self.tabbed_out_at > 0:
                            time_away = time.time() - self.tabbed_out_at
                            self.start_time += time_away  # Verschiebt den Startpunkt um die Abwesenheit
                            self.tabbed_out_at = 0

                    is_char = self._eval_state("char_sel_1", "char_sel_2")
                    is_lobby = self._eval_state("lobby_1", "lobby_2")
                    is_game = self._eval_state("game_static")

                    if is_game:
                        new_state = "GAME"
                    elif is_char or is_lobby:
                        new_state = "MENU"
                    else:
                        new_state = self.current_state

                    if new_state == "GAME" and self.current_state != "GAME":
                        if not self.in_game:
                            self.start_time = time.time()
                            self.in_game = True
                    elif new_state == "MENU" and self.current_state == "GAME":
                        self.finish_run()
                        self.in_game = False

                    self.current_state = new_state

                    if self.current_state == "GAME":
                        self.lbl_status.configure(text="AKTIV IM SPIEL", text_color="#2da44e")
                        now = time.time()

                        if self.zone_watcher:
                            current_z = self.zone_watcher.current_zone
                            if current_z != self.last_zone_check:
                                if not self.is_capturing_zone:
                                    self.lbl_zone.configure(text=f"📍 {current_z}")
                                self.last_zone_check = current_z

                            if not self.is_capturing_zone and not getattr(self, "inline_capture_expanded", False):
                                if current_z == "Unbekannt":
                                    self.btn_capture_zone.configure(text="?", fg_color="#444444", text_color="white",
                                                                    state="normal", width=22)
                                    self.btn_capture_zone.pack(side="left", padx=(5, 0))
                                else:
                                    self.btn_capture_zone.pack_forget()

                        if now - self.last_xp_check > 2.0:
                            self.last_xp_check = now
                            self._update_xp_display(do_scan=True)

                        hp_match, hp_col = self._check_color(self.sensors["hp_sensor"], "hp")
                        mp_match, mp_col = self._check_color(self.sensors["mana_sensor"], "mana")
                        mc_match, mc_col = self._check_color(self.sensors["merc_sensor"], "merc")

                        if not hp_match and now - self.last_potions["hp"] > self.hp_delay:
                            self._press_key(self.hp_key)
                            self.last_potions["hp"] = now
                            if self.hp_sound and now - self.last_alarm_time > 2:
                                threading.Thread(target=lambda: winsound.Beep(450, 250), daemon=True).start()
                                self.last_alarm_time = now

                        if not mp_match and now - self.last_potions["mana"] > self.mana_delay:
                            self._press_key(self.mana_key)
                            self.last_potions["mana"] = now
                            if self.mana_sound and now - self.last_alarm_time > 2:
                                threading.Thread(target=lambda: winsound.Beep(2000, 100), daemon=True).start()
                                self.last_alarm_time = now

                        if not mc_match and now - self.last_potions["merc"] > self.merc_delay:
                            self._press_key(self.merc_key, True)
                            self.last_potions["merc"] = now
                            if self.merc_sound and now - self.last_alarm_time > 2:
                                def merc_snd():
                                    winsound.Beep(800, 80)
                                    time.sleep(0.05)
                                    winsound.Beep(800, 80)

                                threading.Thread(target=merc_snd, daemon=True).start()
                                self.last_alarm_time = now

                        self._update_sensor_ui("hp", self.hp_key, hp_match, hp_col)
                        self._update_sensor_ui("mana", self.mana_key, mp_match, mp_col)
                        self._update_sensor_ui("merc", self.merc_key, mc_match, mc_col)

                    elif self.current_state == "MENU":
                        self.lbl_status.configure(text="MENÜ / LOBBY", text_color="#cf222e")

                        if not self.is_capturing_zone:
                            self.lbl_zone.configure(text="📍 Zone: (Menü)", text_color="#aaaaaa")
                            self.btn_capture_zone.pack_forget()
                        self.last_zone_check = ""
                else:
                    # MULTIBOXING TIMER LOGIC: Wir tabben raus
                    if not self.is_tabbed_out:
                        self.is_tabbed_out = True
                        if getattr(self, "in_game", False):
                            self.tabbed_out_at = time.time()

                    self.lbl_status.configure(text="TABBED OUT (Auto-Pot PAUSE)", text_color="#FF9500")

                    if not self.is_capturing_zone:
                        self.lbl_zone.configure(text="📍 Zone: (Pausiert)", text_color="#aaaaaa")
                        self.btn_capture_zone.pack_forget()
                    self.last_zone_check = ""

                    for key in ["hp", "mana", "merc"]:
                        assigned_key = self.config_data.get(f"{key}_key", "Aus")
                        if assigned_key == "Aus":
                            self.sensors_ui[key]["status"].configure(text="AUS", text_color="#555555")
                        else:
                            self.sensors_ui[key]["status"].configure(text="PAUSE", text_color="#FF9500")

                time.sleep(0.1)
            except Exception as e:
                time.sleep(1)

    def _check_color(self, cfg, mode="match"):
        if not cfg: return False, (0, 0, 0)

        if isinstance(cfg, list):
            if len(cfg) == 0: return False, (0, 0, 0)
            matches = 0
            last_color = (0, 0, 0)
            for point in cfg:
                match, c = self._check_color(point, mode)
                if match: matches += 1
                last_color = c
            return (matches > 0 and matches >= (len(cfg) / 2)), last_color

        if isinstance(cfg, dict) and cfg.get("is_template"):
            return self._check_template(cfg)

        return self._check_single_pixel(cfg, mode)

    def _check_template(self, cfg):
        try:
            template_path = cfg.get("template_path")

            if not os.path.isabs(template_path):
                if getattr(sys, 'frozen', False):
                    base_path = os.path.dirname(sys.executable)
                else:
                    base_path = os.path.dirname(os.path.abspath(__file__))
                template_path = os.path.join(base_path, template_path)

            if not os.path.exists(template_path):
                return False, (0, 0, 0)

            tmpl = cv2.imread(template_path)
            if tmpl is None:
                return False, (0, 0, 0)

            x1, y1, x2, y2 = cfg.get("box", (0, 0, 0, 0))
            if x2 <= x1 or y2 <= y1:
                return False, (0, 0, 0)

            pad = 10
            top = max(0, y1 - pad)
            left = max(0, x1 - pad)
            width = (x2 - x1) + pad * 2
            height = (y2 - y1) + pad * 2

            with mss.mss() as sct:
                monitor = {"top": int(top), "left": int(left), "width": int(width), "height": int(height)}
                sct_img = sct.grab(monitor)
                screen_bgr = np.array(sct_img)[:, :, :3]

            res = cv2.matchTemplate(screen_bgr, tmpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)

            if max_val >= 0.85:
                return True, (cfg.get("r", 0), cfg.get("g", 0), cfg.get("b", 0))

            return False, (0, 0, 0)
        except:
            return False, (0, 0, 0)

    def _check_single_pixel(self, point, mode):
        try:
            with mss.mss() as sct:
                monitor = {"top": point["y"], "left": point["x"], "width": 1, "height": 1}
                sct_img = sct.grab(monitor)
                c = sct_img.pixel(0, 0)

            if mode == "match":
                match = math.sqrt((c[0] - point["r"]) ** 2 + (c[1] - point["g"]) ** 2 + (c[2] - point["b"]) ** 2) < 35
            elif mode == "hp":
                match = c[0] > (point["r"] * 0.4)
            elif mode == "mana":
                match = c[2] > (point["b"] * 0.4)
            elif mode == "merc":
                match = c[1] > (point["g"] * 0.4) and c[1] > c[0]
            else:
                match = False

            return match, c
        except:
            return False, (0, 0, 0)

    def _press_key(self, k, shift=False):
        if sys_hooks and k in "1234":
            c = sys_hooks.SCANCODES.get(k)
            if c:
                if shift: sys_hooks.press_key(sys_hooks.SCANCODES['shift'])
                sys_hooks.click_key(c)
                if shift: sys_hooks.release_key(sys_hooks.SCANCODES['shift'])