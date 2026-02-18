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

# Eigene Module
import d2r_unlocker
import d2r_input
from d2r_tutorial import TutorialAssistant

# --- CONFIG & KONSTANTEN ---
CONFIG_FILE = "d2r_accounts.json"
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
class D2RManager(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("D2R Manager | Ultimate Edition")
        self.geometry("900x850")

        self.settings = {
            "first_run": True,
            "accounts": [],
            "coords": {}
        }
        self.load_config()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.create_widgets()
        self.overlay = None
        self.blocker = None

        # Start Tutorial verzögert
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

    # --- UI ---
    def create_widgets(self):
        self.main_frame = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)

        # HEADER
        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        ctk.CTkLabel(self.header_frame, text="DIABLO II RESURRECTED", font=("Roboto Medium", 24, "bold"),
                     text_color="#aaaaaa").pack(anchor="w")
        ctk.CTkLabel(self.header_frame, text="MULTIBOX MANAGER", font=("Roboto Medium", 32, "bold"),
                     text_color="white").pack(anchor="w")

        self.btn_help = ctk.CTkButton(self.header_frame, text="❓ Tutorial", width=80, command=self.start_tutorial,
                                      fg_color="#333333")
        self.btn_help.place(relx=1.0, rely=0.5, anchor="e")

        # LISTE
        self.list_group = ctk.CTkFrame(self.main_frame)
        self.list_group.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        ctk.CTkLabel(self.list_group, text="ACCOUNT ÜBERSICHT", font=("Roboto Medium", 14)).pack(anchor="w", padx=15,
                                                                                                 pady=(15, 5))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", borderwidth=0,
                        rowheight=30, font=("Roboto", 11))
        style.configure("Treeview.Heading", background="#1f1f1f", foreground="white", relief="flat",
                        font=("Roboto", 11, "bold"))
        style.map("Treeview", background=[('selected', '#1f538d')])

        self.tree = ttk.Treeview(self.list_group, columns=("n", "p", "e"), show="headings", height=6)
        self.tree.heading("n", text="Name", anchor="w");
        self.tree.heading("p", text="Pfad / EXE", anchor="w");
        self.tree.heading("e", text="Email", anchor="w")
        self.tree.column("n", width=150);
        self.tree.column("p", width=350);
        self.tree.column("e", width=200)
        self.tree.pack(fill="x", padx=15, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # EDITOR
        self.edit_group = ctk.CTkFrame(self.main_frame)
        self.edit_group.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        ctk.CTkLabel(self.edit_group, text="BEARBEITEN", font=("Roboto Medium", 14)).grid(row=0, column=0, columnspan=3,
                                                                                          sticky="w", padx=15,
                                                                                          pady=(15, 10))

        self.en = ctk.CTkEntry(self.edit_group, placeholder_text="Name (z.B. Main Char)", height=35)
        self.en.grid(row=1, column=0, sticky="ew", padx=15, pady=5)

        self.ee = ctk.CTkEntry(self.edit_group, placeholder_text="Battle.net Email", height=35)
        self.ee.grid(row=1, column=1, sticky="ew", padx=15, pady=5)

        self.ep = ctk.CTkEntry(self.edit_group, placeholder_text="Pfad zur Launcher.exe oder D2R.exe", height=35)
        self.ep.grid(row=2, column=0, columnspan=2, sticky="ew", padx=15, pady=5)

        self.btn_browse = ctk.CTkButton(self.edit_group, text="...", width=40, height=35, command=self.browse,
                                        fg_color="#444444")
        self.btn_browse.grid(row=2, column=2, padx=(0, 15), pady=5)

        self.ew = ctk.CTkEntry(self.edit_group, placeholder_text="Passwort", show="●", height=35)
        self.ew.grid(row=3, column=0, columnspan=2, sticky="ew", padx=15, pady=5)

        self.btn_box = ctk.CTkFrame(self.edit_group, fg_color="transparent")
        self.btn_box.grid(row=4, column=0, columnspan=3, sticky="ew", padx=15, pady=15)

        self.btn_save = ctk.CTkButton(self.btn_box, text="Speichern", command=self.save, fg_color="#2da44e",
                                      hover_color="#2c974b")
        self.btn_save.pack(side="left", padx=(0, 10))

        ctk.CTkButton(self.btn_box, text="Neu / Leeren", command=self.clear, fg_color="transparent", border_width=1,
                      text_color="#aaaaaa").pack(side="left", padx=10)
        ctk.CTkButton(self.btn_box, text="Löschen", command=self.delete, fg_color="#cf222e",
                      hover_color="#a40e26").pack(side="right")
        self.edit_group.grid_columnconfigure(0, weight=1);
        self.edit_group.grid_columnconfigure(1, weight=1)

        # ACTION
        self.action_group = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.action_group.grid(row=3, column=0, sticky="ew", padx=20, pady=10)

        self.btn_calib = ctk.CTkButton(self.action_group, text="🛠️ Launcher Kalibrieren (Wichtig)",
                                       command=self.start_calibration, fg_color="#333333", height=40)
        self.btn_calib.pack(fill="x", pady=5)

        self.btn_launch = ctk.CTkButton(self.action_group, text="▶  START ACCOUNT & UNLOCK", command=self.launch,
                                        font=("Roboto Medium", 16), height=60, fg_color="#1f538d")
        self.btn_launch.pack(fill="x", pady=10)

        ctk.CTkButton(self.action_group, text="Nur Unlocker ausführen (Manuell)", command=self.manual_unlock,
                      fg_color="transparent", text_color="#666666", height=30).pack(fill="x")

        self.status_bar = ctk.CTkLabel(self, text="Bereit.", text_color="#00ccff", font=("Roboto", 12))
        self.status_bar.grid(row=1, column=0, sticky="ew", pady=10)

        self.refresh()

    # --- TUTORIAL START ---
    def start_tutorial(self):
        steps = [
            {
                "title": "🔒 100% SICHER & OFFLINE",
                "text": "Wichtiger Hinweis vorab:\n\nDieses Tool hat KEINEN Internetzugriff. Es funkt nicht 'nach Hause'.\n\nAlle deine Daten (Accounts & Passwörter) werden ausschließlich LOKAL auf deinem PC in der Datei 'd2r_accounts.json' gespeichert. Du hast die volle Kontrolle.",
                "target": None
            },
            {
                "title": "1. Account Anlegen",
                "text": "Gib hier einen Namen (z.B. 'Bo Barb'), deine E-Mail und dein Passwort ein.\n\nDas Passwort wird nur verschleiert gespeichert, damit es nicht direkt lesbar ist.",
                "target": self.en,
                "pos": "right"
            },
            {
                "title": "2. Pfad Auswählen",
                "text": "Wähle hier die 'Battle.net Launcher.exe' aus dem Installationsordner des jeweiligen Accounts.\n\nTipp: Nutze für jeden Account einen eigenen Ordner (Kopie des D2R Ordners).",
                "target": self.btn_browse,
                "pos": "left"
            },
            {
                "title": "3. Speichern",
                "text": "Klicke auf 'Speichern', um den Account zur Liste hinzuzufügen.",
                "target": self.btn_save,
                "pos": "top"
            },
            {
                "title": "4. Kalibrieren (WICHTIG!)",
                "text": "Bevor du startest, klicke EINMALIG hier drauf.\n\nEin Assistent hilft dir, dem Programm zu zeigen, wo die Buttons im Launcher sind.\nDas musst du nur einmal machen!",
                "target": self.btn_calib,
                "pos": "top"
            },
            {
                "title": "5. Starten",
                "text": "Wähle einen Account in der Liste aus und drücke diesen großen Knopf.\n\n⚠️ ACHTUNG: Ein rotes Fenster erscheint. Ab da: Finger weg von Maus & Tastatur! Das Programm übernimmt die Steuerung.",
                "target": self.btn_launch,
                "pos": "top"
            }
        ]
        TutorialAssistant(self, steps)

    def finish_tutorial(self):
        self.settings["first_run"] = False
        self.save_config()

    def manual_unlock(self):
        d2r_unlocker.main()
        self.status_bar.configure(text="Unlocker manuell ausgeführt.", text_color="green")

    # --- STANDARD LOGIC ---
    def browse(self):
        f = filedialog.askopenfilename(filetypes=[("EXE", "*.exe")])
        if f: self.ep.delete(0, tk.END); self.ep.insert(0, f)

    def refresh(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for a in self.settings["accounts"]: self.tree.insert("", "end", values=(a["name"], a["path"], a["email"]))

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
        found = False
        for i, a in enumerate(self.settings["accounts"]):
            if a["name"] == n: self.settings["accounts"][i] = data; found = True; break
        if not found: self.settings["accounts"].append(data)
        self.save_config();
        self.refresh();
        self.status_bar.configure(text=f"Gespeichert: {n}", text_color="green")

    def delete(self):
        n = self.en.get()
        self.settings["accounts"] = [a for a in self.settings["accounts"] if a["name"] != n]
        self.save_config();
        self.refresh();
        self.clear()

    # --- BLOCKER ---
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
        ctk.CTkLabel(self.blocker, text="⚠️ ACHTUNG ⚠️", font=("Roboto", 40, "bold"), text_color="#FFD700",
                     bg_color=bg).pack(pady=(40, 10))
        ctk.CTkLabel(self.blocker, text="AUTOMATISIERUNG LÄUFT", font=("Roboto", 24, "bold"), text_color="white",
                     bg_color=bg).pack(pady=5)
        ctk.CTkLabel(self.blocker, text="Hände weg von Maus & Tastatur!", font=("Roboto", 20), text_color="white",
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

    # --- HUD (KALIBRIERUNG) ---
    def show_overlay(self, text):
        if self.overlay is None or not ctk.CTkToplevel.winfo_exists(self.overlay):
            self.overlay = ctk.CTkToplevel(self)
            self.overlay.overrideredirect(True);
            self.overlay.attributes('-topmost', True)
            self.overlay.geometry("+50+50")

            # ROTER RAHMEN für bessere Sichtbarkeit
            self.overlay_frame = ctk.CTkFrame(self.overlay, fg_color="#2b2b2b", border_width=3, border_color="#FF3333")
            self.overlay_frame.pack(fill="both", expand=True)

            # ROTE SCHRIFT (#FF3333 = Signalrot)
            self.lbl_overlay = ctk.CTkLabel(self.overlay_frame, text=text, text_color="#FF3333",
                                            font=("Roboto", 18, "bold"), padx=30, pady=20)
            self.lbl_overlay.pack()
        else:
            self.lbl_overlay.configure(text=text)
        self.overlay.update()

    def hide_overlay(self):
        if self.overlay: self.overlay.destroy(); self.overlay = None

    # --- CALIBRATION & LAUNCH (SMART) ---
    def start_calibration(self):
        if not self.settings["accounts"]:
            messagebox.showerror("Fehler",
                                 "Keine Accounts gefunden!\n\nBitte erstelle zuerst einen Account und wähle den Pfad zur Battle.net Launcher.exe aus, damit wir wissen, was wir starten sollen.")
            return

        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Auswahl fehlt",
                                   "Welchen Launcher sollen wir kalibrieren?\n\nBitte klicke in der Liste oben auf den Account, dessen Launcher du öffnen möchtest.")
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
            self.show_overlay(f"Starte Launcher für Kalibrierung...\nBitte warten...")
            try:
                subprocess.Popen([path], cwd=os.path.dirname(path))
            except Exception as e:
                self.hide_overlay()
                messagebox.showerror("Start Fehler", f"Konnte Launcher nicht starten:\n{e}")
                return

            hwnd = 0
            for _ in range(30):
                hwnd = self.find_visible_window(WINDOW_TITLE_LAUNCHER)
                if hwnd: break
                time.sleep(1.0)

            if not hwnd:
                self.hide_overlay()
                messagebox.showerror("Timeout", "Launcher Fenster nicht gefunden!\nIst Battle.net richtig gestartet?")
                return

            # --- WINDOW POS FIX: Hart auf 0,0 setzen ---
            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0040)
            user32.SetForegroundWindow(hwnd)
            time.sleep(1.0)

            self.show_overlay("Launcher gefunden! Los geht's.")
            time.sleep(1.0)

            # Updated Steps with instructions to type
            steps = [
                ("Account wechseln", "switch_x", "switch_y"),
                ("E-Mail Feld", "email_x", "email_y"),
                ("Fortfahren (Blau)", "continue_x", "continue_y"),
                ("Passwort Feld", "pwd_x", "pwd_y"),
                ("Einloggen (Blau)", "login_x", "login_y")
            ]

            for i, (txt, kx, ky) in enumerate(steps):
                display_text = f"SCHRITT {i + 1}/5:\nKlicke auf '{txt}'"

                # Special instructions for typing
                if i == 1:  # Email Step
                    display_text += "\n\nWICHTIG: Tippe danach deine E-Mail ein,\ndamit du weiterkommst!"

                if i == 3:  # Password Step
                    self.show_overlay("Warte auf Passwort-Feld...\n(Klicke notfalls selbst 'Fortfahren')")
                    time.sleep(2.0)
                    display_text = f"SCHRITT {i + 1}/5:\nKlicke auf '{txt}'"

                self.show_overlay(display_text)
                self.wait_for_click()
                cx, cy = self.get_rel_pos(hwnd)
                self.settings["coords"][kx] = cx;
                self.settings["coords"][ky] = cy
                print("\a");
                time.sleep(0.5)

            self.save_config()
            self.show_overlay("FERTIG! Positionen gespeichert.")
            time.sleep(2)
            self.hide_overlay()

        except Exception as e:
            self.hide_overlay()
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
            self.status_bar.configure(text="1. Führe Unlock durch...", text_color="orange")
            try:
                d2r_unlocker.main()
            except Exception as ex:
                print(f"Unlocker: {ex}")
            time.sleep(1)

            path = acc["path"];
            email = acc["email"];
            pwd = self.deobscure(acc["password"])
            is_launcher = "launcher" in path.lower() or "battle.net" in path.lower()
            title = WINDOW_TITLE_LAUNCHER if is_launcher else WINDOW_TITLE_GAME
            coords = self.settings.get("coords", {})

            self.status_bar.configure(text=f"2. Starte {title}...", text_color="#00ccff")
            subprocess.Popen([path], cwd=os.path.dirname(path))

            hwnd = 0;
            retries = 0
            while hwnd == 0 and retries < 60:
                time.sleep(1.0);
                hwnd = self.find_visible_window(title);
                retries += 1

            if hwnd == 0:
                self.status_bar.configure(text="Timeout", text_color="red");
                self.btn_launch.configure(state="normal")
                self.after(0, self.close_blocker);
                return

            self.status_bar.configure(text="Login läuft...", text_color="white")
            time.sleep(1)

            # WINDOW POS FIX AUCH HIER
            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0040)
            user32.SetForegroundWindow(hwnd)
            time.sleep(1)

            rect = RECT();
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            win_x = rect.left;
            win_y = rect.top

            if is_launcher and email:
                if coords.get("switch_x", 0) == 0:
                    messagebox.showwarning("Fehler", "Kalibrieren!")
                    self.btn_launch.configure(state="normal");
                    self.after(0, self.close_blocker);
                    return
                d2r_input.click_at(win_x + coords["switch_x"], win_y + coords["switch_y"])
                time.sleep(3.0)
                d2r_input.click_at(win_x + coords["email_x"], win_y + coords["email_y"]);
                time.sleep(0.5)
                d2r_input.press_key(d2r_input.SCANCODES['ctrl']);
                d2r_input.click_key(d2r_input.SCANCODES['a']);
                d2r_input.release_key(d2r_input.SCANCODES['ctrl']);
                d2r_input.click_key(d2r_input.SCANCODES['backspace'])
                d2r_input.type_string(email);
                time.sleep(0.5)
                if coords.get("continue_x", 0) != 0:
                    d2r_input.click_at(win_x + coords["continue_x"], win_y + coords["continue_y"])
                else:
                    d2r_input.click_key(d2r_input.SCANCODES['enter'])
                time.sleep(2.0)
                if coords.get("pwd_x", 0) != 0: d2r_input.click_at(win_x + coords["pwd_x"], win_y + coords["pwd_y"])
                d2r_input.type_string(pwd);
                time.sleep(0.5)
                if coords.get("login_x", 0) != 0:
                    d2r_input.click_at(win_x + coords["login_x"], win_y + coords["login_y"])
                else:
                    d2r_input.click_key(d2r_input.SCANCODES['enter'])
                self.status_bar.configure(text="FERTIG! Bitte PLAY drücken.", text_color="green")
            elif not is_launcher:
                d2r_input.click_key(d2r_input.SCANCODES['space']);
                time.sleep(3)
                d2r_input.type_string(email);
                d2r_input.click_key(d2r_input.SCANCODES['tab'])
                d2r_input.type_string(pwd);
                d2r_input.click_key(d2r_input.SCANCODES['enter'])
                time.sleep(5)
                d2r_unlocker.main()
                self.status_bar.configure(text="FERTIG: Spiel läuft & Unlocked.", text_color="green")
        except Exception as e:
            self.status_bar.configure(text=f"Fehler: {e}", text_color="red");
            print(e)
        self.after(0, self.close_blocker);
        self.btn_launch.configure(state="normal")


if __name__ == "__main__":
    if ctypes.windll.shell32.IsUserAnAdmin():
        app = D2RManager()
        app.mainloop()
    else:
        messagebox.showerror("Admin", "Bitte als Admin starten!")