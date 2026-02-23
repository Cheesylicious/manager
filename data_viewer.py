import customtkinter as ctk
from tkinter import ttk
import os
import sys
from PIL import Image

# HIER IMPORTIEREN WIR DIE NEUE DATENBANK, UM DIE DATEI SCHLANK ZU HALTEN!
from runeword_data import RUNEWORDS


class RunewordConfigurator(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.all_runes = [
            "El", "Eld", "Tir", "Nef", "Eth", "Ith", "Tal", "Ral", "Ort", "Thul", "Amn", "Sol", "Shael", "Dol", "Hel",
            "Io",
            "Lum", "Ko", "Fal", "Lem", "Pul", "Um", "Mal", "Ist", "Gul", "Vex", "Ohm", "Lo", "Sur", "Ber", "Jah",
            "Cham", "Zod"
        ]

        # Greift auf die ausgelagerte, detailreiche Datenbank zu
        self.runewords = RUNEWORDS

        # Intelligente Pools für die Autovervollständigung
        self.pool_names = [rw["name"] for rw in self.runewords] + self.all_runes
        self.pool_stats = [
            "Schnellere Zauberrate", "Schnellere Erholung nach Treffer", "Schneller Rennen/Gehen",
            "Erhöhter Schaden", "Erhöhte Angriffsgeschwindigkeit", "Bonus zu Angriffswert",
            "Todesschlag", "vernichtenden Schlag", "offene Wunden",
            "Alle Widerstandsarten", "Feuer-Widerstand", "Blitz-Widerstand", "Kälte-Widerstand", "Gift-Widerstand",
            "Leben", "Mana", "Stärke", "Geschicklichkeit", "Vitalität", "Energie",
            "zu allen Fertigkeiten", "Teleportieren", "Einfrieren nicht möglich",
            "Bessere Chance, magischen Gegenstand zu finden", "Extragold von Monstern", "Verbesserte Verteidigung",
            "Abgesaugtes", "Schaden reduziert", "Aura"
        ]
        self.sugg_frame = None

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

        # 3. MITTE: LISTE UND DOPPELTE SUCHFELDER
        list_container = ctk.CTkFrame(self, fg_color="transparent")
        list_container.grid(row=2, column=0, sticky="nsew", padx=10)
        list_container.grid_columnconfigure(0, weight=1)
        list_container.grid_rowconfigure(1, weight=1)

        search_frame = ctk.CTkFrame(list_container, fg_color="transparent")
        search_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        search_frame.grid_columnconfigure(0, weight=1)
        search_frame.grid_columnconfigure(1, weight=1)

        # Suchfeld 1: Standard Suche (Blaues Design)
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="🔍 Suche: Name oder Runenkombination...",
                                         height=35, border_color="#1f538d", border_width=2)
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.search_entry.bind("<KeyRelease>", self.on_search_name_key)
        self.search_entry.bind("<FocusOut>", lambda e: self.after(200, self.hide_suggestions))

        # Suchfeld 2: Eigenschaften Suche (Grünes Design zur klaren Unterscheidung)
        self.search_stats_entry = ctk.CTkEntry(search_frame,
                                               placeholder_text="✨ Suche Eigenschaft: (z.B. Todesschlag, Widerstand...)",
                                               height=35, border_color="#2da44e", border_width=2)
        self.search_stats_entry.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        self.search_stats_entry.bind("<KeyRelease>", self.on_search_stats_key)
        self.search_stats_entry.bind("<FocusOut>", lambda e: self.after(200, self.hide_suggestions))

        t_frame = ctk.CTkFrame(list_container)
        t_frame.grid(row=1, column=0, sticky="nsew")
        style = ttk.Style()
        style.configure("Runes.Treeview", background="#212121", foreground="white", fieldbackground="#212121",
                        rowheight=30)
        style.map("Runes.Treeview", background=[('selected', '#1f538d')])

        self.tree = ttk.Treeview(t_frame, columns=("n", "r", "s", "l", "p"), show="headings", style="Runes.Treeview")
        self.tree.heading("n", text="Name")
        self.tree.heading("r", text="Runen")
        self.tree.heading("s", text="S.")
        self.tree.heading("l", text="Lvl")
        self.tree.heading("p", text="Patch")
        for c, w in zip(("n", "r", "s", "l", "p"), (160, 240, 40, 40, 60)):
            self.tree.column(c, width=w, anchor="center" if c not in ("n", "r") else "w")

        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.show_details)

        # 4. UNTEN: PREVIEW
        self.preview_frame = ctk.CTkFrame(self, border_width=1, border_color="#1f538d", fg_color="#1a1a1a")
        self.preview_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        self.preview_frame.grid_columnconfigure(1, weight=3)

        self.socket_info_frame = ctk.CTkFrame(self.preview_frame, width=80, height=140, fg_color="#111111")
        self.socket_info_frame.grid(row=0, column=0, padx=15, pady=15, sticky="ns")
        self.socket_info_frame.pack_propagate(False)

        self.stats_content = ctk.CTkScrollableFrame(self.preview_frame, fg_color="transparent", height=130)
        self.stats_content.grid(row=0, column=1, padx=5, pady=15, sticky="nsew")

        self.lbl_title = ctk.CTkLabel(self.stats_content, text="Wähle ein Runenwort", font=("Segoe UI", 20, "bold"),
                                      text_color="#FFD700", anchor="w")
        self.lbl_title.pack(fill="x")
        self.lbl_sub = ctk.CTkLabel(self.stats_content, text="", font=("Segoe UI", 12), text_color="#aaaaaa",
                                    anchor="w")
        self.lbl_sub.pack(fill="x")

        self.lbl_stats = ctk.CTkLabel(self.stats_content, text="", font=("Segoe UI", 14), justify="left",
                                      wraplength=460, anchor="nw")
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

    # --- AUTOVERVOLLSTÄNDIGUNG LOGIK ---
    def on_search_name_key(self, event):
        self.apply_filters()
        self.show_suggestions(self.search_entry, self.pool_names)

    def on_search_stats_key(self, event):
        self.apply_filters()
        self.show_suggestions(self.search_stats_entry, self.pool_stats)

    def show_suggestions(self, entry_widget, pool):
        text = entry_widget.get().lower()
        self.hide_suggestions()

        if not text or len(text) < 1:
            return

        # Finde bis zu 6 passende Vorschläge
        matches = [m for m in pool if text in m.lower()][:6]
        if not matches:
            return

        # Berechne die Position direkt unter dem jeweiligen Suchfeld
        x = entry_widget.winfo_x()
        y = entry_widget.winfo_y() + entry_widget.winfo_height()
        width = entry_widget.winfo_width()

        # Erstelle das schwebende Dropdown-Menü (width wird hier direkt im Konstruktor übergeben)
        self.sugg_frame = ctk.CTkFrame(entry_widget.master, fg_color="#212121", border_width=1,
                                       border_color=entry_widget.cget("border_color"), width=width)
        self.sugg_frame.place(x=x, y=y)
        self.sugg_frame.lift()  # Stellt sicher, dass das Menü im Vordergrund liegt

        for m in matches:
            btn = ctk.CTkButton(self.sugg_frame, text=m, fg_color="transparent", hover_color="#1f538d",
                                anchor="w", font=("Segoe UI", 12), text_color="#eeeeee",
                                command=lambda val=m, ent=entry_widget: self.select_suggestion(ent, val))
            btn.pack(fill="x", padx=2, pady=1)

    def hide_suggestions(self):
        if self.sugg_frame and self.sugg_frame.winfo_exists():
            self.sugg_frame.destroy()
            self.sugg_frame = None

    def select_suggestion(self, entry_widget, value):
        entry_widget.delete(0, "end")
        entry_widget.insert(0, value)
        self.hide_suggestions()
        self.apply_filters()

    # -----------------------------------

    def apply_filters(self):
        for i in self.tree.get_children(): self.tree.delete(i)

        search_name = self.search_entry.get().lower()
        search_stats = self.search_stats_entry.get().lower()

        f_type = self.type_filter.get()
        f_sock = self.socket_filter.get()
        f_patch = self.patch_filter.get()
        active_runes = [r for r, v in self.rune_vars.items() if v.get()]

        for rw in self.runewords:
            match_t = f_type == "Alle Typen" or f_type.lower() in rw.get("type", "").lower()
            match_s = f_sock == "Alle Sockel" or str(rw.get("sockets", "")) == f_sock
            match_p = f_patch == "Alle Patches" or rw.get("patch", "") == f_patch

            match_txt = search_name in rw.get("name", "").lower() or any(
                search_name in r.lower() for r in rw.get("runes", []))
            match_stat = search_stats in rw.get("stats", "").lower()
            match_rune = True if not active_runes else all(r in rw.get("runes", []) for r in active_runes)

            if match_t and match_s and match_p and match_txt and match_stat and match_rune:
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

        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        folder_path = os.path.join(base_path, "runes_inventory")

        for w in self.rune_text_container.winfo_children(): w.destroy()
        for w in self.socket_info_frame.winfo_children(): w.destroy()

        for i, r in enumerate(rw["runes"]):
            rune_name = r.capitalize()
            img_path = os.path.join(folder_path, f"{rune_name}.png")

            list_row = ctk.CTkFrame(self.rune_text_container, fg_color="transparent")
            list_row.pack(anchor="w", pady=2)

            ctk.CTkLabel(list_row, text=f"{i + 1}. ", font=("Segoe UI", 13, "bold"), text_color="#aaaaaa").pack(
                side="left")

            has_img = False
            if os.path.exists(img_path):
                try:
                    pil_img = Image.open(img_path)
                    ctk_img_list = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(20, 20))
                    ctk_img_sock = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(24, 24))

                    ctk.CTkLabel(list_row, image=ctk_img_list, text="").pack(side="left", padx=(0, 5))
                    ctk.CTkLabel(self.socket_info_frame, image=ctk_img_sock, text="").pack(pady=2, expand=True)
                    has_img = True
                except:
                    pass

            if not has_img:
                ctk.CTkLabel(list_row, text="[?]", font=("Segoe UI", 13, "bold"), text_color="#555555").pack(
                    side="left", padx=(0, 5))
                ctk.CTkLabel(self.socket_info_frame, text="( O )", font=("Segoe UI", 16, "bold"),
                             text_color="#FF9500").pack(pady=2, expand=True)

            ctk.CTkLabel(list_row, text=rune_name.upper(), font=("Segoe UI", 13, "bold"), text_color="#FF9500").pack(
                side="left")

        for _ in range(rw["sockets"] - len(rw["runes"])):
            ctk.CTkLabel(self.socket_info_frame, text="( O )", font=("Segoe UI", 16, "bold"),
                         text_color="#555555").pack(pady=2, expand=True)