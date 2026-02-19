import customtkinter as ctk
import tkinter as tk
import time
import threading
import os
import json
import math
import winsound
from PIL import ImageGrab

# Importiere Input-Modul für Tastenanschläge
try:
    import d2r_input
except ImportError:
    d2r_input = None

# Importiere externes Drop-Modul
try:
    from d2r_drops import DropWatcher
except ImportError:
    DropWatcher = None

# Importiere externes XP-Modul
try:
    from d2r_xp import XPWatcher
except ImportError:
    XPWatcher = None

# ------------------------------------------------------------------
# KONFIGURATION & SPEICHERUNG
# ------------------------------------------------------------------
TRACKER_CONFIG_FILE = "d2r_tracker_config.json"


class TrackerConfig:
    @staticmethod
    def load():
        if os.path.exists(TRACKER_CONFIG_FILE):
            try:
                with open(TRACKER_CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    defaults = {
                        "hp_delay": "0.8", "mana_delay": "0.8", "merc_delay": "0.8",
                        "hp_key": "Aus", "mana_key": "Aus", "merc_key": "Aus",
                        "hp_sound": True, "mana_sound": False, "merc_sound": True, "drop_sound": True,
                        "width": 360, "height": 260, "alpha": 1.0,
                        "drop_alert_active": False, "xp_active": False
                    }
                    for k, v in defaults.items():
                        if k not in data: data[k] = v
                    return data
            except:
                pass
        return {
            "alpha": 1.0, "hp_key": "Aus", "mana_key": "Aus", "merc_key": "Aus",
            "hp_delay": "0.8", "mana_delay": "0.8", "merc_delay": "0.8",
            "hp_sound": True, "mana_sound": False, "merc_sound": True, "drop_sound": True,
            "width": 360, "height": 260, "drop_alert_active": False, "xp_active": False
        }

    @staticmethod
    def save(data):
        try:
            with open(TRACKER_CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except:
            pass


# ------------------------------------------------------------------
# SETUP WIZARD (8 SCHRITTE)
# ------------------------------------------------------------------
class MultiCalibrationOverlay(ctk.CTkToplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.step = 1
        self.results = {}

        self.title("D2R Tracker Setup")
        self.geometry("550x550")
        self.attributes('-topmost', True)

        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - 550) // 2}+{(sh - 550) // 2}")

        self.lbl_step = ctk.CTkLabel(self, text="SCHRITT 1/8", font=("Roboto", 22, "bold"), text_color="#FFD700")
        self.lbl_step.pack(pady=(25, 5))

        self.lbl_title_step = ctk.CTkLabel(self, text="...", font=("Roboto", 16, "bold"), text_color="white")
        self.lbl_title_step.pack(pady=(0, 15))

        self.lbl_desc = ctk.CTkLabel(self, text="...", font=("Roboto", 14), text_color="#dddddd", wraplength=500,
                                     justify="center")
        self.lbl_desc.pack(pady=10, padx=30)

        self.lbl_count = ctk.CTkLabel(self, text="Bereit?", font=("Roboto", 28, "bold"), text_color="#888888")
        self.lbl_count.pack(pady=20)

        self.btn_action = ctk.CTkButton(self, text="Start (5 Sek)", command=self.start_countdown, fg_color="#1f538d",
                                        height=50, font=("Roboto", 14, "bold"))
        self.btn_action.pack(pady=10)

        self.setup_step(1)

    def setup_step(self, s):
        self.step = s
        self.lbl_step.configure(text=f"SCHRITT {s}/8")
        self.btn_action.configure(state="normal", text="Start (5 Sek)")

        texts = {
            1: ("OFFLINE / CHARAKTER", "Klicke auf ein Element der Charakter-Auswahl (z.B. 'Spielen' Button)."),
            2: ("LOBBY / CHANNEL", "Klicke auf ein Element der Online-Lobby (z.B. 'Spiel erstellen')."),
            3: ("IN-GAME ERKENNUNG", "Gehe ins Spiel. Klicke auf den GOLDENEN RAHMEN einer Kugel (Statisch!)."),
            4: ("HP ALARM", "Klicke auf die ROTE KUGEL bei ca. 30% Höhe."),
            5: ("MANA ALARM", "Klicke auf die BLAUE KUGEL bei ca. 30% Höhe."),
            6: ("SÖLDNER ALARM", "Klicke auf den Lebensbalken des Söldners (oben links)."),
            7: ("XP-BALKEN START", "Klicke auf das LINKE Ende deines XP-Balkens (unten)."),
            8: ("XP-BALKEN ENDE", "Klicke auf das RECHTE Ende deines XP-Balkens (unten).")
        }
        title, desc = texts[s]
        self.lbl_title_step.configure(text=title)
        self.lbl_desc.configure(text=desc)

    def start_countdown(self):
        self.btn_action.configure(state="disabled")
        threading.Thread(target=self._count_logic, daemon=True).start()

    def _count_logic(self):
        for i in range(5, 0, -1):
            self.lbl_count.configure(text=str(i))
            time.sleep(1)

        try:
            x, y = self.winfo_pointerxy()
            img = ImageGrab.grab(bbox=(x, y, x + 1, y + 1))
            c = img.getpixel((0, 0))
            winsound.Beep(1500, 100)
            data = {"x": x, "y": y, "r": c[0], "g": c[1], "b": c[2]}

            keys = {1: "menu_sensor_1", 2: "menu_sensor_2", 3: "game_sensor", 4: "hp_sensor", 5: "mana_sensor",
                    6: "merc_sensor", 7: "xp_start", 8: "xp_end"}
            self.results[keys[self.step]] = data

            if self.step < 8:
                self.after(500, lambda: self.setup_step(self.step + 1))
            else:
                self.after(500, self.finish)
        except:
            pass

    def finish(self):
        self.callback(self.results)
        self.destroy()


# ------------------------------------------------------------------
# OVERLAY (HUD)
# ------------------------------------------------------------------
class RunTrackerOverlay(ctk.CTkToplevel):
    def __init__(self, parent, config_data):
        super().__init__(parent)
        self.config_data = config_data

        # Sensoren laden
        self.sensors = {k: config_data.get(k) for k in
                        ["menu_sensor_1", "menu_sensor_2", "game_sensor", "hp_sensor", "mana_sensor", "merc_sensor"]}

        # Einstellungen
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

        # Fenster Setup
        self.overrideredirect(True)
        self.attributes('-topmost', True, '-alpha', config_data.get("alpha", 1.0))
        self.bg_color = "#000001"
        self.config(bg=self.bg_color)
        self.attributes("-transparentcolor", self.bg_color)
        self.geometry(f"{self.current_width}x{self.current_height}+20+20")

        # Helfer Klassen
        self.drop_watcher = DropWatcher(config_data) if DropWatcher else None
        self.xp_watcher = XPWatcher(config_data) if XPWatcher else None

        # UI
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

        self.lbl_status = ctk.CTkLabel(self.content_frame, text="WAITING...", font=("Roboto", 10, "bold"),
                                       text_color="#888888")
        self.lbl_status.pack()

        self.lbl_timer = ctk.CTkLabel(self.content_frame, text="00:00.00",
                                      font=("Roboto Mono", int(self.current_width * 0.11), "bold"),
                                      text_color="#FFD700", cursor="hand2")
        self.lbl_timer.pack(pady=(0, 2))

        self.lbl_xp = ctk.CTkLabel(self.content_frame, text="XP: --% | Runs to Lv: --", font=("Roboto Mono", 11),
                                   text_color="#ffd700")
        if config_data.get("xp_active"): self.lbl_xp.pack()

        self.stats_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.stats_frame.pack(fill="x", padx=5)
        self.lbl_runs = ctk.CTkLabel(self.stats_frame, text="Runs: 0", font=("Roboto", 11), text_color="#cccccc")
        self.lbl_runs.pack(side="left")
        self.lbl_last = ctk.CTkLabel(self.stats_frame, text="Last: --:--", font=("Roboto", 11), text_color="#888888")
        self.lbl_last.pack(side="right")

        self.avg_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.avg_frame.pack(fill="x", padx=5)
        self.lbl_avg = ctk.CTkLabel(self.avg_frame, text="Ø --:--", font=("Roboto", 11, "bold"), text_color="#00ccff")
        self.lbl_avg.pack(side="right")

        self.guardian_frame = ctk.CTkFrame(self.content_frame, fg_color="#111111", corner_radius=4, height=30)
        self.guardian_frame.pack(fill="x", padx=5, pady=(2, 5), side="bottom")
        self.lbl_hp = ctk.CTkLabel(self.guardian_frame, text=self.fmt_status("HP", False),
                                   font=("Roboto Mono", 9, "bold"), text_color="#2da44e")
        self.lbl_hp.pack(side="left", padx=5)
        self.lbl_mp = ctk.CTkLabel(self.guardian_frame, text=self.fmt_status("MP", False),
                                   font=("Roboto Mono", 9, "bold"), text_color="#00ccff")
        self.lbl_mp.pack(side="left", padx=2)
        self.lbl_mc = ctk.CTkLabel(self.guardian_frame, text=self.fmt_status("MERC", False),
                                   font=("Roboto Mono", 9, "bold"), text_color="#aaaaaa")
        self.lbl_mc.pack(side="left", padx=2)
        self.btn_mute = ctk.CTkButton(self.guardian_frame, text="🔊", width=25, height=18, fg_color="transparent",
                                      command=self.toggle_mute)
        self.btn_mute.pack(side="right", padx=2)

        self.history_frame = ctk.CTkFrame(self.content_frame, fg_color="#0d0d0d", corner_radius=6)

        self.resizer = ctk.CTkLabel(self.main_frame, text="⤡", font=("Arial", 14), text_color="#444", cursor="sizing")
        self.resizer.place(relx=1.0, rely=1.0, anchor="se", x=-2, y=-2)
        self.resizer.bind("<Button-1>", self.resize_start);
        self.resizer.bind("<B1-Motion>", self.resize_move);
        self.resizer.bind("<ButtonRelease-1>", self.resize_end)

        self.run_history, self.is_expanded, self.monitoring, self.in_game, self.paused = [], False, False, False, False
        self.start_time, self.run_count, self.alarm_active, self.last_alarm_time = 0, 0, True, 0
        self.last_potions = {"hp": 0, "mana": 0, "merc": 0}
        self.stop_event = threading.Event()

        self.context_menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white")
        self.context_menu.add_command(label="⏸️ Pause", command=self.toggle_pause)
        self.context_menu.add_command(label="🔄 Reset Run", command=self.reset_current_run)
        self.context_menu.add_command(label="🗑️ Reset Session", command=self.reset_session)
        self.context_menu.add_command(label="❌ Schließen", command=self.stop_tracking)

        for w in [self.main_frame, self.content_frame, self.lbl_status, self.stats_frame, self.lbl_timer, self.lbl_xp,
                  self.avg_frame]:
            w.bind("<Button-1>", self.start_move);
            w.bind("<B1-Motion>", self.do_move);
            w.bind("<Button-3>", self.show_context_menu)
        self.lbl_timer.bind("<Button-1>", self.toggle_history);
        self.x = self.y = 0

    def fmt_status(self, t, active):
        dot = "●" if active else "○"
        keys = {"HP": self.hp_key, "MP": self.mana_key, "MERC": self.merc_key}
        k = keys[t] if keys[t] != "Aus" else "-"
        return f"{t[0]}{dot}:{k}"

    def change_alpha(self, v):
        self.attributes('-alpha', v); self.config_data["alpha"] = v

    def start_move(self, e):
        self.x, self.y = e.x, e.y

    def do_move(self, e):
        self.geometry(f"+{self.winfo_x() + (e.x - self.x)}+{self.winfo_y() + (e.y - self.y)}")

    def show_context_menu(self, e):
        self.context_menu.tk_popup(e.x_root, e.y_root)

    def toggle_pause(self):
        self.paused = not self.paused; self.lbl_status.configure(text="⏸️ PAUSED" if self.paused else "WAITING...")

    def toggle_mute(self):
        self.alarm_active = not self.alarm_active; self.btn_mute.configure(text="🔊" if self.alarm_active else "🔇")

    def reset_current_run(self):
        self.start_time = 0; self.in_game = False; self.lbl_timer.configure(text="00:00.00")

    def reset_session(self):
        self.run_history, self.run_count = [], 0
        self.lbl_runs.configure(text="Runs: 0");
        self.lbl_last.configure(text="Last: --:--");
        self.lbl_avg.configure(text="Ø --:--")
        if self.xp_watcher: self.xp_watcher.session_start_xp = None
        self.reset_current_run()

    def resize_start(self, e):
        self.rs_x, self.rs_y, self.rs_w, self.rs_h = e.x_root, e.y_root, self.winfo_width(), self.winfo_height()

    def resize_move(self, e):
        nw, nh = max(200, min(500, self.rs_w + (e.x_root - self.rs_x))), max(150, min(400, self.rs_h + (
                    e.y_root - self.rs_y)))
        self.geometry(f"{nw}x{nh}");
        self.current_width, self.current_height = nw, nh
        self.lbl_timer.configure(font=("Roboto Mono", int(nw * 0.11), "bold"))

    def resize_end(self, e):
        self.config_data.update({"width": self.current_width, "height": self.current_height}); TrackerConfig.save(
            self.config_data)

    def toggle_history(self, event=None):
        self.is_expanded = not self.is_expanded
        if self.is_expanded:
            self.geometry(f"{self.current_width}x{self.current_height + 220}");
            self.history_frame.pack(fill="both", expand=True, padx=5, pady=(0, 10), before=self.guardian_frame);
            self.update_history_list()
        else:
            self.geometry(f"{self.current_width}x{self.current_height}"); self.history_frame.pack_forget()

    def update_history_list(self):
        for w in self.history_frame.winfo_children(): w.destroy()
        recent = self.run_history[-10:];
        recent.reverse()
        for i, dur in enumerate(recent):
            row = ctk.CTkFrame(self.history_frame, fg_color="transparent")
            row.pack(fill="x", padx=5)
            ctk.CTkLabel(row, text=f"{len(self.run_history) - i}.", font=("Roboto Mono", 9)).pack(side="left")
            ctk.CTkLabel(row, text=f"{int(dur // 60):02}:{int(dur % 60):02}", font=("Roboto Mono", 9)).pack(
                side="right")

    def start_tracking(self):
        self.monitoring = True;
        self.stop_event.clear()
        if self.drop_watcher: self.drop_watcher.start()
        threading.Thread(target=self._logic_loop, daemon=True).start()
        self.update_timer_gui()

    def stop_tracking(self):
        self.monitoring = False
        self.stop_event.set()
        if self.drop_watcher:
            self.drop_watcher.stop()
        TrackerConfig.save(self.config_data)
        self.destroy()

    def finish_run(self):
        if self.start_time == 0: return
        dur = time.time() - self.start_time
        self.run_history.append(dur);
        self.run_count += 1
        self.lbl_runs.configure(text=f"Runs: {self.run_count}")
        self.lbl_last.configure(text=f"Last: {int(dur // 60):02}:{int(dur % 60):02}")
        avg = sum(self.run_history) / self.run_count
        self.lbl_avg.configure(text=f"Ø {int(avg // 60):02}:{int(avg % 60):02}")
        if self.xp_watcher and self.config_data.get("xp_active"):
            xp = self.xp_watcher.get_current_xp_percent()
            runs = self.xp_watcher.estimate_runs_to_level(self.run_count)
            self.lbl_xp.configure(text=f"XP: {xp}% | Runs to Lv: {runs}")
        if self.is_expanded: self.update_history_list()
        self.start_time = 0

    def _logic_loop(self):
        cg, cm = 0, 0
        while not self.stop_event.is_set():
            if self.paused: time.sleep(0.5); continue
            try:
                in_game = self._check_color(self.sensors["game_sensor"])
                in_menu = self._check_color(self.sensors["menu_sensor_1"]) or self._check_color(
                    self.sensors["menu_sensor_2"])
                cg = cg + 1 if in_game else 0;
                cm = cm + 1 if in_menu else 0
                if cg >= 2:
                    if not self.in_game: self.start_time = time.time(); self.in_game = True
                    now = time.time()
                    hp, mp, mc = self._check_color(self.sensors["hp_sensor"], "hp"), self._check_color(
                        self.sensors["mana_sensor"], "mana"), self._check_color(self.sensors["merc_sensor"], "merc")
                    if not hp and now - self.last_potions["hp"] > self.hp_delay:
                        self._press_key(self.hp_key)
                        self.last_potions["hp"] = now
                        if self.alarm_active and self.hp_sound and now - self.last_alarm_time > 2:
                            winsound.Beep(1200, 150);
                            self.last_alarm_time = now
                    if not mp and now - self.last_potions["mana"] > self.mana_delay:
                        self._press_key(self.mana_key)
                        self.last_potions["mana"] = now
                        if self.alarm_active and self.mana_sound and now - self.last_alarm_time > 2:
                            winsound.Beep(800, 100);
                            self.last_alarm_time = now
                    if not mc and now - self.last_potions["merc"] > self.merc_delay:
                        self._press_key(self.merc_key, True)
                        self.last_potions["merc"] = now
                        if self.alarm_active and self.merc_sound and now - self.last_alarm_time > 2:
                            winsound.Beep(1000, 150);
                            self.last_alarm_time = now
                    self.lbl_hp.configure(text=self.fmt_status("HP", hp), text_color="#2da44e" if hp else "#FF3333")
                    self.lbl_mp.configure(text=self.fmt_status("MP", mp), text_color="#00ccff" if mp else "#FF9900")
                    self.lbl_mc.configure(text=self.fmt_status("MERC", mc), text_color="#aaaaaa" if mc else "#8B0000")
                    self.lbl_status.configure(text="IN GAME", text_color="#2da44e")
                elif cm >= 2:
                    if self.in_game: self.finish_run(); self.in_game = False
                    self.lbl_status.configure(text="MENU / LOBBY", text_color="#cf222e")
                time.sleep(0.1)
            except:
                time.sleep(1)

    def _check_color(self, cfg, mode="match"):
        if not cfg: return False
        try:
            image = ImageGrab.grab(bbox=(cfg["x"], cfg["y"], cfg["x"] + 1, cfg["y"] + 1))
            c = image.getpixel((0, 0))
            if mode == "match": return math.sqrt(
                (c[0] - cfg["r"]) ** 2 + (c[1] - cfg["g"]) ** 2 + (c[2] - cfg["b"]) ** 2) < 35
            if mode == "hp": return c[0] > (cfg["r"] * 0.4)
            if mode == "mana": return c[2] > (cfg["b"] * 0.4)
            if mode == "merc": return math.sqrt(
                (c[0] - cfg["r"]) ** 2 + (c[1] - cfg["g"]) ** 2 + (c[2] - cfg["b"]) ** 2) < 80
            return False
        except:
            return False

    def _press_key(self, k, shift=False):
        if d2r_input and k in "1234":
            c = d2r_input.SCANCODES.get(k)
            if c:
                if shift: d2r_input.press_key(d2r_input.SCANCODES['shift'])
                d2r_input.click_key(c)
                if shift: d2r_input.release_key(d2r_input.SCANCODES['shift'])

    def update_timer_gui(self):
        if self.monitoring and not self.stop_event.is_set():
            if self.in_game and self.start_time > 0 and not self.paused:
                dur = time.time() - self.start_time
                self.lbl_timer.configure(text=f"{int(dur // 60):02}:{int(dur % 60):02}.{int((dur % 1) * 100):02}")
            self.after(50, self.update_timer_gui)


# ------------------------------------------------------------------
# CONFIG TAB
# ------------------------------------------------------------------
class TrackerConfigurator(ctk.CTkFrame):
    def __init__(self, parent, main_app_ref):
        super().__init__(parent)
        self.app, self.overlay, self.config_data = main_app_ref, None, TrackerConfig.load()
        self.create_widgets()

    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        info = ctk.CTkFrame(self, fg_color="transparent");
        info.pack(fill="x", padx=20, pady=20)
        ctk.CTkLabel(info, text="ULTIMATE TRACKER & GUARDIAN", font=("Roboto", 20, "bold"), text_color="#FFD700").pack(
            anchor="w")
        conf = ctk.CTkFrame(self, border_width=1, border_color="#333");
        conf.pack(fill="x", padx=20, pady=10)
        p = ctk.CTkFrame(conf, fg_color="transparent");
        p.pack(fill="x", padx=15, pady=10)
        for i, (l, k) in enumerate([("HP Trank:", "hp"), ("Mana Trank:", "mana"), ("Merc Trank:", "merc")]):
            ctk.CTkLabel(p, text=l).grid(row=i, column=0, padx=5, pady=2, sticky="w")
            v = ctk.StringVar(value=self.config_data.get(f"{k}_key", "Aus"))
            ctk.CTkOptionMenu(p, values=["Aus", "1", "2", "3", "4"], variable=v,
                              command=lambda x, k=k: self.save_conf(f"{k}_key", x), width=70).grid(row=i, column=1)
            e = ctk.CTkEntry(p, width=50);
            e.insert(0, self.config_data.get(f"{k}_delay", "0.8"));
            e.grid(row=i, column=2, padx=10)
            e.bind("<KeyRelease>", lambda e, k=k, ent=e: self.save_conf(f"{k}_delay", ent.get()))
            cb = ctk.BooleanVar(value=self.config_data.get(f"{k}_sound", True))
            ctk.CTkCheckBox(p, text="🔔", variable=cb, width=20,
                            command=lambda k=k, var=cb: self.save_conf(f"{k}_sound", var.get())).grid(row=i, column=3)

        d_frame = ctk.CTkFrame(conf, fg_color="transparent");
        d_frame.pack(fill="x", padx=20, pady=5)
        self.drop_var = ctk.BooleanVar(value=self.config_data.get("drop_alert_active", False))
        ctk.CTkCheckBox(d_frame, text="🔸 High Rune Alarm", variable=self.drop_var, command=self.save_drop,
                        text_color="#FFD700").pack(side="left")
        self.xp_var = ctk.BooleanVar(value=self.config_data.get("xp_active", False))
        ctk.CTkCheckBox(d_frame, text="📈 XP Tracker", variable=self.xp_var, command=self.save_xp,
                        text_color="#00ccff").pack(side="left", padx=20)

        self.status_lbl = ctk.CTkLabel(conf, text="Status: Prüfe...", font=("Roboto Mono", 11));
        self.status_lbl.pack(padx=15, pady=5)
        ctk.CTkButton(conf, text="⚙️ Wizard (8 Schritte)", command=self.start_wizard, fg_color="#333").pack(padx=15,
                                                                                                            pady=15)
        self.btn_start = ctk.CTkButton(self, text="▶ START OVERLAY", command=self.toggle, height=50,
                                       fg_color="#2da44e");
        self.btn_start.pack(fill="x", padx=20, pady=10)
        self.after(500, self.live_check)

    def save_conf(self, k, v):
        self.config_data[k] = v; TrackerConfig.save(self.config_data)

    def save_drop(self):
        self.config_data["drop_alert_active"] = self.drop_var.get(); TrackerConfig.save(self.config_data)

    def save_xp(self):
        self.config_data["xp_active"] = self.xp_var.get(); TrackerConfig.save(self.config_data)

    def start_wizard(self):
        MultiCalibrationOverlay(self.app, self.on_calib_done)

    def on_calib_done(self, res):
        self.config_data.update(res); TrackerConfig.save(self.config_data)

    def live_check(self):
        if not self.winfo_exists(): return
        req = ["menu_sensor_1", "menu_sensor_2", "game_sensor", "hp_sensor", "mana_sensor", "merc_sensor", "xp_start",
               "xp_end"]
        ok = all(k in self.config_data for k in req)
        self.status_lbl.configure(text="Status: OK ✅" if ok else "Kalibrierung fehlt ❌",
                                  text_color="#2da44e" if ok else "#cf222e")
        self.after(1000, self.live_check)

    def toggle(self):
        if self.overlay:
            self.overlay.stop_tracking(); self.overlay = None; self.btn_start.configure(text="▶ START OVERLAY",
                                                                                        fg_color="#2da44e")
        else:
            self.overlay = RunTrackerOverlay(self.app,
                                             self.config_data); self.overlay.start_tracking(); self.btn_start.configure(
                text="⏹ STOP", fg_color="#cf222e")