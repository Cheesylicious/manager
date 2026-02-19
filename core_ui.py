import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import base64
import subprocess
import time
import threading
import ctypes
from ctypes import wintypes
from PIL import Image

# Getarnte Eigene Module
import handle_cleaner
import sys_hooks
from help_guide import TutorialAssistant
from data_viewer import RunewordConfigurator
from overlay_widget import TrackerConfigurator

# --- CONFIG & KONSTANTEN ---
CONFIG_FILE = "profile_data.json"
WINDOW_TITLE_GAME = "Diablo II: Resurrected"
WINDOW_TITLE_LAUNCHER = "Battle.net"

# Windows API
user32 = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


VK_LBUTTON = 0x01

# --- MODERN UI SETUP ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")


# --- HAUPT PROGRAMM ---
class MainManager(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("System Verwaltung")
        self.geometry("950x900")

        self.settings = {
            "first_run": True,
            "accounts": [],
            "coords": {}
        }
        self.load_config()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.tab_accounts = self.tabview.add("Profile & Start")
        self.tab_runewords = self.tabview.add("Datenbank")
        self.tab_tracker = self.tabview.add("Overlay & Tracker")

        self.create_widgets()
        self.create_runeword_tab()
        self.create_tracker_tab()

        self.overlay = None
        self.blocker = None

        if self.settings.get("first_run", True):
            self.after(800, self.start_tutorial)

    # --- CORE ---
    def obscure(self, t):
        return base64.b64encode(t.encode()).decode()

    def deobscure(self, t):
        return base64.b64decode(t.encode()).decode()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.settings["accounts"] = data
                    else:
                        if "coords" not in data: data["coords"] = {}
                        if "first_run" not in data: data["first_run"] = True
                        defaults = ["switch_x", "switch_y", "email_x", "email_y", "continue_x", "continue_y", "pwd_x",
                                    "pwd_y", "login_x", "login_y"]
                        for k in defaults:
                            if k not in data["coords"]: data["coords"][k] = 0
                        self.settings = data
            except:
                pass

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f: json.dump(self.settings, f, indent=4)

    # --- UI TABS ---
    def create_runeword_tab(self):
        self.rw_tool = RunewordConfigurator(self.tab_runewords)
        self.rw_tool.pack(fill="both", expand=True)

    def create_tracker_tab(self):
        self.tracker_tool = TrackerConfigurator(self.tab_tracker, self)
        self.tracker_tool.pack(fill="both", expand=True)

    def create_widgets(self):
        self.main_frame = ctk.CTkScrollableFrame(self.tab_accounts, corner_radius=0, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # HEADER
        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        ctk.CTkLabel(self.header_frame, text="APPLIKATIONS-MANAGER", font=("Roboto Medium", 24, "bold"),
                     text_color="#aaaaaa").pack(anchor="w")
        ctk.CTkLabel(self.header_frame, text="UMGEBUNGS-STEUERUNG", font=("Roboto Medium", 32, "bold"),
                     text_color="white").pack(anchor="w")

        self.btn_help = ctk.CTkButton(self.header_frame, text="❓ Anleitung", width=80, command=self.start_tutorial,
                                      fg_color="#333333")
        self.btn_help.place(relx=1.0, rely=0.5, anchor="e")

        # LISTE
        self.list_group = ctk.CTkFrame(self.main_frame)
        self.list_group.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        ctk.CTkLabel(self.list_group, text="GESPEICHERTE PROFILE", font=("Roboto Medium", 14)).pack(anchor="w", padx=15,
                                                                                                 pady=(15, 5))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", borderwidth=0,
                        rowheight=30, font=("Roboto", 11))
        style.configure("Treeview.Heading", background="#1f1f1f", foreground="white", relief="flat",
                        font=("Roboto", 11, "bold"))
        style.map("Treeview", background=[('selected', '#1f538d')])

        self.tree = ttk.Treeview(self.list_group, columns=("n", "p", "e"), show="headings", height=6)
        self.tree.heading("n", text="Profil Name", anchor="w");
        self.tree.heading("p", text="Ausführbare Datei (.exe)", anchor="w");
        self.tree.heading("e", text="Benutzer-Login", anchor="w")
        self.tree.column("n", width=150);
        self.tree.column("p", width=350);
        self.tree.column("e", width=200)
        self.tree.pack(fill="x", padx=15, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # EDITOR
        self.edit_group = ctk.CTkFrame(self.main_frame)
        self.edit_group.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        ctk.CTkLabel(self.edit_group, text="PROFIL BEARBEITEN / NEU ANLEGEN", font=("Roboto Medium", 14)).grid(row=0, column=0, columnspan=3,
                                                                                          sticky="w", padx=15,
                                                                                          pady=(15, 10))

        self.en = ctk.CTkEntry(self.edit_group, placeholder_text="Profil Name (z.B. Mein Main Char)", height=35)
        self.en.grid(row=1, column=0, sticky="ew", padx=15, pady=5)

        self.ee = ctk.CTkEntry(self.edit_group, placeholder_text="Login E-Mail Adresse", height=35)
        self.ee.grid(row=1, column=1, sticky="ew", padx=15, pady=5)

        self.ep = ctk.CTkEntry(self.edit_group, placeholder_text="Pfad zur Start-Datei (z.B. Battle.net Launcher.exe)", height=35)
        self.ep.grid(row=2, column=0, columnspan=2, sticky="ew", padx=15, pady=5)

        self.btn_browse = ctk.CTkButton(self.edit_group, text="...", width=40, height=35, command=self.browse,
                                        fg_color="#444444")
        self.btn_browse.grid(row=2, column=2, padx=(0, 15), pady=5)

        self.ew = ctk.CTkEntry(self.edit_group, placeholder_text="Passwort (wird verschleiert gespeichert)", show="●", height=35)
        self.ew.grid(row=3, column=0, columnspan=2, sticky="ew", padx=15, pady=5)

        self.btn_box = ctk.CTkFrame(self.edit_group, fg_color="transparent")
        self.btn_box.grid(row=4, column=0, columnspan=3, sticky="ew", padx=15, pady=15)

        self.btn_save = ctk.CTkButton(self.btn_box, text="Speichern", command=self.save, fg_color="#2da44e",
                                      hover_color="#2c974b")
        self.btn_save.pack(side="left", padx=(0, 10))

        ctk.CTkButton(self.btn_box, text="Eingaben leeren", command=self.clear, fg_color="transparent", border_width=1,
                      text_color="#aaaaaa").pack(side="left", padx=10)
        ctk.CTkButton(self.btn_box, text="Profil löschen", command=self.delete, fg_color="#cf222e",
                      hover_color="#a40e26").pack(side="right")
        self.edit_group.grid_columnconfigure(0, weight=1);
        self.edit_group.grid_columnconfigure(1, weight=1)

        # ACTION
        self.action_group = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.action_group.grid(row=3, column=0, sticky="ew", padx=20, pady=10)

        self.btn_calib = ctk.CTkButton(self.action_group, text="🛠️ System Kalibrierung starten (Nur 1x nötig!)",
                                       command=self.start_calibration, fg_color="#333333", height=40)
        self.btn_calib.pack(fill="x", pady=5)

        self.btn_launch = ctk.CTkButton(self.action_group, text="▶  AUSGEWÄHLTES PROFIL STARTEN", command=self.launch,
                                        font=("Roboto Medium", 16), height=60, fg_color="#1f538d")
        self.btn_launch.pack(fill="x", pady=10)

        ctk.CTkButton(self.action_group, text="Multi-Client Freischaltung (Manuell erzwingen)", command=self.manual_unlock,
                      fg_color="transparent", text_color="#666666", height=30).pack(fill="x")

        self.status_bar = ctk.CTkLabel(self, text="Status: Bereit.", text_color="#00ccff", font=("Roboto", 12))
        self.status_bar.grid(row=1, column=0, sticky="ew", pady=10)

        self.refresh()

    def start_tutorial(self):
        steps = [
            {
                "title": "🔒 100% Sicher & Lokal",
                "text": "Dieses Tool arbeitet komplett offline. Es werden KEINE Daten ins Internet gesendet.\n\nDeine E-Mail und Passwörter bleiben ausschließlich auf deinem eigenen Computer in der Datei 'profile_data.json'.",
                "target": None
            },
            {
                "title": "Schritt 1: Profil Daten",
                "text": "Trage hier einen beliebigen Namen für dein Profil ein (z.B. 'Mein Zauberer').\nDanach gibst du deine E-Mail und dein Passwort ein. Keine Angst, das Passwort wird unleserlich abgespeichert.",
                "target": self.en,
                "pos": "right"
            },
            {
                "title": "Schritt 2: Datei auswählen",
                "text": "Klicke auf den kleinen Button mit den drei Punkten '...' und suche die Programm-Datei, die gestartet werden soll (meistens die Battle.net Launcher.exe).",
                "target": self.btn_browse,
                "pos": "left"
            },
            {
                "title": "Schritt 3: Speichern",
                "text": "Wenn du alle Daten eingetragen hast, klicke auf 'Speichern'. Das Profil erscheint dann oben in der Liste.",
                "target": self.btn_save,
                "pos": "top"
            },
            {
                "title": "Schritt 4: Einmalige Kalibrierung",
                "text": "SEHR WICHTIG: Bevor du das erste Mal startest, musst du das Tool an deinen Monitor anpassen.\n\nKlicke auf diesen Button. Das Tool wird dir dann genaue Anweisungen geben, worauf du klicken musst, damit es weiß, wo sich die Eingabefelder befinden.",
                "target": self.btn_calib,
                "pos": "top"
            },
            {
                "title": "Schritt 5: Starten!",
                "text": "Wähle oben in der Liste dein Profil aus und klicke auf diesen riesigen blauen Button.\n\n⚠️ ACHTUNG: Sobald der rote Warnbildschirm erscheint, nimmst du die Hände von der Maus und Tastatur! Das Programm tippt nun alles automatisch für dich ein.",
                "target": self.btn_launch,
                "pos": "top"
            }
        ]
        TutorialAssistant(self, steps)

    def finish_tutorial(self):
        self.settings["first_run"] = False
        self.save_config()

    def manual_unlock(self):
        handle_cleaner.main()
        self.status_bar.configure(text="Status: Multi-Client Sperren wurden entfernt.", text_color="green")

    def browse(self):
        f = filedialog.askopenfilename(filetypes=[("EXE", "*.exe")])
        if f: self.ep.delete(0, tk.END); self.ep.insert(0, f)

    def refresh(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for a in self.settings.get("accounts", []): self.tree.insert("", "end",
                                                                     values=(a["name"], a["path"], a["email"]))

    def on_select(self, e):
        s = self.tree.selection()
        if s:
            n = self.tree.item(s[0])['values'][0]
            for a in self.settings["accounts"]:
                if a["name"] == n:
                    self.en.delete(0, tk.END);
                    self.en.insert(0, a["name"])
                    self.ep.delete(0, tk.END);
                    self.ep.insert(0, a["path"])
                    self.ee.delete(0, tk.END);
                    self.ee.insert(0, a["email"])
                    self.ew.delete(0, tk.END);
                    self.ew.insert(0, self.deobscure(a["password"]))

    def clear(self):
        self.en.delete(0, tk.END);
        self.ep.delete(0, tk.END);
        self.ee.delete(0, tk.END);
        self.ew.delete(0, tk.END)
        self.tree.selection_remove(self.tree.selection())

    def save(self):
        n = self.en.get();
        p = self.ep.get();
        e = self.ee.get();
        w = self.ew.get()
        if not n or not p: return
        data = {"name": n, "path": p, "email": e, "password": self.obscure(w)}
        if "accounts" not in self.settings: self.settings["accounts"] = []
        found = False
        for i, a in enumerate(self.settings["accounts"]):
            if a["name"] == n: self.settings["accounts"][i] = data; found = True; break
        if not found: self.settings["accounts"].append(data)
        self.save_config();
        self.refresh();
        self.status_bar.configure(text=f"Status: Profil '{n}' erfolgreich gespeichert.", text_color="green")

    def delete(self):
        n = self.en.get()
        self.settings["accounts"] = [a for a in self.settings["accounts"] if a["name"] != n]
        self.save_config();
        self.refresh();
        self.clear()

    def show_blocker(self):
        if self.blocker: return
        self.blocker = ctk.CTkToplevel(self)
        self.blocker.attributes('-topmost', True);
        self.blocker.overrideredirect(True)
        sw = self.winfo_screenwidth();
        sh = self.winfo_screenheight()
        w = 650;
        h = 350
        x = (sw - w) // 2;
        y = (sh - h) // 2
        self.blocker.geometry(f"{w}x{h}+{x}+{y}")
        self.blocker.configure(fg_color="#8B0000")
        bg = "#8B0000"
        ctk.CTkLabel(self.blocker, text="⚠️ SYSTEM GESPERRT ⚠️", font=("Roboto", 40, "bold"), text_color="#FFD700",
                     bg_color=bg).pack(pady=(40, 10))
        ctk.CTkLabel(self.blocker, text="AUTOMATISIERUNG LÄUFT", font=("Roboto", 24, "bold"), text_color="white",
                     bg_color=bg).pack(pady=5)
        ctk.CTkLabel(self.blocker, text="Nimm jetzt die Hände von Maus und Tastatur!", font=("Roboto", 18), text_color="#cccccc",
                     bg_color=bg).pack(pady=5)
        self.lbl_timer = ctk.CTkLabel(self.blocker, text="0s", font=("Roboto Mono", 30, "bold"), text_color="#CCCCCC",
                                      bg_color=bg)
        self.lbl_timer.pack(pady=20)
        self.start_time = time.time();
        self.update_timer()

    def update_timer(self):
        if self.blocker:
            elapsed = int(time.time() - self.start_time)
            self.lbl_timer.configure(text=f"{elapsed}s")
            self.blocker.after(1000, self.update_timer)

    def close_blocker(self):
        if self.blocker: self.blocker.destroy(); self.blocker = None

    def show_overlay(self, text):
        if self.overlay is None or not ctk.CTkToplevel.winfo_exists(self.overlay):
            self.overlay = ctk.CTkToplevel(self)
            self.overlay.overrideredirect(True);
            self.overlay.attributes('-topmost', True)
            self.overlay.geometry("+50+50")
            self.overlay_frame = ctk.CTkFrame(self.overlay, fg_color="#2b2b2b", border_width=3, border_color="#FF3333")
            self.overlay_frame.pack(fill="both", expand=True)
            self.lbl_overlay = ctk.CTkLabel(self.overlay_frame, text=text, text_color="#FF3333",
                                            font=("Roboto", 18, "bold"), padx=30, pady=20)
            self.lbl_overlay.pack()
        else:
            self.lbl_overlay.configure(text=text)
        self.overlay.update()

    def hide_overlay(self):
        if self.overlay: self.overlay.destroy(); self.overlay = None

    def start_calibration(self):
        if not self.settings.get("accounts"):
            messagebox.showerror("Fehler", "Bitte erstelle zuerst ein Profil und wähle es aus.")
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Hinweis", "Bitte wähle zuerst ein Profil aus der Liste oben aus, das gestartet werden soll.")
            return
        name = self.tree.item(sel[0])['values'][0]
        account = next((a for a in self.settings["accounts"] if a["name"] == name), None)
        path = account["path"]
        screen_w = self.winfo_screenwidth()
        self.geometry(f"+{screen_w - 920}+50")
        threading.Thread(target=self._run_calibration, args=(path,), daemon=True).start()

    def wait_for_click(self):
        while user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000: time.sleep(0.05)
        while True:
            if user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000: return True
            time.sleep(0.01)

    def get_rel_pos(self, hwnd):
        pt = POINT();
        user32.GetCursorPos(ctypes.byref(pt))
        rect = RECT();
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        return (pt.x - rect.left, pt.y - rect.top)

    def _run_calibration(self, path):
        try:
            self.show_overlay(f"Starte Programm für die Kalibrierung...\nBitte warten, bis es geöffnet ist.")
            try:
                subprocess.Popen([path], cwd=os.path.dirname(path))
            except Exception as e:
                self.hide_overlay()
                messagebox.showerror("Fehler", f"Programm konnte nicht gestartet werden:\n{e}")
                return

            hwnd = 0
            for _ in range(30):
                hwnd = self.find_visible_window(WINDOW_TITLE_LAUNCHER)
                if hwnd: break
                time.sleep(1.0)

            if not hwnd:
                self.hide_overlay()
                messagebox.showerror("Fehler", "Das Fenster wurde nicht rechtzeitig gefunden.")
                return

            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0040)
            user32.SetForegroundWindow(hwnd)
            time.sleep(1.0)

            steps = [
                ("Account-Wechseln Symbol (Zahnrad)", "switch_x", "switch_y"),
                ("E-Mail Eingabefeld", "email_x", "email_y"),
                ("Blauer Weiter-Button", "continue_x", "continue_y"),
                ("Passwort Eingabefeld", "pwd_x", "pwd_y"),
                ("Blauer Einloggen-Button", "login_x", "login_y")
            ]

            for i, (txt, kx, ky) in enumerate(steps):
                self.show_overlay(f"SCHRITT {i + 1}/5:\nKlicke mit der Maus exakt auf das Feld für:\n'{txt}'")
                self.wait_for_click()
                cx, cy = self.get_rel_pos(hwnd)
                self.settings["coords"][kx] = cx;
                self.settings["coords"][ky] = cy
                time.sleep(0.5)

            self.save_config()
            self.show_overlay("WUNDERBAR!\nAlle Positionen wurden gespeichert.")
            time.sleep(2)
            self.hide_overlay()

        except Exception as e:
            self.hide_overlay();
            print(e)

    def find_visible_window(self, title_substring):
        result = []
        def enum_window_callback(hwnd, lParam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    if title_substring.lower() in buff.value.lower(): result.append(hwnd)
            return True
        proc = WNDENUMPROC(enum_window_callback)
        user32.EnumWindows(proc, 0)
        return result[0] if result else 0

    def launch(self):
        s = self.tree.selection()
        if not s: return
        n = self.tree.item(s[0])['values'][0]
        for a in self.settings["accounts"]:
            if a["name"] == n:
                self.show_blocker()
                threading.Thread(target=self._run, args=(a,), daemon=True).start()
                break

    def _run(self, acc):
        self.btn_launch.configure(state="disabled")
        try:
            self.status_bar.configure(text="Status: 1. Entferne alte Sperren...", text_color="orange")
            try:
                handle_cleaner.main()
            except:
                pass
            time.sleep(1)

            path, email, pwd = acc["path"], acc["email"], self.deobscure(acc["password"])
            is_launcher = "launcher" in path.lower() or "battle.net" in path.lower()
            title = WINDOW_TITLE_LAUNCHER if is_launcher else WINDOW_TITLE_GAME
            coords = self.settings.get("coords", {})

            self.status_bar.configure(text=f"Status: 2. Starte Programm...", text_color="#00ccff")
            subprocess.Popen([path], cwd=os.path.dirname(path))

            hwnd = 0;
            retries = 0
            while hwnd == 0 and retries < 60:
                time.sleep(1.0);
                hwnd = self.find_visible_window(title);
                retries += 1

            if hwnd == 0:
                self.status_bar.configure(text="Status: Zeitüberschreitung beim Starten", text_color="red");
                self.btn_launch.configure(state="normal");
                self.after(0, self.close_blocker);
                return

            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0040)
            user32.SetForegroundWindow(hwnd);
            time.sleep(1)

            rect = RECT();
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            win_x, win_y = rect.left, rect.top

            if is_launcher and email:
                sys_hooks.click_at(win_x + coords["switch_x"], win_y + coords["switch_y"]);
                time.sleep(3.0)
                sys_hooks.click_at(win_x + coords["email_x"], win_y + coords["email_y"]);
                time.sleep(0.5)
                sys_hooks.press_key(sys_hooks.SCANCODES['ctrl']);
                sys_hooks.click_key(sys_hooks.SCANCODES['a'])
                sys_hooks.release_key(sys_hooks.SCANCODES['ctrl']);
                sys_hooks.click_key(sys_hooks.SCANCODES['backspace'])
                sys_hooks.type_string(email);
                time.sleep(0.5)

                if coords.get("continue_x", 0) != 0:
                    sys_hooks.click_at(win_x + coords["continue_x"], win_y + coords["continue_y"])
                else:
                    sys_hooks.click_key(sys_hooks.SCANCODES['enter'])

                time.sleep(2.0)
                if coords.get("pwd_x", 0) != 0: sys_hooks.click_at(win_x + coords["pwd_x"], win_y + coords["pwd_y"])
                sys_hooks.type_string(pwd);
                time.sleep(0.5)

                if coords.get("login_x", 0) != 0:
                    sys_hooks.click_at(win_x + coords["login_x"], win_y + coords["login_y"])
                else:
                    sys_hooks.click_key(sys_hooks.SCANCODES['enter'])
                self.status_bar.configure(text="Status: Vorgang erfolgreich abgeschlossen.", text_color="green")
            elif not is_launcher:
                sys_hooks.click_key(sys_hooks.SCANCODES['space']);
                time.sleep(3)
                sys_hooks.type_string(email);
                sys_hooks.click_key(sys_hooks.SCANCODES['tab'])
                sys_hooks.type_string(pwd);
                sys_hooks.click_key(sys_hooks.SCANCODES['enter'])
                time.sleep(5);
                handle_cleaner.main()
                self.status_bar.configure(text="Status: Vorgang erfolgreich abgeschlossen.", text_color="green")
        except Exception as e:
            self.status_bar.configure(text="Status: Ein unerwarteter Fehler ist aufgetreten.", text_color="red");
            print(e)
        self.after(0, self.close_blocker);
        self.btn_launch.configure(state="normal")