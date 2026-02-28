import customtkinter as ctk
import tkinter as tk
import threading
import ctypes
import winsound

from overlay_config import STEPS_INFO, TrackerConfig
from tz_fetcher import TZFetcher

# Mixins importieren
from tracker_zone_capture import ZoneCaptureMixin
from tracker_logic_loop import PotionLogicMixin
from tracker_window_state import WindowStateMixin
from tracker_run_manager import RunManagerMixin
from tracker_pending_runes import PendingRunesMixin

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


class RunTrackerOverlay(ctk.CTkToplevel, ZoneCaptureMixin, PotionLogicMixin, WindowStateMixin, RunManagerMixin,
                        PendingRunesMixin):
    def __init__(self, parent, config_data, configurator=None):
        super().__init__(parent)
        self.config_data = config_data
        self.configurator = configurator
        self.parent_app = parent

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

        self.current_run_drops = []
        self.pending_runes = []

        self.bound_hwnd = None

        self.drop_watcher = DropWatcher(config_data, drop_callback=self.on_drop_detected,
                                        ui_parent=self) if DropWatcher else None
        self.xp_watcher = XPWatcher(config_data) if XPWatcher else None
        self.zone_watcher = ZoneWatcher(config_data) if ZoneWatcher else None

        self._build_ui()

        self.run_history, self.is_expanded, self.monitoring, self.in_game, self.paused = [], False, False, False, False
        self.start_time, self.run_count, self.last_alarm_time = 0, 0, 0
        self.last_potions = {"hp": 0, "mana": 0, "merc": 0}
        self.stop_event = threading.Event()
        self.current_state = "UNKNOWN"
        self.last_xp_check = 0
        self.last_ghost_toggle = 0
        self.last_zone_check = ""
        self.blink_state = False

        # Startet den Fetcher für die Terrorzonen
        self.tz_fetcher = TZFetcher(self.stop_event)
        self.tz_fetcher.start(self.update_tz_ui)

        self.after(200, self.apply_stealth_mode)
        self.after(1000, self._blink_loop)

        if self.config_data.get("clickthrough", False):
            self.after(300, lambda: self.set_clickthrough(True))

    def _build_ui(self):
        """Kapselt den gesamten Aufbau der Benutzeroberfläche."""
        self.main_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", border_width=1, border_color="#444444",
                                       corner_radius=8)
        self.main_frame.pack(fill="both", expand=True, padx=2, pady=2)

        self.slider_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent", width=20)
        self.slider_frame.pack(side="right", fill="y", padx=(0, 5), pady=10)
        self.alpha_slider = ctk.CTkSlider(self.slider_frame, from_=0.2, to=1.0, orientation="vertical",
                                          command=self.change_alpha, height=100, width=12)
        self.alpha_slider.set(self.config_data.get("alpha", 1.0))
        self.alpha_slider.pack(pady=5)

        self.content_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.content_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.lbl_status = ctk.CTkLabel(self.content_frame, text="WARTEN...", font=("Roboto", 9, "bold"),
                                       text_color="#888888")
        self.lbl_status.pack(pady=0)

        # ---- ZONE WRAPPER ----
        self.zone_wrapper = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.zone_wrapper.pack(fill="x", pady=(0, 1))

        self.zone_top_frame = ctk.CTkFrame(self.zone_wrapper, fg_color="transparent")
        self.zone_top_frame.pack(anchor="center")

        self.lbl_zone = ctk.CTkLabel(self.zone_top_frame, text="📍 Zone: Unbekannt", font=("Roboto", 11, "bold"),
                                     text_color="#00ccff")
        self.lbl_zone.pack(side="left")

        self.btn_capture_zone = ctk.CTkButton(self.zone_top_frame, text="?", width=20, height=18, fg_color="#444444",
                                              hover_color="#1f538d", font=("Roboto", 10, "bold"),
                                              command=self.open_inline_capture)

        self.manual_zone_entry = ctk.CTkEntry(self.zone_top_frame, width=95, height=18, font=("Roboto", 10),
                                              placeholder_text="Name")
        self.btn_manual_capture = ctk.CTkButton(self.zone_top_frame, text="OK", width=24, height=18, fg_color="#2da44e",
                                                hover_color="#238636", font=("Roboto", 10, "bold"),
                                                command=self.start_manual_capture)

        self.selection_container = ctk.CTkFrame(self.zone_wrapper, fg_color="transparent")
        self.act_btn_frame = ctk.CTkFrame(self.selection_container, fg_color="transparent")

        for act in ["A1", "A2", "A3", "A4", "A5"]:
            btn = ctk.CTkButton(self.act_btn_frame, text=act, width=28, height=20, font=("Roboto", 11, "bold"),
                                fg_color="#1f538d", hover_color="#2da44e",
                                command=lambda a=act: self.show_zone_dropdown(a))
            btn.pack(side="left", padx=1)

        self.dropdown_var = ctk.StringVar(value="Wähle...")
        self.zone_dropdown = ctk.CTkOptionMenu(self.selection_container, variable=self.dropdown_var,
                                               values=["Wähle..."], width=130, height=22, font=("Roboto", 11),
                                               command=self.start_inline_capture_dropdown)

        # --- INNOVATION: Terrorzonen-Block ---
        self.tz_display_frame = ctk.CTkFrame(self.zone_wrapper, fg_color="#111111", corner_radius=6, border_width=1,
                                             border_color="#333333")

        self.lbl_next_tz = ctk.CTkLabel(self.tz_display_frame, text="🔮 TZ: Lade...",
                                        font=("Roboto", 10, "bold"), text_color="#aa88ff")
        self.lbl_next_tz.pack(pady=2, padx=5)

        if self.config_data.get("show_next_tz", True):
            self.tz_display_frame.pack(pady=(2, 1), fill="x", padx=15)

        self.lbl_live_loot = ctk.CTkLabel(self.content_frame, text="", font=("Roboto", 10, "bold"),
                                          text_color="#FFD700")
        self.lbl_live_loot.pack(pady=0)

        self.pending_var = ctk.StringVar(value="📸 Runen nachtragen")
        self.pending_dropdown = ctk.CTkOptionMenu(self.content_frame, variable=self.pending_var, values=[], width=160,
                                                  height=22, font=("Roboto", 11, "bold"), fg_color="#1f538d",
                                                  button_color="#1a4577", command=self.process_selected_pending_rune)

        self.timer_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.timer_container.pack(pady=0)

        self.lbl_timer = ctk.CTkLabel(self.timer_container, text="00:00.00",
                                      font=("Roboto Mono", int(self.current_width * 0.10), "bold"),
                                      text_color="#FFD700", cursor="hand2")
        self.lbl_timer.pack(side="left", padx=(5, 2))
        self.lbl_timer.bind("<Button-1>", self.toggle_history)

        self.btn_toggle_expand = ctk.CTkButton(self.timer_container, text="▼", width=20, height=20,
                                               fg_color="transparent", hover_color="#333333", font=("Arial", 12),
                                               command=self.toggle_history)
        self.btn_toggle_expand.pack(side="left")

        # KOMPAKTER EXP-BLOCK
        self.lbl_xp = ctk.CTkLabel(self.content_frame, text="XP: --% | --%/h | Next: --",
                                   font=("Roboto Mono", 10, "bold"), text_color="#ffd700", cursor="hand2")
        self.lbl_xp.bind("<Button-3>", self.reset_xp_stats)

        if self.config_data.get("xp_active"):
            self.lbl_xp.pack(pady=(0, 2))

        self.stats_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.stats_frame.pack(fill="x", padx=10)
        self.lbl_runs = ctk.CTkLabel(self.stats_frame, text="RUN 0", font=("Roboto", 10, "bold"), text_color="#cccccc")
        self.lbl_runs.pack(side="left")
        self.lbl_last = ctk.CTkLabel(self.stats_frame, text="LAST --:--", font=("Roboto", 10), text_color="#888888")
        self.lbl_last.pack(side="right")

        self.avg_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.avg_frame.pack(fill="x", padx=10)
        self.lbl_avg = ctk.CTkLabel(self.avg_frame, text="Ø --:--", font=("Roboto", 10, "bold"), text_color="#00ccff")
        self.lbl_avg.pack(side="right")

        self.guardian_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.guardian_frame.pack(fill="x", padx=5, pady=(2, 2), side="bottom")

        self.sensors_ui = {}
        sensor_configs = [("hp", "LP", "#FF3333"), ("mana", "MP", "#00ccff"), ("merc", "SÖL", "#2da44e")]

        for key, title, color in sensor_configs:
            f = ctk.CTkFrame(self.guardian_frame, fg_color="#151515", corner_radius=6)
            f.pack(side="left", fill="both", expand=True, padx=1)

            top_f = ctk.CTkFrame(f, fg_color="transparent")
            top_f.pack(fill="x", padx=2, pady=(2, 0))

            indicator = ctk.CTkFrame(top_f, width=8, height=8, corner_radius=4, fg_color="#000000")
            indicator.pack(side="left", padx=(0, 2))

            lbl_title = ctk.CTkLabel(top_f, text=title, font=("Roboto", 9, "bold"), text_color=color)
            lbl_title.pack(side="left")

            btn_sound = ctk.CTkButton(top_f, text="🔊" if self.config_data.get(f"{key}_sound", True) else "🔇", width=16,
                                      height=16, fg_color="transparent", hover_color="#333333", font=("Arial", 8),
                                      command=lambda k=key: self.toggle_individual_sound(k))
            btn_sound.pack(side="right")

            lbl_status = ctk.CTkLabel(f, text="OFF", font=("Roboto Mono", 8, "bold"), text_color="#555555")
            lbl_status.pack(pady=(0, 2))

            self.sensors_ui[key] = {"title": lbl_title, "status": lbl_status, "sound": btn_sound, "color": color,
                                    "indicator": indicator}

        self.expanded_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")

        self.tools_frame = ctk.CTkFrame(self.expanded_frame, fg_color="#111111", corner_radius=6)
        self.tools_frame.pack(fill="x", pady=(0, 5))
        self.tools_frame.grid_columnconfigure(0, weight=1)

        self.ap_var = ctk.BooleanVar(value=self.config_data.get("auto_pickup", False))
        self.cb_autopickup = ctk.CTkSwitch(self.tools_frame, text="Auto-Pickup", variable=self.ap_var,
                                           command=self.toggle_autopickup, font=("Roboto", 12, "bold"),
                                           text_color="#2da44e")
        self.cb_autopickup.grid(row=0, column=0, pady=10, padx=10, sticky="w")

        lbl_learn = ctk.CTkLabel(self.tools_frame, text="Runen Scanner anlernen (Falls noch nicht erkannt):",
                                 font=("Roboto", 11, "bold"), text_color="#aaaaaa")
        lbl_learn.grid(row=1, column=0, pady=(0, 5), padx=10, sticky="w")

        self.btn_learn_text = ctk.CTkButton(self.tools_frame, text="📝 1. Schrift am Boden scannen", height=28,
                                            command=self.open_text_capture, fg_color="#1f538d", hover_color="#1a4577")
        self.btn_learn_text.grid(row=2, column=0, pady=2, padx=10, sticky="ew")

        self.btn_learn_icon = ctk.CTkButton(self.tools_frame, text="🖼️ 2. Icon im Inventar ausschneiden", height=28,
                                            command=self.open_icon_snipping, fg_color="#1f538d", hover_color="#1a4577")
        self.btn_learn_icon.grid(row=3, column=0, pady=(2, 10), padx=10, sticky="ew")

        self.history_frame = ctk.CTkFrame(self.expanded_frame, fg_color="#0d0d0d", corner_radius=6)
        self.history_frame.pack(fill="both", expand=True)

        self.resizer = ctk.CTkLabel(self.main_frame, text="⤡", font=("Arial", 14), text_color="#444", cursor="sizing")
        self.resizer.place(relx=1.0, rely=1.0, anchor="se", x=-2, y=-2)
        self.resizer.bind("<Button-1>", self.resize_start)
        self.resizer.bind("<B1-Motion>", self.resize_move)
        self.resizer.bind("<ButtonRelease-1>", self.resize_end)

        self.context_menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white")
        self.context_menu.add_command(label="🔗 An aktuelles Spiel binden", command=self.bind_to_active_window)
        self.context_menu.add_command(label="⏸️ Pause", command=self.toggle_pause)
        self.context_menu.add_command(label="👻 Ghost-Modus (Strg+Alt+G)", command=lambda: self.set_clickthrough(True))
        self.context_menu.add_command(label="🔄 Run-Timer zurücksetzen", command=self.reset_current_run)
        # NEU: Eintrag im Dropdown-Menü
        self.context_menu.add_command(label="📈 EXP-Statistik zurücksetzen", command=self.reset_xp_stats)
        self.context_menu.add_command(label="🗑️ Alle Daten zurücksetzen", command=self.reset_session)
        self.context_menu.add_command(label="❌ Beenden", command=self.stop_tracking)

        for w in [self.main_frame, self.content_frame, self.lbl_status, self.stats_frame, self.timer_container,
                  self.lbl_timer, self.lbl_xp,
                  self.avg_frame, self.zone_wrapper, self.zone_top_frame, self.lbl_zone, self.lbl_live_loot]:
            w.bind("<Button-1>", self.start_move)
            w.bind("<B1-Motion>", self.do_move)
            w.bind("<Button-3>", self.show_context_menu)
        self.x = self.y = 0

    def update_tz_ui(self, tz_data):
        """Aktualisiert die Terrorzonen-Labels threadsicher (verhindert Engine-Abstürze)."""
        if self.winfo_exists() and hasattr(self, "lbl_next_tz"):
            new_text = f"🔮 TZ: {tz_data.get('next', 'Unbekannt')}"
            self.after(0, lambda: self.lbl_next_tz.configure(text=new_text))

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

        # Ein- und Ausblenden des TZ-Blocks je nach Checkbox in der Config
        if hasattr(self, "tz_display_frame"):
            if self.config_data.get("show_next_tz", True):
                self.tz_display_frame.pack(pady=(2, 1), fill="x", padx=15)
            else:
                self.tz_display_frame.pack_forget()

    def toggle_individual_sound(self, key):
        current = self.config_data.get(f"{key}_sound", True)
        new_val = not current
        self.config_data[f"{key}_sound"] = new_val
        TrackerConfig.save(self.config_data)
        setattr(self, f"{key}_sound", new_val)
        self.sensors_ui[key]["sound"].configure(text="🔊" if new_val else "🔇")

        if self.configurator:
            self.configurator.sync_ui()

    def reset_xp_stats(self, event=None):
        """Wird per Rechtsklick auf die EXP-Anzeige oder über das Menü aufgerufen."""
        if self.xp_watcher:
            self.xp_watcher.reset()
            winsound.Beep(800, 50)
            self.lbl_xp.configure(text="XP: RESET...", text_color="#ffffff")
            self.after(500, lambda: self.lbl_xp.configure(text_color="#ffd700"))
            self._update_xp_display(do_scan=True)

    def _update_xp_display(self, do_scan=True):
        if not self.config_data.get("xp_active") or not self.xp_watcher: return

        if do_scan:
            perc, xph = self.xp_watcher.get_current_xp_percent()
            runs_left = self.xp_watcher.estimate_runs_to_level(self.run_count)
            self.lbl_xp.configure(text=f"XP: {perc}% | {xph}/h | Next: {runs_left}")

    def _blink_loop(self):
        """Lässt 'Unbekannt' rot/blau blinken, wenn keine Zonenaufnahme aktiv ist."""
        if getattr(self, "monitoring", False) and not self.stop_event.is_set():
            if self.last_zone_check == "Unbekannt" and not self.is_capturing_zone and not self.inline_capture_expanded:
                self.blink_state = not self.blink_state
                self.lbl_zone.configure(text_color="#cf222e" if self.blink_state else "#00ccff")
            else:
                self.lbl_zone.configure(text_color="#00ccff")

        self.after(600, self._blink_loop)

    def bind_to_active_window(self):
        """Bindet den Tracker manuell an das Fenster, das gerade im Vordergrund ist."""
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if hwnd:
            self.bound_hwnd = hwnd
            winsound.Beep(1500, 100)
            if hasattr(self, 'lbl_status'):
                self.lbl_status.configure(text="MANUELL GEBUNDEN", text_color="#00ccff")

    def _is_d2r_foreground(self):
        """
        Überschreibt die Mixin-Methode, um sauberes Multiboxing zu ermöglichen.
        Ignoriert fremde D2R-Fenster und schickt den Tracker in den Pause-Modus.
        """
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd: return False

            # 1. Wenn wir gebunden sind, muss es exakt dieses HWND-Fenster sein!
            if getattr(self, "bound_hwnd", None) is not None:
                return hwnd == self.bound_hwnd

            # 2. Wenn noch nicht gebunden, binden wir uns an das erste Diablo-Fenster, das wir sehen
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length == 0: return False
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)

            if "Diablo" in buff.value:
                self.bound_hwnd = hwnd  # BINDING SETZEN!
                return True
            return False
        except:
            return False