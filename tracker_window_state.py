import time
import ctypes
import tkinter as tk
import customtkinter as ctk
import winsound
from overlay_config import TrackerConfig

class WindowStateMixin:
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
        except Exception:
            pass

    def change_alpha(self, v):
        self.attributes('-alpha', v)
        self.config_data["alpha"] = v

        for child in self.winfo_children():
            if isinstance(child, tk.Toplevel) or isinstance(child, ctk.CTkToplevel):
                try:
                    child.attributes('-alpha', v)
                except:
                    pass

    def start_move(self, e):
        self.x, self.y = e.x, e.y

    def do_move(self, e):
        self.geometry(f"+{self.winfo_x() + (e.x - self.x)}+{self.winfo_y() + (e.y - self.y)}")

    def show_context_menu(self, e):
        self.context_menu.tk_popup(e.x_root, e.y_root)

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