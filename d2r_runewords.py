import customtkinter as ctk
from tkinter import ttk


class RunewordConfigurator(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.all_runes = [
            "El", "Eld", "Tir", "Nef", "Eth", "Ith", "Tal", "Ral", "Ort", "Thul", "Amn", "Sol", "Shael", "Dol", "Hel",
            "Io",
            "Lum", "Ko", "Fal", "Lem", "Pul", "Um", "Mal", "Ist", "Gul", "Vex", "Ohm", "Lo", "Sur", "Ber", "Jah",
            "Cham", "Zod"
        ]

        # MASSIVE DATENBANK (ALLE relevanten Runenwörter)
        self.runewords = [
            # --- PATCH 3.0 / REIGN OF THE WARLOCK ---
            {"name": "BESESSENHEIT", "eng": "Obsession", "runes": ["Zod", "Ist", "Lem", "Lum", "Io", "Nef"], "lvl": 69,
             "sockets": 6, "type": "Stab", "patch": "3.0",
             "stats": "• 24% Chance Lvl 10 Schwächen bei Treffer\n• +4 All Skills\n• +65% FCR\n• +60% FHR\n• +[15-25]% Leben\n• All Res +[60-70]"},
            {"name": "ZIRKEL", "eng": "Coven", "runes": ["Ist", "Ral", "Io"], "lvl": 63, "sockets": 3, "type": "Helm",
             "patch": "3.0", "stats": "• +1 All Skills\n• +20% FCR\n• 31% MF\n• Feuer-Resi +30%"},
            {"name": "RITUAL", "eng": "Ritual", "runes": ["Amn", "Shael", "Ohm"], "lvl": 57, "sockets": 3,
             "type": "Dolch", "patch": "3.0", "stats": "• 13% Siegel: Tod bei Treffer\n• +40% IAS\n• +304% ED"},
            {"name": "WACHSAMKEIT", "eng": "Vigilance", "runes": ["Dol", "Gul"], "lvl": 53, "sockets": 2,
             "type": "Schild", "patch": "3.0", "stats": "• 5% Feuerring bei Treffer\n• +10% FRW\n• +30% Block-Rate"},
            {"name": "MACHT", "eng": "Power", "runes": ["Hel", "Shae", "Ral"], "lvl": 29, "sockets": 3,
             "type": "Rüstung", "patch": "3.0", "stats": "• +2 Hexenmeister-Skills\n• 10% Miasmakette"},

            # --- PATCH 2.6 / 2.4 ---
            {"name": "MOSAIK", "eng": "Mosaic", "runes": ["Mal", "Gul", "Thul"], "lvl": 53, "sockets": 3,
             "type": "Klaue", "patch": "2.6",
             "stats": "• +2 Kampfkünste (Assa)\n• 50% Finisher-Ladungserhalt\n• +20% AR"},
            {"name": "HETZE", "eng": "Hustle", "runes": ["Shael", "Ko", "Eld"], "lvl": 39, "sockets": 3,
             "type": "Waffe/Rüstung", "patch": "2.6",
             "stats": "• Waffe: 5% Temposchub, +30% IAS\n• Rüstung: +65% FRW, +40% IAS"},
            {"name": "METAMORPHOSE", "eng": "Metamorphosis", "runes": ["Io", "Cham", "Fal"], "lvl": 67, "sockets": 3,
             "type": "Helm", "patch": "2.6", "stats": "• Mal des Wolfes/Bären\n• +25% CB"},
            {"name": "FLACKERNDE FLAMME", "eng": "Flickering Flame", "runes": ["Nef", "Pul", "Vex"], "lvl": 55,
             "sockets": 3, "type": "Helm", "patch": "2.4", "stats": "• Lvl 4-8 Resist Fire Aura\n• +3 Feuer-Skills"},
            {"name": "HEILUNG", "eng": "Cure", "runes": ["Shael", "Io", "Tal"], "lvl": 35, "sockets": 3, "type": "Helm",
             "patch": "2.6", "stats": "• Lvl 1 Reinigung Aura\n• +20% FHR"},
            {"name": "NEBEL", "eng": "Mist", "runes": ["Cham", "Shael", "Gul", "Thul", "Ith"], "lvl": 67, "sockets": 5,
             "type": "Bogen", "patch": "2.4", "stats": "• Lvl 8-12 Konzentration Aura\n• 100% Stech-Angriff"},
            {"name": "UNBEUGSAMER WILLE", "eng": "Unbending Will", "runes": ["Fal", "Io", "Ith", "Eld", "El", "Hel"],
             "lvl": 41, "sockets": 6, "type": "Schwert", "patch": "2.4", "stats": "• +330% ED, +IAS, +Skills (Barbar)"},
            {"name": "WEISHEIT", "eng": "Wisdom", "runes": ["Pul", "Ith", "Eld"], "lvl": 45, "sockets": 3,
             "type": "Helm", "patch": "2.4", "stats": "• 33% Piercing, +5 Mana nach Kill"},

            # --- KLASSIKER & HIGH-END ---
            {"name": "RÄTSEL", "eng": "Enigma", "runes": ["Jah", "Ith", "Ber"], "lvl": 65, "sockets": 3,
             "type": "Rüstung", "patch": "1.10",
             "stats": "• +2 All Skills\n• +1 Teleport\n• +STR (Lvl basierend)\n• 45% FRW"},
            {"name": "GEIST", "eng": "Spirit", "runes": ["Tal", "Thul", "Ort", "Amn"], "lvl": 25, "sockets": 4,
             "type": "Schwert/Schild", "patch": "1.10", "stats": "• +2 All Skills\n• +25-35% FCR\n• +55% FHR"},
            {"name": "TRAUER", "eng": "Grief", "runes": ["Eth", "Tir", "Lo", "Mal", "Ral"], "lvl": 59, "sockets": 5,
             "type": "Waffe", "patch": "1.10", "stats": "• +340-400 Schaden\n• +30-40% IAS\n• -25% Ziel-Def"},
            {"name": "UNENDLICHKEIT", "eng": "Infinity", "runes": ["Ber", "Mal", "Ber", "Ist"], "lvl": 63, "sockets": 4,
             "type": "Waffe", "patch": "1.10", "stats": "• Lvl 12 Conviction Aura\n• -55% Blitz-Resi Gegner"},
            {"name": "RUF ZU DEN WAFFEN", "eng": "CTA", "runes": ["Amn", "Ral", "Mal", "Ist", "Ohm"], "lvl": 57,
             "sockets": 5, "type": "Waffe", "patch": "1.10", "stats": "• +1 All Skills\n• +1-6 Battle Orders"},
            {"name": "ODEM DER STERBENDEN", "eng": "BOTD", "runes": ["Vex", "Hel", "El", "Eld", "Zod", "Eth"],
             "lvl": 69, "sockets": 6, "type": "Waffe", "patch": "1.10",
             "stats": "• Unzerstörbar, +60% IAS, +350-400% ED"},
            {"name": "HERZ DER EICHE", "eng": "HOTO", "runes": ["Ko", "Vex", "Pul", "Thul"], "lvl": 55, "sockets": 4,
             "type": "Flegel/Stab", "patch": "1.10", "stats": "• +3 All Skills, +40% FCR, All Res +30-40"},
            {"name": "STÄRKE", "eng": "Fortitude", "runes": ["El", "Sol", "Dol", "Lo"], "lvl": 59, "sockets": 4,
             "type": "Rüstung/Waffe", "patch": "1.10", "stats": "• +300% ED, +200% Def, All Res +25-30"},
            {"name": "PHÖNIX", "eng": "Phoenix", "runes": ["Vex", "Vex", "Lo", "Jah"], "lvl": 65, "sockets": 4,
             "type": "Waffe/Schild", "patch": "1.10", "stats": "• Lvl 10-15 Rücknahme Aura, -28% Feuer-Resi Gegner"},
            {"name": "TRAUM", "eng": "Dream", "runes": ["Io", "Jah", "Pul"], "lvl": 65, "sockets": 3,
             "type": "Helm/Schild", "patch": "1.10", "stats": "• Lvl 15 Heiliger Schock Aura"},
            {"name": "DRACHE", "eng": "Dragon", "runes": ["Sur", "Lo", "Sol"], "lvl": 61, "sockets": 3,
             "type": "Rüstung/Schild", "patch": "1.10", "stats": "• Lvl 14 Heiliges Feuer Aura"},
            {"name": "EXIL", "eng": "Exile", "runes": ["Vex", "Ohm", "Ist", "Dol"], "lvl": 57, "sockets": 4,
             "type": "Paladin-Schild", "patch": "1.10", "stats": "• 15% Trotz Aura, Selbstreparatur"},
            {"name": "STOLZ", "eng": "Pride", "runes": ["Cham", "Sur", "Io", "Lo"], "lvl": 67, "sockets": 4,
             "type": "Stangenwaffe", "patch": "1.10", "stats": "• Lvl 16-20 Konzentration Aura"},
            {"name": "GLAUBE", "eng": "Faith", "runes": ["Ohm", "Jah", "Lem", "Eld"], "lvl": 65, "sockets": 4,
             "type": "Bogen", "patch": "1.10", "stats": "• Lvl 12-15 Fanatismus Aura"},
            {"name": "DORNEN", "eng": "Bramble", "runes": ["Ral", "Ohm", "Sur", "Eth"], "lvl": 61, "sockets": 4,
             "type": "Rüstung", "patch": "1.10", "stats": "• Lvl 15-21 Dornen Aura"},
            {"name": "LETZTER WUNSCH", "eng": "Last Wish", "runes": ["Jah", "Mal", "Jah", "Sur", "Jah", "Ber"],
             "lvl": 65, "sockets": 6, "type": "Waffe", "patch": "1.10", "stats": "• Lvl 17 Macht Aura, 60-70% CB"},

            # --- STARTER & MID-RANGE ---
            {"name": "HEIMLICHKEIT", "eng": "Stealth", "runes": ["Tal", "Eth"], "lvl": 17, "sockets": 2,
             "type": "Rüstung", "patch": "1.09", "stats": "• 25% FCR/FRW/FHR"},
            {"name": "ÜBERLIEFERUNG", "eng": "Lore", "runes": ["Ort", "Sol"], "lvl": 27, "sockets": 2, "type": "Helm",
             "patch": "1.09", "stats": "• +1 All Skills, +30 Blitz-Resi"},
            {"name": "REIM", "eng": "Rhyme", "runes": ["Shael", "Eth"], "lvl": 29, "sockets": 2, "type": "Schild",
             "patch": "1.09", "stats": "• Einfrieren nicht möglich, +25 All Res"},
            {"name": "WEISS", "eng": "White", "runes": ["Dol", "Io"], "lvl": 35, "sockets": 2, "type": "Stab",
             "patch": "1.09", "stats": "• +3 Gift/Knochen-Skills, +2 Knochenspeer"},
            {"name": "STAHL", "eng": "Steel", "runes": ["Tir", "El"], "lvl": 13, "sockets": 2, "type": "Waffe",
             "patch": "1.09", "stats": "• 25% IAS, 50% Offene Wunden"},
            {"name": "BLATT", "eng": "Leaf", "runes": ["Tir", "Ral"], "lvl": 19, "sockets": 2, "type": "Stab",
             "patch": "1.09", "stats": "• +3 Feuer-Skills, +3 Wärme"},
            {"name": "BOSHAFTIGKEIT", "eng": "Malice", "runes": ["Ith", "El", "Eth"], "lvl": 15, "sockets": 3,
             "type": "Waffe", "patch": "1.09", "stats": "• 100% Offene Wunden, Verhindert Heilung"},
            {"name": "VERRAT", "eng": "Treachery", "runes": ["Shael", "Thul", "Lem"], "lvl": 43, "sockets": 3,
             "type": "Rüstung", "patch": "1.11", "stats": "• 5% Fade bei Treffer, +45% IAS"},
            {"name": "GEHORSAM", "eng": "Obedience", "runes": ["Hel", "Ko", "Thul", "Eth", "Fal"], "lvl": 41,
             "sockets": 5, "type": "Stangenwaffe", "patch": "1.10", "stats": "• +370% ED, 40% CB"},
            {"name": "RAUCH", "eng": "Smoke", "runes": ["Nef", "Lum"], "lvl": 37, "sockets": 2, "type": "Rüstung",
             "patch": "1.09", "stats": "• +50 All Resis, +20% FHR"},
            {"name": "ERLEUCHTUNG", "eng": "Enlightenment", "runes": ["Pul", "Ral", "Sol"], "lvl": 45, "sockets": 3,
             "type": "Rüstung", "patch": "1.11", "stats": "• +2 Zauberin-Skills"},
            {"name": "FRIEDEN", "eng": "Peace", "runes": ["Shael", "Thul", "Amn"], "lvl": 29, "sockets": 3,
             "type": "Rüstung", "patch": "1.11", "stats": "• +2 Amazonen-Skills"},
            {"name": "MYTHOS", "eng": "Myth", "runes": ["Hel", "Amn", "Nef"], "lvl": 25, "sockets": 3,
             "type": "Rüstung", "patch": "1.11", "stats": "• +2 Barbaren-Skills"},
            {"name": "KNOCHEN", "eng": "Bone", "runes": ["Sol", "Um", "Um"], "lvl": 47, "sockets": 3, "type": "Rüstung",
             "patch": "1.11", "stats": "• +2 Necro-Skills"},
            {"name": "REGEN", "eng": "Rain", "runes": ["Ort", "Mal", "Ith"], "lvl": 49, "sockets": 3, "type": "Rüstung",
             "patch": "1.11", "stats": "• +2 Druiden-Skills"},
            {"name": "PRINZIP", "eng": "Principle", "runes": ["Gul", "Sur", "Io"], "lvl": 53, "sockets": 3,
             "type": "Rüstung", "patch": "1.11", "stats": "• +2 Paladin-Skills"},
            {"name": "MONDSICHEL", "eng": "Crescent Moon", "runes": ["Shael", "Um", "Tir"], "lvl": 47, "sockets": 3,
             "type": "Axt/Schwert/Stange", "patch": "1.10", "stats": "• -35% Blitz-Resi Gegner"},
            {"name": "HARMONIE", "eng": "Harmony", "runes": ["Tir", "Ith", "Sol", "Ko"], "lvl": 39, "sockets": 4,
             "type": "Bogen", "patch": "1.10", "stats": "• Lvl 10 Gedeihen Aura"},
            {"name": "EID", "eng": "Oath", "runes": ["Shael", "Pul", "Mal", "Lum"], "lvl": 49, "sockets": 4,
             "type": "Waffe", "patch": "1.10", "stats": "• Unzerstörbar, +50% IAS"},
            {"name": "TOD", "eng": "Death", "runes": ["Hel", "El", "Vex", "Ort", "Gul"], "lvl": 55, "sockets": 5,
             "type": "Waffe", "patch": "1.10", "stats": "• Unzerstörbar, 50% CB"},
            {"name": "EINSICHT", "eng": "Insight", "runes": ["Ral", "Tir", "Tal", "Sol"], "lvl": 27, "sockets": 4,
             "type": "Waffe", "patch": "1.10", "stats": "• Lvl 12-17 Meditations Aura"},
            {"name": "KÖNIGSMORD", "eng": "Kingslayer", "runes": ["Mal", "Um", "Gul", "Fal"], "lvl": 53, "sockets": 4,
             "type": "Waffe", "patch": "1.10", "stats": "• 33% CB, -25% Ziel-Def"},
            {"name": "SCHNEIDE", "eng": "Edge", "runes": ["Tir", "Tal", "Amn"], "lvl": 25, "sockets": 3,
             "type": "Bogen", "patch": "1.10", "stats": "• Lvl 15 Dornen Aura"},
            {"name": "WOHLSTAND", "eng": "Wealth", "runes": ["Lem", "Ko", "Tir"], "lvl": 43, "sockets": 3,
             "type": "Rüstung", "patch": "1.09", "stats": "• 300% Extragold, 100% MF"},
            {"name": "ZEPHYR", "eng": "Zephyr", "runes": ["Ort", "Eth"], "lvl": 21, "sockets": 2, "type": "Bogen",
             "patch": "1.09", "stats": "• +25% FRW/IAS"},
            {"name": "ZUFLUCHT", "eng": "Sanctuary", "runes": ["Ko", "Ko", "Mal"], "lvl": 49, "sockets": 3,
             "type": "Schild", "patch": "1.10", "stats": "• +50-70 All Res, 20% Block"},
            {"name": "LÖWENHERZ", "eng": "Lionheart", "runes": ["Hel", "Lum", "Fal"], "lvl": 41, "sockets": 3,
             "type": "Rüstung", "patch": "1.09", "stats": "• +All Stats, +30 All Res"},
            {"name": "STILLE", "eng": "Silence", "runes": ["Dol", "Eld", "Hel", "Ist", "Tir", "Vex"], "lvl": 55,
             "sockets": 6, "type": "Waffe", "patch": "1.09", "stats": "• +2 Skills, All Res +75"},
            {"name": "BOGEN_MELODIE", "eng": "Melody", "runes": ["Shael", "Ko", "Nef"], "lvl": 39, "sockets": 3,
             "type": "Bogen", "patch": "1.09", "stats": "• +3 Bogen-Skills, 20% IAS"},
            {"name": "ERINNERUNG", "eng": "Memory", "runes": ["Lum", "Io", "Sol", "Eth"], "lvl": 37, "sockets": 4,
             "type": "Stab", "patch": "1.09", "stats": "• +3 Sorc Skills, +3 Energieschild"},
            {"name": "KÖNIGLICHE GNADE", "eng": "King's Grace", "runes": ["Amn", "Ral", "Thul"], "lvl": 25,
             "sockets": 3, "type": "Schwert", "patch": "1.09", "stats": "• +100% Dmg an Dämonen"},
            {"name": "LEIDENSCHAFT", "eng": "Passion", "runes": ["Dol", "Ort", "Eld", "Lem"], "lvl": 43, "sockets": 4,
             "type": "Waffe", "patch": "1.10", "stats": "• +1 Eifer, +1 Amok"},
            {"name": "NADIR", "eng": "Nadir", "runes": ["Nef", "Tir"], "lvl": 13, "sockets": 2, "type": "Helm",
             "patch": "1.09", "stats": "• Lvl 13 Cloak of Shadows"},
            {"name": "PRASSSELN", "eng": "Pattern", "runes": ["Tal", "Ort", "Thul"], "lvl": 23, "sockets": 3,
             "type": "Klaue", "patch": "2.4", "stats": "• +All Res, +Skills"},
            {"name": "PEST", "eng": "Plague", "runes": ["Cham", "Shael", "Um"], "lvl": 67, "sockets": 3,
             "type": "Waffe", "patch": "2.4", "stats": "• 20% Lower Resist bei Treffer"},
            {"name": "BRAND", "eng": "Brand", "runes": ["Jah", "Lo", "Mal", "Gul"], "lvl": 65, "sockets": 4,
             "type": "Bogen", "patch": "1.10", "stats": "• 100% Knochenspeer bei Treffer"},
            {"name": "EIS", "eng": "Ice", "runes": ["Amn", "Shael", "Jah", "Lo"], "lvl": 65, "sockets": 4,
             "type": "Bogen", "patch": "1.10", "stats": "• Lvl 18 Heiliger Frost Aura"},
            {"name": "ZERSTÖRUNG", "eng": "Destruction", "runes": ["Vex", "Lo", "Ber", "Jah", "Ko"], "lvl": 65,
             "sockets": 5, "type": "Waffe", "patch": "1.10", "stats": "• Chance auf Vulkan/Riss bei Treffer"},
            {"name": "UNENDLICH", "eng": "Boundless", "runes": ["Zod", "Cham", "Jah", "Ber"], "lvl": 69, "sockets": 4,
             "type": "Schild", "patch": "3.0", "stats": "• +3 All Skills, All Res +50, DR 15%"},
            {"name": "EWIGKEIT", "eng": "Eternity", "runes": ["Amn", "Ber", "Ist", "Sol", "Sur"], "lvl": 63,
             "sockets": 5, "type": "Waffe", "patch": "1.10", "stats": "• Unzerstörbar, 20% CB, Wiederbeleben"}
        ]

        self.rune_vars = {}
        self.create_widgets()

    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # 1. FILTER HEADER
        filter_header = ctk.CTkFrame(self, fg_color="transparent")
        filter_header.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        self.type_filter = ctk.CTkOptionMenu(filter_header,
                                             values=["Alle Typen", "Waffe", "Rüstung", "Helm", "Schild", "Bogen",
                                                     "Stab", "Klaue"], command=lambda x: self.apply_filters())
        self.type_filter.pack(side="left", padx=5)

        self.socket_filter = ctk.CTkOptionMenu(filter_header, values=["Alle Sockel", "2", "3", "4", "5", "6"],
                                               command=lambda x: self.apply_filters())
        self.socket_filter.pack(side="left", padx=5)

        self.patch_filter = ctk.CTkOptionMenu(filter_header,
                                              values=["Alle Patches", "3.0", "2.6", "2.4", "1.11", "1.10", "1.09"],
                                              command=lambda x: self.apply_filters())
        self.patch_filter.pack(side="left", padx=5)

        # 2. RUNEN GRID (Nur Text-Checkboxes)
        rune_grid_frame = ctk.CTkFrame(self, border_width=1, border_color="#333333")
        rune_grid_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

        for i, rune in enumerate(self.all_runes):
            var = ctk.BooleanVar(value=False)
            self.rune_vars[rune] = var
            cb = ctk.CTkCheckBox(rune_grid_frame, text=rune, variable=var, font=("Segoe UI", 11),
                                 checkbox_width=18, checkbox_height=18, width=75, command=self.apply_filters)
            cb.grid(row=(i // 11), column=i % 11, padx=4, pady=8, sticky="w")

        # 3. MITTE: LISTE
        list_container = ctk.CTkFrame(self, fg_color="transparent")
        list_container.grid(row=2, column=0, sticky="nsew", padx=10)
        list_container.grid_columnconfigure(0, weight=1)
        list_container.grid_rowconfigure(1, weight=1)

        self.search_entry = ctk.CTkEntry(list_container, placeholder_text="Suche Name oder Runenkombination...",
                                         height=35)
        self.search_entry.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.search_entry.bind("<KeyRelease>", lambda e: self.apply_filters())

        t_frame = ctk.CTkFrame(list_container)
        t_frame.grid(row=1, column=0, sticky="nsew")
        style = ttk.Style()
        style.configure("Runes.Treeview", background="#212121", foreground="white", fieldbackground="#212121",
                        rowheight=30)
        style.map("Runes.Treeview", background=[('selected', '#1f538d')])

        self.tree = ttk.Treeview(t_frame, columns=("n", "r", "s", "l", "p"), show="headings", style="Runes.Treeview")
        self.tree.heading("n", text="Name");
        self.tree.heading("r", text="Runen")
        self.tree.heading("s", text="S.");
        self.tree.heading("l", text="Lvl");
        self.tree.heading("p", text="Patch")
        for c, w in zip(("n", "r", "s", "l", "p"), (160, 240, 40, 40, 60)):
            self.tree.column(c, width=w, anchor="center" if c not in ("n", "r") else "w")

        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.show_details)

        # 4. UNTEN: PREVIEW (Ohne Canvas)
        self.preview_frame = ctk.CTkFrame(self, border_width=1, border_color="#1f538d", fg_color="#1a1a1a")
        self.preview_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        self.preview_frame.grid_columnconfigure(1, weight=3)

        # Statischer Sockel-Anzeiger (Text-basiert)
        self.socket_info_frame = ctk.CTkFrame(self.preview_frame, width=80, height=140, fg_color="#111111")
        self.socket_info_frame.grid(row=0, column=0, padx=15, pady=15, sticky="ns")
        self.lbl_socket_visual = ctk.CTkLabel(self.socket_info_frame, text="", font=("Segoe UI", 16, "bold"),
                                              text_color="#FF9500")
        self.lbl_socket_visual.pack(expand=True)

        self.stats_content = ctk.CTkFrame(self.preview_frame, fg_color="transparent")
        self.stats_content.grid(row=0, column=1, padx=5, pady=15, sticky="nsew")
        self.lbl_title = ctk.CTkLabel(self.stats_content, text="Wähle ein Runenwort", font=("Segoe UI", 20, "bold"),
                                      text_color="#FFD700", anchor="w")
        self.lbl_title.pack(fill="x")
        self.lbl_sub = ctk.CTkLabel(self.stats_content, text="", font=("Segoe UI", 12), text_color="#aaaaaa",
                                    anchor="w")
        self.lbl_sub.pack(fill="x")
        self.lbl_stats = ctk.CTkLabel(self.stats_content, text="", font=("Segoe UI", 14), justify="left",
                                      wraplength=500, anchor="nw")
        self.lbl_stats.pack(fill="both", pady=10)

        self.rune_list_frame = ctk.CTkFrame(self.preview_frame, fg_color="transparent")
        self.rune_list_frame.grid(row=0, column=2, padx=20, pady=15, sticky="ne")
        ctk.CTkLabel(self.rune_list_frame, text="RUNENLISTE", font=("Segoe UI", 10, "bold"),
                     text_color="#888888").pack()
        self.rune_text_container = ctk.CTkFrame(self.rune_list_frame, fg_color="transparent")
        self.rune_text_container.pack(pady=5)

        self.footer = ctk.CTkLabel(self.preview_frame, text="", font=("Segoe UI", 10), text_color="#666666",
                                   fg_color="#111111")
        self.footer.grid(row=1, column=0, columnspan=3, sticky="ew")

        self.apply_filters()

    def apply_filters(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        search = self.search_entry.get().lower()
        f_type = self.type_filter.get();
        f_sock = self.socket_filter.get();
        f_patch = self.patch_filter.get()
        active_runes = [r for r, v in self.rune_vars.items() if v.get()]

        for rw in self.runewords:
            match_t = f_type == "Alle Typen" or f_type.lower() in rw.get("type", "").lower()
            match_s = f_sock == "Alle Sockel" or str(rw.get("sockets", "")) == f_sock
            match_p = f_patch == "Alle Patches" or rw.get("patch", "") == f_patch
            match_txt = search in rw.get("name", "").lower() or any(search in r.lower() for r in rw.get("runes", []))
            match_rune = True if not active_runes else any(r in rw.get("runes", []) for r in active_runes)

            if match_t and match_s and match_p and match_txt and match_rune:
                self.tree.insert("", "end",
                                 values=(rw["name"], " + ".join(rw["runes"]), rw["sockets"], rw["lvl"], rw["patch"]))

    def show_details(self, event):
        sel = self.tree.selection()
        if not sel: return
        name = self.tree.item(sel[0])['values'][0]
        rw = next((r for r in self.runewords if r["name"] == name), None)
        if not rw: return

        self.lbl_title.configure(text=rw["name"])
        self.lbl_sub.configure(text=f"RUNENWORT | {rw['sockets']} SOCKEL | PATCH {rw['patch']}")
        self.lbl_stats.configure(text=rw["stats"])
        self.footer.configure(text=f"Level: {rw['lvl']} | Typ: {rw['type']} | Engl: {rw.get('eng')}")

        for w in self.rune_text_container.winfo_children(): w.destroy()
        for i, r in enumerate(rw["runes"]):
            ctk.CTkLabel(self.rune_text_container, text=f"{i + 1}. {r.upper()}", font=("Segoe UI", 13, "bold"),
                         text_color="#FF9500").pack(anchor="w")

        # Sockel Visualisierung mit ASCII/Symbolen
        sock_vis = "\n".join(["( O )" for _ in range(rw["sockets"])])
        self.lbl_socket_visual.configure(text=sock_vis)