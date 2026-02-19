import customtkinter as ctk
import tkinter as tk
import time
import threading
import os
import json
import math
import winsound
import ctypes
from PIL import ImageGrab

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

TRACKER_CONFIG_FILE = "overlay_config.json"

STEPS_INFO = {
    "char_sel_1": (
        "Charakter-Menü (Punkt 1)",
        "Gehe ins Spiel-Hauptmenü, wo dein Charakter am Lagerfeuer steht.\n\nNICHT KLICKEN! Bewege einfach nur den Mauszeiger ganz unten exakt in die Mitte des Buttons 'Spielen' und warte, bis der Countdown abläuft.",
        5
    ),
    "char_sel_2": (
        "Charakter-Menü (Punkt 2)",
        "Bleibe im Hauptmenü bei deinem Charakter.\n\nNICHT KLICKEN! Wähle als zweiten Punkt etwas absolut Unbewegliches.\nBewege den Mauszeiger auf den massiven, grauen Zierrahmen ganz links oder ganz rechts am Bildschirmrand und warte.",
        5
    ),
    "lobby_1": (
        "Online-Lobby (Punkt 1)",
        "Gehe in die Online-Lobby (falls du Online spielst).\n\nBewege den Mauszeiger dort unten auf den Button 'Spiel erstellen' und warte auf den Piepton.\n(Spielst du nur Offline? Dann klicke hier im Fenster auf 'Überspringen').",
        5
    ),
    "lobby_2": (
        "Online-Lobby (Punkt 2)",
        "Bleibe in der Online-Lobby.\n\nBewege den Mauszeiger auf einen weiteren festen Punkt, zum Beispiel den äußeren goldenen Rahmen des Chat-Fensters, und warte.",
        5
    ),
    "loading_screen": (
        "Ladebildschirm (KLICK-MODUS!)",
        "Achtung, jetzt musst du WÄHREND des Ladens klicken!\n\nDrücke hier auf Start, wechsle ins Spiel und benutze einen Wegpunkt. WÄHREND der Ladebildschirm zu sehen ist (Bild ist komplett schwarz), KLICKE 2 bis 3 Mal schnell hintereinander irgendwo in das Schwarze!\n\nDu hast ab jetzt 8 Sekunden Zeit dafür. Jeder Klick piept!",
        8
    ),
    "game_static": (
        "Spiel-Umgebung (Feste Steinfigur)",
        "Gehe nun RICHTIG ins Spiel hinein, sodass du herumlaufen kannst.\n\nBewege den Mauszeiger unten links auf die graue, steinerne Engels-Statue (die Figur, die die rote Kugel hält). Wichtig: Keine Kugel, kein Feuer, nur der feste graue Stein! Zeigen, warten, NICHT klicken!",
        5
    ),
    "hp_sensor": (
        "Rote Lebenskugel (HP)",
        "Bewege den Mauszeiger direkt in das ROTE deiner Lebenskugel.\n\nHalte die Maus genau auf die Höhe, bei der automatisch ein Heiltrank getrunken werden soll (z.B. bei ca. 30% Füllstand). Nicht klicken!",
        5
    ),
    "mana_sensor": (
        "Blaue Manakugel (MP)",
        "Bewege den Mauszeiger direkt in das BLAUE deiner Manakugel.\n\nHalte die Maus genau auf die Höhe, bei der automatisch ein Manatrank eingeworfen werden soll. Nur zielen, nicht klicken!",
        5
    ),
    "merc_sensor": (
        "Söldner Lebensbalken (Grün)",
        "Bewege den Mauszeiger oben links auf den GRÜNEN Lebensbalken deines Söldners/Begleiters.\n\nHalte die Maus genau an die Stelle des Balkens, an der er einen Trank bekommen soll.",
        5
    ),
    "xp_start": (
        "Erfahrungsbalken - Start",
        "Wir messen deinen Fortschritt!\n\nBewege den Mauszeiger ganz unten in der Mitte auf den allerersten Pixel (ganz links) deines Erfahrungs-Balkens und warte.",
        5
    ),
    "xp_end": (
        "Erfahrungsbalken - Ende",
        "Fast fertig!\n\nBewege den Mauszeiger nun ganz unten auf das absolute Ende (ganz rechts) deines Erfahrungs-Balkens und warte auf den Piepton.",
        5
    )
}


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
                        "drop_alert_active": False, "xp_active": False,
                        "min_rune": "Pul", "clickthrough": False
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
            "width": 360, "height": 260, "drop_alert_active": False, "xp_active": False,
            "min_rune": "Pul", "clickthrough": False
        }

    @staticmethod
    def save(data):
        try:
            with open(TRACKER_CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except:
            pass


class CalibrationOverlay(ctk.CTkToplevel):
    def __init__(self, parent, keys_to_calibrate, callback):
        super().__init__(parent)
        self.callback = callback
        self.keys = keys_to_calibrate
        self.current_index = 0
        self.results = {}

        self.title("Overlay Einrichtung")
        self.geometry("650x580")
        self.attributes('-topmost', True)

        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - 650) // 2}+{(sh - 580) // 2}")

        self.lbl_step = ctk.CTkLabel(self, text="...", font=("Roboto", 22, "bold"), text_color="#FFD700")
        self.lbl_step.pack(pady=(25, 5))

        self.lbl_title_step = ctk.CTkLabel(self, text="...", font=("Roboto", 18, "bold"), text_color="white")
        self.lbl_title_step.pack(pady=(0, 15))

        self.lbl_desc = ctk.CTkLabel(self, text="...", font=("Roboto", 15), text_color="#dddddd", wraplength=550,
                                     justify="center")
        self.lbl_desc.pack(pady=10, padx=20)

        self.lbl_count = ctk.CTkLabel(self, text="Bist du bereit?", font=("Roboto", 32, "bold"), text_color="#888888")
        self.lbl_count.pack(pady=20)

        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=10)

        self.btn_action = ctk.CTkButton(self.btn_frame, text="Starten", command=self.start_countdown,
                                        fg_color="#1f538d", height=50, font=("Roboto", 14, "bold"))
        self.btn_action.pack(side="left", padx=10)

        self.btn_skip = ctk.CTkButton(self.btn_frame, text="Überspringen ⏭", command=self.skip_step,
                                      fg_color="transparent", border_width=1, text_color="#aaaaaa", height=50)
        self.btn_skip.pack(side="left", padx=10)

        self.setup_step()
        self.after(200, self.apply_stealth_mode)

    def apply_stealth_mode(self):
        try:
            WDA_EXCLUDEFROMCAPTURE = 0x0011
            hwnd = int(self.wm_frame(), 16)
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
        except Exception:
            pass

    def setup_step(self):
        if self.current_index >= len(self.keys):
            self.finish()
            return

        current_key = self.keys[self.current_index]
        name, desc, time_sec = STEPS_INFO[current_key]

        self.lbl_step.configure(text=f"Schritt {self.current_index + 1} von {len(self.keys)}")
        self.lbl_title_step.configure(text=name)
        self.lbl_desc.configure(text=desc)
        self.lbl_count.configure(text="Bist du bereit?", text_color="#888888")
        self.btn_action.configure(state="normal", text=f"Starten ({time_sec} Sek)")
        self.btn_skip.configure(state="normal")

    def skip_step(self):
        self.current_index += 1
        self.setup_step()

    def start_countdown(self):
        self.btn_action.configure(state="disabled")
        self.btn_skip.configure(state="disabled")
        current_key = self.keys[self.current_index]
        time_sec = STEPS_INFO[current_key][2]

        if current_key == "loading_screen":
            threading.Thread(target=self._click_record_logic, args=(time_sec, current_key), daemon=True).start()
        else:
            threading.Thread(target=self._count_logic, args=(time_sec, current_key), daemon=True).start()

    def _click_record_logic(self, seconds, key):
        time.sleep(0.5)
        end_time = time.time() + seconds
        clicks = []
        was_pressed = False

        while time.time() < end_time:
            remaining = int(end_time - time.time())
            self.lbl_count.configure(text=f"Klick-Modus aktiv! ({remaining}s)\nKLICKE JETZT!", text_color="#FF9500")

            if ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000:
                if not was_pressed:
                    try:
                        x, y = self.winfo_pointerxy()
                        img = ImageGrab.grab(bbox=(x, y, x + 1, y + 1))
                        c = img.getpixel((0, 0))
                        clicks.append({"x": x, "y": y, "r": c[0], "g": c[1], "b": c[2]})
                        winsound.Beep(2000, 50)
                    except:
                        pass
                    was_pressed = True
            else:
                was_pressed = False

            time.sleep(0.01)

        if clicks:
            self.results[key] = clicks
            winsound.Beep(1000, 300)

        self.current_index += 1
        self.after(500, self.setup_step)

    def _count_logic(self, seconds, key):
        for i in range(seconds, 0, -1):
            color = "#FF3333" if i <= 3 else "#00ccff"
            self.lbl_count.configure(text=str(i), text_color=color)
            time.sleep(1)

        try:
            x, y = self.winfo_pointerxy()
            img = ImageGrab.grab(bbox=(x, y, x + 1, y + 1))
            c = img.getpixel((0, 0))
            winsound.Beep(1500, 100)

            self.results[key] = {"x": x, "y": y, "r": c[0], "g": c[1], "b": c[2]}

            self.current_index += 1
            self.after(500, self.setup_step)
        except Exception as e:
            print(f"Fehler beim Grabben: {e}")
            self.current_index += 1
            self.after(500, self.setup_step)

    def finish(self):
        self.callback(self.results)
        self.destroy()


class RunTrackerOverlay(ctk.CTkToplevel):
    def __init__(self, parent, config_data):
        super().__init__(parent)
        self.config_data = config_data

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

        self.drop_watcher = DropWatcher(config_data) if DropWatcher else None
        self.xp_watcher = XPWatcher(config_data) if XPWatcher else None

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

        self.guardian_frame = ctk.CTkFrame(self.content_frame, fg_color="#111111", corner_radius=4, height=30)
        self.guardian_frame.pack(fill="x", padx=5, pady=(2, 5), side="bottom")
        self.lbl_hp = ctk.CTkLabel(self.guardian_frame, text=self.fmt_status("LP", False),
                                   font=("Roboto Mono", 9, "bold"), text_color="#2da44e")
        self.lbl_hp.pack(side="left", padx=5)
        self.lbl_mp = ctk.CTkLabel(self.guardian_frame, text=self.fmt_status("MP", False),
                                   font=("Roboto Mono", 9, "bold"), text_color="#00ccff")
        self.lbl_mp.pack(side="left", padx=2)
        self.lbl_mc = ctk.CTkLabel(self.guardian_frame, text=self.fmt_status("SÖLD", False),
                                   font=("Roboto Mono", 9, "bold"), text_color="#aaaaaa")
        self.lbl_mc.pack(side="left", padx=2)
        self.btn_mute = ctk.CTkButton(self.guardian_frame, text="🔊", width=25, height=18, fg_color="transparent",
                                      command=self.toggle_mute)
        self.btn_mute.pack(side="right", padx=2)

        self.history_frame = ctk.CTkFrame(self.content_frame, fg_color="#0d0d0d", corner_radius=6)

        self.resizer = ctk.CTkLabel(self.main_frame, text="⤡", font=("Arial", 14), text_color="#444", cursor="sizing")
        self.resizer.place(relx=1.0, rely=1.0, anchor="se", x=-2, y=-2)
        self.resizer.bind("<Button-1>", self.resize_start)
        self.resizer.bind("<B1-Motion>", self.resize_move)
        self.resizer.bind("<ButtonRelease-1>", self.resize_end)

        self.run_history, self.is_expanded, self.monitoring, self.in_game, self.paused = [], False, False, False, False
        self.start_time, self.run_count, self.alarm_active, self.last_alarm_time = 0, 0, True, 0
        self.last_potions = {"hp": 0, "mana": 0, "merc": 0}
        self.stop_event = threading.Event()
        self.current_state = "UNKNOWN"
        self.last_xp_check = 0
        self.last_ghost_toggle = 0

        self.context_menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white")
        self.context_menu.add_command(label="⏸️ Pause", command=self.toggle_pause)
        self.context_menu.add_command(label="👻 Ghost-Modus (EIN/AUS per Strg+Alt+G)",
                                      command=lambda: self.set_clickthrough(True))
        self.context_menu.add_command(label="🔄 Run-Timer zurücksetzen", command=self.reset_current_run)
        self.context_menu.add_command(label="🗑️ Alle Daten zurücksetzen", command=self.reset_session)
        self.context_menu.add_command(label="❌ Beenden", command=self.stop_tracking)

        for w in [self.main_frame, self.content_frame, self.lbl_status, self.stats_frame, self.lbl_timer, self.lbl_xp,
                  self.avg_frame]:
            w.bind("<Button-1>", self.start_move)
            w.bind("<B1-Motion>", self.do_move)
            w.bind("<Button-3>", self.show_context_menu)
        self.lbl_timer.bind("<Button-1>", self.toggle_history)
        self.x = self.y = 0

        self.after(200, self.apply_stealth_mode)

        if self.config_data.get("clickthrough", False):
            self.after(300, lambda: self.set_clickthrough(True))

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

    def fmt_status(self, t, active):
        dot = "●" if active else "○"
        keys = {"LP": self.hp_key, "MP": self.mana_key, "SÖLD": self.merc_key}
        k = keys[t] if keys[t] != "Aus" else "-"
        return f"{t[0]}{dot}:{k}"

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

    def toggle_mute(self):
        self.alarm_active = not self.alarm_active
        self.btn_mute.configure(text="🔊" if self.alarm_active else "🔇")

    def reset_current_run(self):
        self.start_time = 0
        self.in_game = False
        self.lbl_timer.configure(text="00:00.00")

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
            self.geometry(f"{self.current_width}x{self.current_height + 220}")
            self.history_frame.pack(fill="both", expand=True, padx=5, pady=(0, 10), before=self.guardian_frame)
            self.update_history_list()
        else:
            self.geometry(f"{self.current_width}x{self.current_height}")
            self.history_frame.pack_forget()

    def update_history_list(self):
        for w in self.history_frame.winfo_children(): w.destroy()
        recent = self.run_history[-10:]
        recent.reverse()
        for i, dur in enumerate(recent):
            row = ctk.CTkFrame(self.history_frame, fg_color="transparent")
            row.pack(fill="x", padx=5)
            ctk.CTkLabel(row, text=f"{len(self.run_history) - i}.", font=("Roboto Mono", 9)).pack(side="left")
            ctk.CTkLabel(row, text=f"{int(dur // 60):02}:{int(dur % 60):02}", font=("Roboto Mono", 9)).pack(
                side="right")

    def start_tracking(self):
        self.monitoring = True
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
        self.run_history.append(dur)
        self.run_count += 1
        self.lbl_runs.configure(text=f"Runs: {self.run_count}")
        self.lbl_last.configure(text=f"Letzter: {int(dur // 60):02}:{int(dur % 60):02}")
        avg = sum(self.run_history) / self.run_count
        self.lbl_avg.configure(text=f"Ø {int(avg // 60):02}:{int(avg % 60):02}")

        self._update_xp_display(do_scan=False)

        if self.is_expanded: self.update_history_list()
        self.start_time = 0

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

        match1 = self._check_color(cfg1) if cfg1 else True
        match2 = self._check_color(cfg2) if cfg2 else True
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

                        # OPTIMIERT: Scannt den Bildschirm jetzt alle 2 Sekunden für sofortiges Feedback
                        if now - self.last_xp_check > 2.0:
                            self.last_xp_check = now
                            self._update_xp_display(do_scan=True)

                        hp = self._check_color(self.sensors["hp_sensor"], "hp")
                        mp = self._check_color(self.sensors["mana_sensor"], "mana")
                        mc = self._check_color(self.sensors["merc_sensor"], "merc")

                        if not hp and now - self.last_potions["hp"] > self.hp_delay:
                            self._press_key(self.hp_key)
                            self.last_potions["hp"] = now
                            if self.alarm_active and self.hp_sound and now - self.last_alarm_time > 2:
                                winsound.Beep(1200, 150)
                                self.last_alarm_time = now
                        if not mp and now - self.last_potions["mana"] > self.mana_delay:
                            self._press_key(self.mana_key)
                            self.last_potions["mana"] = now
                            if self.alarm_active and self.mana_sound and now - self.last_alarm_time > 2:
                                winsound.Beep(800, 100)
                                self.last_alarm_time = now
                        if not mc and now - self.last_potions["merc"] > self.merc_delay:
                            self._press_key(self.merc_key, True)
                            self.last_potions["merc"] = now
                            if self.alarm_active and self.merc_sound and now - self.last_alarm_time > 2:
                                winsound.Beep(1000, 150)
                                self.last_alarm_time = now

                        self.lbl_hp.configure(text=self.fmt_status("LP", hp), text_color="#2da44e" if hp else "#FF3333")
                        self.lbl_mp.configure(text=self.fmt_status("MP", mp), text_color="#00ccff" if mp else "#FF9900")
                        self.lbl_mc.configure(text=self.fmt_status("SÖLD", mc),
                                              text_color="#aaaaaa" if mc else "#8B0000")
                    else:
                        self.lbl_status.configure(text="TABBED OUT (Auto-Pot PAUSE)", text_color="#FF9500")

                elif self.current_state == "MENU":
                    self.lbl_status.configure(text="MENÜ / LOBBY", text_color="#cf222e")

                time.sleep(0.1)
            except Exception as e:
                time.sleep(1)

    def _check_color(self, cfg, mode="match"):
        if not cfg: return False

        if isinstance(cfg, list):
            if len(cfg) == 0: return False
            matches = 0
            for point in cfg:
                if self._check_single_pixel(point, mode):
                    matches += 1
            return matches > 0 and matches >= (len(cfg) / 2)

        return self._check_single_pixel(cfg, mode)

    def _check_single_pixel(self, point, mode):
        try:
            image = ImageGrab.grab(bbox=(point["x"], point["y"], point["x"] + 1, point["y"] + 1))
            c = image.getpixel((0, 0))

            if mode == "match":
                return math.sqrt((c[0] - point["r"]) ** 2 + (c[1] - point["g"]) ** 2 + (c[2] - point["b"]) ** 2) < 35
            if mode == "hp":
                return c[0] > (point["r"] * 0.4)
            if mode == "mana":
                return c[2] > (point["b"] * 0.4)
            if mode == "merc":
                return c[1] > (point["g"] * 0.4) and c[1] > c[0]
            return False
        except:
            return False

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


class TrackerConfigurator(ctk.CTkScrollableFrame):
    def __init__(self, parent, main_app_ref):
        super().__init__(parent, fg_color="transparent")
        self.app = main_app_ref
        self.overlay = None
        self.config_data = TrackerConfig.load()

        self.rune_names = [
            "El", "Eld", "Tir", "Nef", "Eth", "Ith", "Tal", "Ral", "Ort", "Thul", "Amn", "Sol", "Shael", "Dol", "Hel",
            "Io", "Lum", "Ko", "Fal", "Lem", "Pul", "Um", "Mal", "Ist", "Gul", "Vex", "Ohm", "Lo", "Sur", "Ber",
            "Jah", "Cham", "Zod"
        ]

        self.status_labels = {}
        self.create_widgets()

    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)

        info = ctk.CTkFrame(self, fg_color="transparent")
        info.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(info, text="OVERLAY & TRACKER STEUERUNG", font=("Roboto", 22, "bold"), text_color="#FFD700").pack(
            anchor="w")

        self.btn_start = ctk.CTkButton(self, text="▶ OVERLAY STARTEN", command=self.toggle, height=55,
                                       font=("Roboto", 16, "bold"), fg_color="#2da44e")
        self.btn_start.pack(fill="x", padx=10, pady=5)

        settings_frame = ctk.CTkFrame(self, border_width=1, border_color="#333")
        settings_frame.pack(fill="x", padx=10, pady=15)

        ctk.CTkLabel(settings_frame, text="Tränke & Automation", font=("Roboto", 14, "bold")).pack(anchor="w", padx=15,
                                                                                                   pady=(10, 5))

        p = ctk.CTkFrame(settings_frame, fg_color="transparent")
        p.pack(fill="x", padx=15, pady=5)
        for i, (l, k) in enumerate(
                [("Lebenspunkte (Rot):", "hp"), ("Manapunkte (Blau):", "mana"), ("Söldner / Begleiter:", "merc")]):
            ctk.CTkLabel(p, text=l).grid(row=i, column=0, padx=5, pady=2, sticky="w")
            v = ctk.StringVar(value=self.config_data.get(f"{k}_key", "Aus"))
            ctk.CTkOptionMenu(p, values=["Aus", "1", "2", "3", "4"], variable=v,
                              command=lambda x, k=k: self.save_conf(f"{k}_key", x), width=70).grid(row=i, column=1)
            e = ctk.CTkEntry(p, width=50)
            e.insert(0, self.config_data.get(f"{k}_delay", "0.8"))
            e.grid(row=i, column=2, padx=10)
            e.bind("<KeyRelease>", lambda e, k=k, ent=e: self.save_conf(f"{k}_delay", ent.get()))
            cb = ctk.BooleanVar(value=self.config_data.get(f"{k}_sound", True))
            ctk.CTkCheckBox(p, text="🔔 Sound", variable=cb, width=20,
                            command=lambda k=k, var=cb: self.save_conf(f"{k}_sound", var.get())).grid(row=i, column=3)

        d_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        d_frame.pack(fill="x", padx=15, pady=10)

        self.drop_var = ctk.BooleanVar(value=self.config_data.get("drop_alert_active", False))
        ctk.CTkCheckBox(d_frame, text="🔸 High Rune Alarm:", variable=self.drop_var, command=self.save_drop,
                        text_color="#FFD700").pack(side="left", padx=(0, 5))

        current_rune = self.config_data.get("min_rune", "Pul")
        self.rune_combo = ctk.CTkOptionMenu(d_frame, values=self.rune_names, width=70, command=self.save_rune_choice)
        self.rune_combo.set(current_rune)
        self.rune_combo.pack(side="left")

        self.xp_var = ctk.BooleanVar(value=self.config_data.get("xp_active", False))
        ctk.CTkCheckBox(d_frame, text="📈 EXP-Tracker einblenden", variable=self.xp_var, command=self.save_xp,
                        text_color="#00ccff").pack(side="left", padx=20)

        self.ghost_var = ctk.BooleanVar(value=self.config_data.get("clickthrough", False))
        cb_ghost = ctk.CTkCheckBox(d_frame, text="👻 Overlay durchklickbar (Ghost-Modus)", variable=self.ghost_var,
                                   command=self.save_ghost, text_color="#aaaaaa")
        cb_ghost.pack(side="left", padx=20)

        calib_frame = ctk.CTkFrame(self, border_width=1, border_color="#333")
        calib_frame.pack(fill="x", padx=10, pady=10)

        c_header = ctk.CTkFrame(calib_frame, fg_color="transparent")
        c_header.pack(fill="x", padx=15, pady=10)

        self.is_calib_expanded = False
        self.btn_toggle_calib = ctk.CTkButton(c_header, text="▶ Sensor Kalibrierung (Status)",
                                              command=self.toggle_calib_list, fg_color="transparent",
                                              text_color="#FFD700", font=("Roboto", 14, "bold"), hover_color="#333333",
                                              anchor="w")
        self.btn_toggle_calib.pack(side="left")

        btn_all = ctk.CTkButton(c_header, text="Alle neu kalibrieren", command=self.calibrate_all, fg_color="#8B0000",
                                hover_color="#5A0000", width=140)
        btn_all.pack(side="right", padx=5)

        btn_missing = ctk.CTkButton(c_header, text="Nur Fehlende kalibrieren", command=self.calibrate_missing,
                                    fg_color="#1f538d", width=160)
        btn_missing.pack(side="right", padx=5)

        self.list_container = ctk.CTkFrame(calib_frame, fg_color="transparent")

        for key, (name, _, _) in STEPS_INFO.items():
            row = ctk.CTkFrame(self.list_container, fg_color="#1a1a1a", corner_radius=4)
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(row, text=name, font=("Roboto", 12)).pack(side="left", padx=10, pady=4)

            lbl_status = ctk.CTkLabel(row, text="?", font=("Roboto", 12, "bold"))
            lbl_status.pack(side="left", padx=20)
            self.status_labels[key] = lbl_status

            btn_single = ctk.CTkButton(row, text="Einzeln Kalibrieren", width=120, height=24, fg_color="#333",
                                       command=lambda k=key: self.calibrate_single(k))
            btn_single.pack(side="right", padx=10, pady=4)

        self.after(500, self.update_status_list)

    def toggle_calib_list(self):
        self.is_calib_expanded = not self.is_calib_expanded
        if self.is_calib_expanded:
            self.btn_toggle_calib.configure(text="▼ Sensor Kalibrierung (Status)")
            self.list_container.pack(fill="x", padx=15, pady=5)
        else:
            self.btn_toggle_calib.configure(text="▶ Sensor Kalibrierung (Status)")
            self.list_container.pack_forget()

    def update_status_list(self):
        if not self.winfo_exists(): return

        for key, lbl in self.status_labels.items():
            if key in self.config_data and self.config_data[key]:
                lbl.configure(text="✅ Gespeichert", text_color="#2da44e")
            else:
                lbl.configure(text="❌ Fehlt", text_color="#cf222e")

        self.after(1000, self.update_status_list)

    def calibrate_single(self, key):
        CalibrationOverlay(self.app, [key], self.on_calib_done)

    def calibrate_missing(self):
        missing_keys = [k for k in STEPS_INFO.keys() if k not in self.config_data or not self.config_data[k]]
        if not missing_keys:
            return
        CalibrationOverlay(self.app, missing_keys, self.on_calib_done)

    def calibrate_all(self):
        all_keys = list(STEPS_INFO.keys())
        CalibrationOverlay(self.app, all_keys, self.on_calib_done)

    def save_conf(self, k, v):
        self.config_data[k] = v
        TrackerConfig.save(self.config_data)

    def save_drop(self):
        self.config_data["drop_alert_active"] = self.drop_var.get()
        TrackerConfig.save(self.config_data)

    def save_rune_choice(self, choice):
        self.config_data["min_rune"] = choice
        TrackerConfig.save(self.config_data)

    def save_xp(self):
        self.config_data["xp_active"] = self.xp_var.get()
        TrackerConfig.save(self.config_data)
        if self.overlay:
            if self.xp_var.get():
                self.overlay.lbl_xp.pack()
                self.overlay._update_xp_display(do_scan=False)
            else:
                self.overlay.lbl_xp.pack_forget()

    def save_ghost(self):
        self.config_data["clickthrough"] = self.ghost_var.get()
        TrackerConfig.save(self.config_data)
        if self.overlay:
            self.overlay.set_clickthrough(self.ghost_var.get())

    def on_calib_done(self, res):
        self.config_data.update(res)
        TrackerConfig.save(self.config_data)

    def toggle(self):
        if self.overlay:
            self.overlay.stop_tracking()
            self.overlay = None
            self.btn_start.configure(text="▶ OVERLAY STARTEN", fg_color="#2da44e")
        else:
            self.overlay = RunTrackerOverlay(self.app, self.config_data)
            self.overlay.start_tracking()
            self.btn_start.configure(text="⏹ STOPP", fg_color="#cf222e")