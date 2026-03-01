import customtkinter as ctk
from overlay_config import TrackerConfig, STEPS_INFO
from overlay_calibration import CalibrationOverlay
from overlay_tracker import RunTrackerOverlay
from rune_filter_ui import RuneFilterWindow
from rune_capture_ui import RuneCaptureWindow
from zone_capture_ui import ZoneCaptureWindow

# --- NEUE MODULE ---
from database_manager import ItemDatabaseManager
from ui_loot_filter import LootFilterWindow


class TrackerConfigurator(ctk.CTkScrollableFrame):
    def __init__(self, parent, main_app_ref):
        super().__init__(parent, fg_color="transparent")
        self.app = main_app_ref
        self.overlay = None
        self.config_data = TrackerConfig.load()

        # Initialisiere die Datenbank für angelernte Items
        self.db_manager = ItemDatabaseManager()

        self.status_labels = {}
        self.sound_vars = {}
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
            e.bind("<KeyRelease>", lambda e, k=k, ent=e: self.save_conf(f"{k}_delay", ent.get()))
            e.grid(row=i, column=2, padx=10)

            cb = ctk.BooleanVar(value=self.config_data.get(f"{k}_sound", True))
            self.sound_vars[k] = cb
            ctk.CTkCheckBox(p, text="🔔 Sound", variable=cb, width=20,
                            command=lambda k=k, var=cb: self.save_conf(f"{k}_sound", var.get())).grid(row=i, column=3)

        # REIHE 1: ALARM & FILTER & SCANNER
        d_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        d_frame.pack(fill="x", padx=15, pady=(15, 5))

        self.drop_var = ctk.BooleanVar(value=self.config_data.get("drop_alert_active", False))
        ctk.CTkCheckBox(d_frame, text="🔸 Runen Alarm:", variable=self.drop_var, command=self.save_drop,
                        text_color="#FFD700").pack(side="left", padx=(0, 5))

        self.btn_rune_filter = ctk.CTkButton(d_frame, text="⚙️ Filter einstellen", width=120,
                                             command=self.open_rune_filter, fg_color="#444444")
        self.btn_rune_filter.pack(side="left", padx=(5, 5))

        self.btn_rune_capture = ctk.CTkButton(d_frame, text="📸 Rune aufnehmen", width=120,
                                              command=self.open_rune_capture, fg_color="#1f538d")
        self.btn_rune_capture.pack(side="left", padx=(5, 5))

        self.btn_loot_filter = ctk.CTkButton(d_frame, text="🎒 Eigener Loot", width=120, command=self.open_loot_filter,
                                             fg_color="#556b2f")
        self.btn_loot_filter.pack(side="left", padx=(5, 5))

        self.btn_popup_manager = ctk.CTkButton(d_frame, text="🔕 Pop-ups verwalten", width=140, command=self.open_popup_manager, fg_color="#8B008B")
        self.btn_popup_manager.pack(side="left", padx=(5, 10))

        # REIHE 2: PICKUP, DELAY & NEUER TELEPORT
        p_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        p_frame.pack(fill="x", padx=15, pady=5)

        self.pickup_var = ctk.BooleanVar(value=self.config_data.get("auto_pickup", False))
        ctk.CTkCheckBox(p_frame, text="🖐 Auto-Pickup", variable=self.pickup_var, command=self.save_pickup,
                        text_color="#ff7f50").pack(side="left", padx=(0, 5))

        delay_frame = ctk.CTkFrame(p_frame, fg_color="transparent")
        delay_frame.pack(side="left", padx=(5, 15))
        ctk.CTkLabel(delay_frame, text="Verzögerung (ms):", font=("Roboto", 11)).pack(side="left", padx=(0, 5))

        self.pickup_min_entry = ctk.CTkEntry(delay_frame, width=40, height=24)
        self.pickup_min_entry.insert(0, str(self.config_data.get("pickup_delay_min", 150)))
        self.pickup_min_entry.bind("<KeyRelease>", lambda e: self.save_pickup_delay())
        self.pickup_min_entry.pack(side="left")

        ctk.CTkLabel(delay_frame, text="-", font=("Roboto", 11)).pack(side="left", padx=2)

        self.pickup_max_entry = ctk.CTkEntry(delay_frame, width=40, height=24)
        self.pickup_max_entry.insert(0, str(self.config_data.get("pickup_delay_max", 350)))
        self.pickup_max_entry.bind("<KeyRelease>", lambda e: self.save_pickup_delay())
        self.pickup_max_entry.pack(side="left")

        # NEU: Teleport-Pickup Toggle und Keybind
        self.tp_pickup_var = ctk.BooleanVar(value=self.config_data.get("teleport_pickup", False))
        ctk.CTkCheckBox(p_frame, text="⚡ TP-Pickup", variable=self.tp_pickup_var, command=self.save_tp_pickup,
                        text_color="#00ccff").pack(side="left", padx=(5, 5))

        self.tp_key_var = ctk.StringVar(value=self.config_data.get("teleport_key", "Aus"))
        tp_keys = ["Aus", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "Q", "W", "E", "R", "T", "A", "S", "D", "F", "Z", "X", "C", "V", "1", "2", "3", "4"]
        ctk.CTkOptionMenu(p_frame, values=tp_keys, variable=self.tp_key_var,
                          command=self.save_tp_key, width=65, height=24).pack(side="left", padx=(0, 5))

        # REIHE 3: ZONEN & EXP & GHOST
        e_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        e_frame.pack(fill="x", padx=15, pady=5)

        self.xp_var = ctk.BooleanVar(value=self.config_data.get("xp_active", False))
        ctk.CTkCheckBox(e_frame, text="📈 EXP-Tracker", variable=self.xp_var, command=self.save_xp,
                        text_color="#00ccff").pack(side="left", padx=(0, 5))

        self.btn_zone_capture = ctk.CTkButton(e_frame, text="🗺️ Zone aufnehmen", width=120,
                                              command=self.open_zone_capture, fg_color="#008080")
        self.btn_zone_capture.pack(side="left", padx=(10, 20))

        self.ghost_var = ctk.BooleanVar(value=self.config_data.get("clickthrough", False))
        cb_ghost = ctk.CTkCheckBox(e_frame, text="👻 Ghost-Modus", variable=self.ghost_var,
                                   command=self.save_ghost, text_color="#aaaaaa")
        cb_ghost.pack(side="left", padx=5)

        # REIHE 4: TERROR ZONEN
        tz_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        tz_frame.pack(fill="x", padx=15, pady=(5, 15))

        self.tz_var = ctk.BooleanVar(value=self.config_data.get("show_next_tz", True))
        ctk.CTkCheckBox(tz_frame, text="🔮 Nächste Terrorzone (D2Emu) anzeigen", variable=self.tz_var,
                        command=self.save_tz,
                        text_color="#aa88ff").pack(side="left", padx=(0, 5))

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

    def open_rune_filter(self):
        RuneFilterWindow(self.app, self.config_data, self.on_runes_updated)

    def open_rune_capture(self):
        RuneCaptureWindow(self.app, self.on_runes_updated)

    def open_zone_capture(self):
        ZoneCaptureWindow(self.app, self.on_zone_updated)

    def open_loot_filter(self):
        LootFilterWindow(self.app, self.db_manager, self.on_loot_updated)

    def on_loot_updated(self):
        pass

    def open_popup_manager(self):
        from ui_popup_manager import PopupManagerWindow
        PopupManagerWindow(self.app, self.config_data, self.on_popup_updated)

    def on_popup_updated(self, updated_config):
        self.config_data = updated_config
        TrackerConfig.save(self.config_data)
        if self.overlay:
            self.overlay.reload_config()

    def on_runes_updated(self):
        TrackerConfig.save(self.config_data)
        if self.overlay and hasattr(self.overlay, 'drop_watcher') and self.overlay.drop_watcher:
            self.overlay.drop_watcher.config = self.config_data
            self.overlay.drop_watcher._load_templates()

    def on_zone_updated(self):
        if self.overlay and hasattr(self.overlay, 'zone_watcher') and self.overlay.zone_watcher:
            self.overlay.zone_watcher._load_templates()

    def sync_ui(self):
        for key, var in self.sound_vars.items():
            var.set(self.config_data.get(f"{key}_sound", True))

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
        if not missing_keys: return
        CalibrationOverlay(self.app, missing_keys, self.on_calib_done)

    def calibrate_all(self):
        all_keys = list(STEPS_INFO.keys())
        CalibrationOverlay(self.app, all_keys, self.on_calib_done)

    def save_conf(self, k, v):
        self.config_data[k] = v
        TrackerConfig.save(self.config_data)
        if self.overlay: self.overlay.reload_config()

    def save_drop(self):
        is_active = self.drop_var.get()
        self.config_data["drop_alert_active"] = is_active
        if not is_active and self.pickup_var.get():
            self.pickup_var.set(False)
            self.config_data["auto_pickup"] = False
        TrackerConfig.save(self.config_data)
        if self.overlay and hasattr(self.overlay, 'drop_watcher') and self.overlay.drop_watcher:
            self.overlay.drop_watcher.config = self.config_data
            self.overlay.drop_watcher.update_config(is_active)

    def save_pickup(self):
        is_active = self.pickup_var.get()
        self.config_data["auto_pickup"] = is_active
        if is_active and not self.drop_var.get():
            self.drop_var.set(True)
            self.config_data["drop_alert_active"] = True
        TrackerConfig.save(self.config_data)
        if self.overlay and hasattr(self.overlay, 'drop_watcher') and self.overlay.drop_watcher:
            self.overlay.drop_watcher.config = self.config_data
            if is_active: self.overlay.drop_watcher.update_config(True)

    # NEU: Speichern des TP Checkbox Status
    def save_tp_pickup(self):
        self.config_data["teleport_pickup"] = self.tp_pickup_var.get()
        TrackerConfig.save(self.config_data)
        if self.overlay and hasattr(self.overlay, 'drop_watcher') and self.overlay.drop_watcher:
            self.overlay.drop_watcher.config = self.config_data

    # NEU: Speichern der TP Taste
    def save_tp_key(self, choice):
        self.config_data["teleport_key"] = choice
        TrackerConfig.save(self.config_data)
        if self.overlay and hasattr(self.overlay, 'drop_watcher') and self.overlay.drop_watcher:
            self.overlay.drop_watcher.config = self.config_data

    def save_pickup_delay(self):
        try:
            min_val = int(self.pickup_min_entry.get())
            max_val = int(self.pickup_max_entry.get())
            self.config_data["pickup_delay_min"] = min_val
            self.config_data["pickup_delay_max"] = max_val
            TrackerConfig.save(self.config_data)
            if self.overlay and hasattr(self.overlay, 'drop_watcher') and self.overlay.drop_watcher:
                self.overlay.drop_watcher.config = self.config_data
        except ValueError:
            pass

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
        if self.overlay: self.overlay.set_clickthrough(self.ghost_var.get())

    def save_tz(self):
        self.config_data["show_next_tz"] = self.tz_var.get()
        TrackerConfig.save(self.config_data)
        if self.overlay and hasattr(self.overlay, "lbl_next_tz"):
            if self.tz_var.get():
                self.overlay.lbl_next_tz.pack(pady=(2, 2))
            else:
                self.overlay.lbl_next_tz.pack_forget()

    def on_calib_done(self, res):
        self.config_data.update(res)
        TrackerConfig.save(self.config_data)

    def toggle(self):
        if self.overlay:
            self.overlay.stop_tracking()
            self.overlay = None
            self.btn_start.configure(text="▶ OVERLAY STARTEN", fg_color="#2da44e")
        else:
            self.overlay = RunTrackerOverlay(self.app, self.config_data, configurator=self)
            self.overlay.start_tracking()
            self.btn_start.configure(text="⏹ STOPP", fg_color="#cf222e")