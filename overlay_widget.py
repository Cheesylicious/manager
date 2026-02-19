import customtkinter as ctk
from overlay_config import TrackerConfig, STEPS_INFO
from overlay_calibration import CalibrationOverlay
from overlay_tracker import RunTrackerOverlay

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
        if not missing_keys:
            return
        CalibrationOverlay(self.app, missing_keys, self.on_calib_done)

    def calibrate_all(self):
        all_keys = list(STEPS_INFO.keys())
        CalibrationOverlay(self.app, all_keys, self.on_calib_done)

    def save_conf(self, k, v):
        self.config_data[k] = v
        TrackerConfig.save(self.config_data)
        if self.overlay:
            self.overlay.reload_config()

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
            self.overlay = RunTrackerOverlay(self.app, self.config_data, configurator=self)
            self.overlay.start_tracking()
            self.btn_start.configure(text="⏹ STOPP", fg_color="#cf222e")