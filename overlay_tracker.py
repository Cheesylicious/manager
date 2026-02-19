import customtkinter as ctk
import tkinter as tk
import time
import threading
import math
import winsound
import ctypes
import mss

from overlay_config import STEPS_INFO, TrackerConfig

try:
    import sys_hooks
except ImportError:
    try:
        import d2r_input as sys_hooks
    except ImportError:
        sys_hooks = None

try:
    from pixel_scanner import DropWatcher
except ImportError:
    try:
        from d2r_drops import DropWatcher
    except ImportError:
        DropWatcher = None

try:
    from progress_calc import XPWatcher
except ImportError:
    try:
        from d2r_xp import XPWatcher
    except ImportError:
        XPWatcher = None

try:
    from zone_scanner import ZoneWatcher
except ImportError:
    ZoneWatcher = None


class RunTrackerOverlay(ctk.CTkToplevel):
    def __init__(self, parent, config_data, configurator=None):
        super().__init__(parent)
        self.config_data = config_data
        self.configurator = configurator

        self.sensors = {k: config_data.get(k) for k in STEPS_INFO.keys()}

        self.hp_key = config_data.get("hp_key", "Aus")
        self.mana_key = config_data.get("mana_key", "Aus")
        self.merc_key = config_data.get("merc_key", "Aus")
        self.hp_sound = config_data.get("hp_sound", True)
        self.mana_sound = config_data.get("mana_sound", False)
        self.merc_sound = config_data.get("merc_sound", True)
        self.current_width = config_data.get("width", 340)
        self.current_height = config_data.get("height", 200)
        self.hp_delay = float(config_data.get("hp_delay", 0.8))
        self.mana_delay = float(config_data.get("mana_delay", 0.8))
        self.merc_delay = float(config_data.get("merc_delay", 0.8))

        self.overrideredirect(True)
        self.attributes('-topmost', True, '-alpha', config_data.get("alpha", 1.0))
        self.bg_color = "#000001"
        self.config(bg=self.bg_color)
        self.attributes("-transparentcolor", self.bg_color)
        self.geometry(f"{self.current_width}x{self.current_height}+20+20")

        # Liste für die im aktuellen Run gefundenen Runen
        self.current_run_drops = []

        # Hier übergeben wir unseren Callback (on_drop_detected) an den Scanner
        self.drop_watcher = DropWatcher(config_data, drop_callback=self.on_drop_detected) if DropWatcher else None
        self.xp_watcher = XPWatcher(config_data) if XPWatcher else None
        self.zone_watcher = ZoneWatcher(config_data) if ZoneWatcher else None

        self.main_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", border_width=1, border_color="#444444",
                                       corner_radius=8)
        self.main_frame.pack(fill="both", expand=True, padx=2, pady=2)

        self.slider_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent", width=20)
        self.slider_frame.pack(side="right", fill="y", padx=(0, 5), pady=10)
        self.alpha_slider = ctk.CTkSlider(self.slider_frame, from_=0.2, to=1.0, orientation="vertical",
                                          command=self.change_alpha, height=100, width=12)
        self.alpha_slider.set(config_data.get("alpha", 1.0))
        self.alpha_slider.pack(pady=5)

        self.content_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.content_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.lbl_status = ctk.CTkLabel(self.content_frame, text="WARTEN...", font=("Roboto", 10, "bold"),
                                       text_color="#888888")
        self.lbl_status.pack()

        self.lbl_zone = ctk.CTkLabel(self.content_frame, text="📍 Zone: Unbekannt", font=("Roboto", 12, "bold"),
                                     text_color="#00ccff")
        self.lbl_zone.pack(pady=(0, 2))

        # --- NEU: Live-Loot Anzeige direkt im Overlay ---
        self.lbl_live_loot = ctk.CTkLabel(self.content_frame, text="", font=("Roboto", 11, "bold"),
                                          text_color="#FFD700")
        self.lbl_live_loot.pack(pady=(0, 2))

        self.lbl_timer = ctk.CTkLabel(self.content_frame, text="00:00.00",
                                      font=("Roboto Mono", int(self.current_width * 0.11), "bold"),
                                      text_color="#FFD700", cursor="hand2")
        self.lbl_timer.pack(pady=(0, 2))

        self.lbl_xp = ctk.CTkLabel(self.content_frame, text="EXP: --% | --%/h | RUNS: --", font=("Roboto Mono", 11),
                                   text_color="#ffd700")
        if config_data.get("xp_active"):
            self.lbl_xp.pack()

        self.stats_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.stats_frame.pack(fill="x", padx=5)
        self.lbl_runs = ctk.CTkLabel(self.stats_frame, text="Runs: 0", font=("Roboto", 11), text_color="#cccccc")
        self.lbl_runs.pack(side="left")
        self.lbl_last = ctk.CTkLabel(self.stats_frame, text="Letzter: --:--", font=("Roboto", 11), text_color="#888888")
        self.lbl_last.pack(side="right")

        self.avg_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.avg_frame.pack(fill="x", padx=5)
        self.lbl_avg = ctk.CTkLabel(self.avg_frame, text="Ø --:--", font=("Roboto", 11, "bold"), text_color="#00ccff")
        self.lbl_avg.pack(side="right")

        self.guardian_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.guardian_frame.pack(fill="x", padx=5, pady=(2, 5), side="bottom")

        self.sensors_ui = {}
        sensor_configs = [("hp", "❤️ LP", "#FF3333"), ("mana", "💧 MP", "#00ccff"), ("merc", "🛡️ SÖLD", "#2da44e")]

        for key, title, color in sensor_configs:
            f = ctk.CTkFrame(self.guardian_frame, fg_color="#151515", corner_radius=6)
            f.pack(side="left", fill="both", expand=True, padx=2)

            top_f = ctk.CTkFrame(f, fg_color="transparent")
            top_f.pack(fill="x", padx=4, pady=(4, 0))

            indicator = ctk.CTkFrame(top_f, width=12, height=12, corner_radius=6, fg_color="#000000")
            indicator.pack(side="left", padx=(0, 4))

            lbl_title = ctk.CTkLabel(top_f, text=title, font=("Roboto", 11, "bold"), text_color=color)
            lbl_title.pack(side="left")

            btn_sound = ctk.CTkButton(top_f, text="🔊" if self.config_data.get(f"{key}_sound", True) else "🔇",
                                      width=20, height=20, fg_color="transparent", hover_color="#333333",
                                      command=lambda k=key: self.toggle_individual_sound(k))
            btn_sound.pack(side="right")

            lbl_status = ctk.CTkLabel(f, text="AUS", font=("Roboto Mono", 10, "bold"), text_color="#555555")
            lbl_status.pack(pady=(0, 4))

            self.sensors_ui[key] = {"title": lbl_title, "status": lbl_status, "sound": btn_sound, "color": color,
                                    "indicator": indicator}

        self.history_frame = ctk.CTkFrame(self.content_frame, fg_color="#0d0d0d", corner_radius=6)

        self.resizer = ctk.CTkLabel(self.main_frame, text="⤡", font=("Arial", 14), text_color="#444", cursor="sizing")
        self.resizer.place(relx=1.0, rely=1.0, anchor="se", x=-2, y=-2)
        self.resizer.bind("<Button-1>", self.resize_start)
        self.resizer.bind("<B1-Motion>", self.resize_move)
        self.resizer.bind("<ButtonRelease-1>", self.resize_end)

        self.run_history, self.is_expanded, self.monitoring, self.in_game, self.paused = [], False, False, False, False
        self.start_time, self.run_count, self.last_alarm_time = 0, 0, 0
        self.last_potions = {"hp": 0, "mana": 0, "merc": 0}
        self.stop_event = threading.Event()
        self.current_state = "UNKNOWN"
        self.last_xp_check = 0
        self.last_ghost_toggle = 0
        self.last_zone_check = ""

        self.context_menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white")
        self.context_menu.add_command(label="⏸️ Pause", command=self.toggle_pause)
        self.context_menu.add_command(label="👻 Ghost-Modus (EIN/AUS per Strg+Alt+G)",
                                      command=lambda: self.set_clickthrough(True))
        self.context_menu.add_command(label="🔄 Run-Timer zurücksetzen", command=self.reset_current_run)
        self.context_menu.add_command(label="🗑️ Alle Daten zurücksetzen", command=self.reset_session)
        self.context_menu.add_command(label="❌ Beenden", command=self.stop_tracking)

        for w in [self.main_frame, self.content_frame, self.lbl_status, self.stats_frame, self.lbl_timer, self.lbl_xp,
                  self.avg_frame, self.lbl_zone, self.lbl_live_loot]:
            w.bind("<Button-1>", self.start_move)
            w.bind("<B1-Motion>", self.do_move)
            w.bind("<Button-3>", self.show_context_menu)
        self.lbl_timer.bind("<Button-1>", self.toggle_history)
        self.x = self.y = 0

        self.after(200, self.apply_stealth_mode)

        if self.config_data.get("clickthrough", False):
            self.after(300, lambda: self.set_clickthrough(True))

    # --- NEU: Live-Update wenn eine Rune gefunden wurde ---
    def on_drop_detected(self, drop_name):
        if self.in_game and drop_name not in self.current_run_drops:
            self.current_run_drops.append(drop_name)
            drop_str = ", ".join(self.current_run_drops)
            self.lbl_live_loot.configure(text=f"💎 Loot: [{drop_str}]")

    def reload_config(self):
        self.hp_key = self.config_data.get("hp_key", "Aus")
        self.mana_key = self.config_data.get("mana_key", "Aus")
        self.merc_key = self.config_data.get("merc_key", "Aus")
        self.hp_delay = float(self.config_data.get("hp_delay", 0.8))
        self.mana_delay = float(self.config_data.get("mana_delay", 0.8))
        self.merc_delay = float(self.config_data.get("merc_delay", 0.8))
        self.hp_sound = self.config_data.get("hp_sound", True)
        self.mana_sound = self.config_data.get("mana_sound", False)
        self.merc_sound = self.config_data.get("merc_sound", True)

        if hasattr(self, "sensors_ui"):
            for key in ["hp", "mana", "merc"]:
                sound_on = self.config_data.get(f"{key}_sound", True)
                self.sensors_ui[key]["sound"].configure(text="🔊" if sound_on else "🔇")

    def toggle_individual_sound(self, key):
        current = self.config_data.get(f"{key}_sound", True)
        new_val = not current
        self.config_data[f"{key}_sound"] = new_val
        TrackerConfig.save(self.config_data)

        setattr(self, f"{key}_sound", new_val)
        self.sensors_ui[key]["sound"].configure(text="🔊" if new_val else "🔇")

        if self.configurator:
            self.configurator.sync_ui()

    def apply_stealth_mode(self):
        try:
            WDA_EXCLUDEFROMCAPTURE = 0x0011
            hwnd = int(self.wm_frame(), 16)
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
        except Exception:
            pass

    def toggle_ghost_hotkey(self):
        now = time.time()
        if now - self.last_ghost_toggle < 1.0: return
        self.last_ghost_toggle = now

        current_state = self.config_data.get("clickthrough", False)
        new_state = not current_state
        self.set_clickthrough(new_state)
        winsound.Beep(2000 if new_state else 1000, 150)

    def set_clickthrough(self, enable):
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            if not hwnd: hwnd = self.winfo_id()

            GWL_EXSTYLE = -20
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_LAYERED = 0x00080000

            exstyle = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if enable:
                exstyle |= (WS_EX_TRANSPARENT | WS_EX_LAYERED)
                self.main_frame.configure(border_color="#FF3333")
            else:
                exstyle &= ~WS_EX_TRANSPARENT
                self.main_frame.configure(border_color="#444444")

            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle)
            self.config_data["clickthrough"] = enable
            TrackerConfig.save(self.config_data)
        except Exception as e:
            pass

    def change_alpha(self, v):
        self.attributes('-alpha', v)
        self.config_data["alpha"] = v

    def start_move(self, e):
        self.x, self.y = e.x, e.y

    def do_move(self, e):
        self.geometry(f"+{self.winfo_x() + (e.x - self.x)}+{self.winfo_y() + (e.y - self.y)}")

    def show_context_menu(self, e):
        self.context_menu.tk_popup(e.x_root, e.y_root)

    def toggle_pause(self):
        self.paused = not self.paused
        self.lbl_status.configure(text="⏸️ PAUSIERT" if self.paused else "WARTEN...")

    def reset_current_run(self):
        self.start_time = 0
        self.in_game = False
        self.current_state = "UNKNOWN"
        self.current_run_drops = []
        self.lbl_timer.configure(text="00:00.00")
        self.lbl_live_loot.configure(text="")  # Feld wieder leeren

    def reset_session(self):
        self.run_history, self.run_count = [], 0
        self.lbl_runs.configure(text="Runs: 0")
        self.lbl_last.configure(text="Letzter: --:--")
        self.lbl_avg.configure(text="Ø --:--")
        if self.xp_watcher:
            self.xp_watcher.session_start_xp = None
            self.xp_watcher.session_start_time = None
        self._update_xp_display(do_scan=False)
        self.reset_current_run()

    def resize_start(self, e):
        self.rs_x, self.rs_y, self.rs_w, self.rs_h = e.x_root, e.y_root, self.winfo_width(), self.winfo_height()

    def resize_move(self, e):
        nw, nh = max(200, min(500, self.rs_w + (e.x_root - self.rs_x))), max(150, min(400, self.rs_h + (
                e.y_root - self.rs_y)))
        self.geometry(f"{nw}x{nh}")
        self.current_width, self.current_height = nw, nh
        self.lbl_timer.configure(font=("Roboto Mono", int(nw * 0.11), "bold"))

    def resize_end(self, e):
        self.config_data.update({"width": self.current_width, "height": self.current_height})
        TrackerConfig.save(self.config_data)

    def toggle_history(self, event=None):
        self.is_expanded = not self.is_expanded
        if self.is_expanded:
            self.geometry(f"{self.current_width}x{self.current_height + 250}")
            self.history_frame.pack(fill="both", expand=True, padx=5, pady=(0, 10), before=self.guardian_frame)
            self.update_history_list()
        else:
            self.geometry(f"{self.current_width}x{self.current_height}")
            self.history_frame.pack_forget()

    def update_history_list(self):
        for w in self.history_frame.winfo_children(): w.destroy()
        recent = self.run_history[-10:]
        recent.reverse()

        for i, run_data in enumerate(recent):
            row = ctk.CTkFrame(self.history_frame, fg_color="transparent")
            row.pack(fill="x", padx=5, pady=2)

            dur = run_data["duration"]
            drops = run_data.get("drops", [])

            ctk.CTkLabel(row, text=f"{len(self.run_history) - i}.", font=("Roboto Mono", 10)).pack(side="left")

            time_lbl = ctk.CTkLabel(row, text=f"{int(dur // 60):02}:{int(dur % 60):02}", font=("Roboto Mono", 10))
            time_lbl.pack(side="right")

            if drops:
                drop_str = " + ".join(drops)
                ctk.CTkLabel(row, text=f"[{drop_str}]", font=("Roboto", 10, "bold"), text_color="#FFD700").pack(
                    side="right", padx=(0, 10))

    def start_tracking(self):
        self.monitoring = True
        self.stop_event.clear()
        if self.drop_watcher: self.drop_watcher.start()
        if self.zone_watcher: self.zone_watcher.start()
        threading.Thread(target=self._logic_loop, daemon=True).start()
        self.update_timer_gui()

    def stop_tracking(self):
        self.monitoring = False
        self.stop_event.set()
        if self.drop_watcher: self.drop_watcher.stop()
        if self.zone_watcher: self.zone_watcher.stop()
        TrackerConfig.save(self.config_data)
        self.destroy()

    def finish_run(self):
        if self.start_time == 0: return
        dur = time.time() - self.start_time

        self.run_history.append({
            "duration": dur,
            "drops": list(self.current_run_drops)
        })

        self.run_count += 1
        self.lbl_runs.configure(text=f"Runs: {self.run_count}")
        self.lbl_last.configure(text=f"Letzter: {int(dur // 60):02}:{int(dur % 60):02}")

        avg = sum(r["duration"] for r in self.run_history) / max(1, self.run_count)
        self.lbl_avg.configure(text=f"Ø {int(avg // 60):02}:{int(avg % 60):02}")

        self._update_xp_display(do_scan=False)

        if self.is_expanded: self.update_history_list()

        self.start_time = 0
        self.current_run_drops = []
        self.lbl_live_loot.configure(text="")  # Feld für neuen Run leeren

    def _update_xp_display(self, do_scan=True):
        if self.xp_watcher and self.config_data.get("xp_active"):
            try:
                if do_scan:
                    xp, xph = self.xp_watcher.get_current_xp_percent()
                else:
                    xp = getattr(self.xp_watcher, 'current_xp', 0.0)
                    xph = getattr(self.xp_watcher, 'current_xph', "0.0")

                runs = self.xp_watcher.estimate_runs_to_level(self.run_count)
                self.lbl_xp.configure(text=f"EXP: {xp}% | {xph}%/h | RUNS: {runs}")
            except Exception as e:
                pass

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
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length == 0: return False
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            return "Diablo" in buff.value
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
        while not self.stop_event.is_set():
            ctrl = ctypes.windll.user32.GetAsyncKeyState(0x11) & 0x8000
            alt = ctypes.windll.user32.GetAsyncKeyState(0x12) & 0x8000
            g_key = ctypes.windll.user32.GetAsyncKeyState(0x47) & 0x8000
            if ctrl and alt and g_key:
                self.toggle_ghost_hotkey()

            if self.paused: time.sleep(0.5); continue

            try:
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
                    if self._is_d2r_foreground():
                        self.lbl_status.configure(text="AKTIV IM SPIEL", text_color="#2da44e")
                        now = time.time()

                        if self.zone_watcher:
                            current_z = self.zone_watcher.current_zone
                            if current_z != self.last_zone_check:
                                self.lbl_zone.configure(text=f"📍 {current_z}")
                                self.last_zone_check = current_z

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

                    else:
                        self.lbl_status.configure(text="TABBED OUT (Auto-Pot PAUSE)", text_color="#FF9500")
                        for key in ["hp", "mana", "merc"]:
                            assigned_key = self.config_data.get(f"{key}_key", "Aus")
                            if assigned_key == "Aus":
                                self.sensors_ui[key]["status"].configure(text="AUS", text_color="#555555")
                            else:
                                self.sensors_ui[key]["status"].configure(text="PAUSE", text_color="#FF9500")

                elif self.current_state == "MENU":
                    self.lbl_status.configure(text="MENÜ / LOBBY", text_color="#cf222e")

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
                match, c = self._check_single_pixel(point, mode)
                if match: matches += 1
                last_color = c
            return (matches > 0 and matches >= (len(cfg) / 2)), last_color

        return self._check_single_pixel(cfg, mode)

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

    def update_timer_gui(self):
        if self.monitoring and not self.stop_event.is_set():
            if self.in_game and self.start_time > 0 and not self.paused:
                dur = time.time() - self.start_time
                self.lbl_timer.configure(text=f"{int(dur // 60):02}:{int(dur % 60):02}.{int((dur % 1) * 100):02}")
            self.after(50, self.update_timer_gui)