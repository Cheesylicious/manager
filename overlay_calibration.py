import customtkinter as ctk
import time
import threading
import ctypes
import winsound
from PIL import ImageGrab
from overlay_config import STEPS_INFO

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