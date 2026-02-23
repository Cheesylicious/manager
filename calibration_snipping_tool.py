import customtkinter as ctk
import tkinter as tk
import cv2
import numpy as np
import mss
import os
import sys
from PIL import Image, ImageTk


class CalibrationSnippingTool(ctk.CTkToplevel):
    def __init__(self, parent, step_key, step_name, step_desc, success_callback):
        """
        Ein Vollbild-Overlay für die Kalibrierung.
        Dual-Logik:
        - Zieht der Nutzer einen Bereich, wird ein Bild für Template-Matching gespeichert.
        - Klickt der Nutzer nur, wird präzise ein einzelner Pixel gespeichert.
        """
        super().__init__(parent)
        self.step_key = step_key
        self.step_name = step_name
        self.step_desc = step_desc
        self.success_callback = success_callback

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 1.0)
        self.configure(cursor="crosshair")

        with mss.mss() as sct:
            monitor = sct.monitors[1]
            self.geometry(f"{monitor['width']}x{monitor['height']}+0+0")
            sct_img = sct.grab(monitor)
            self.bg_image_cv = np.array(sct_img)[:, :, :3]

            rgb_image = cv2.cvtColor(self.bg_image_cv, cv2.COLOR_BGR2RGB)
            self.bg_image_pil = Image.fromarray(rgb_image)
            self.bg_image_tk = ImageTk.PhotoImage(self.bg_image_pil)

        self.canvas = tk.Canvas(self, width=monitor["width"], height=monitor["height"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_image(0, 0, image=self.bg_image_tk, anchor="nw")

        instruction_text = f"Kalibrierung: {self.step_name}\n{self.step_desc}\n(Klicken & Ziehen für Bereich, oder nur Klicken. ESC zum Abbrechen)"
        box_width = 800
        center_x = monitor["width"] // 2

        self.canvas.create_rectangle(center_x - box_width // 2, 20, center_x + box_width // 2, 110,
                                     fill="#1a1a1a", outline="#FFD700", width=2)
        self.canvas.create_text(center_x, 65, text=instruction_text, fill="#FFD700",
                                font=("Arial", 14, "bold"), justify="center")

        self.rect = None
        self.start_x = None
        self.start_y = None

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Escape>", lambda e: self.destroy())

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y,
                                                 outline="#00ccff", width=3)

    def on_drag(self, event):
        if self.start_x is None or self.start_y is None:
            return
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        if self.start_x is None or self.start_y is None:
            return

        end_x, end_y = event.x, event.y

        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)

        width = x2 - x1
        height = y2 - y1

        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2

        b, g, r = self.bg_image_cv[center_y, center_x]

        if width > 5 and height > 5:
            # Absolute Pfad-Generierung, damit der Ordner garantiert am richtigen Ort landet!
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))

            folder_path = os.path.join(base_path, "state_templates")
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)

            filename = f"{self.step_key}.png"
            filepath = os.path.join(folder_path, filename)

            # Relativen Pfad für die Config speichern, damit es portabel bleibt
            relative_path = os.path.join("state_templates", filename)

            cropped_img = self.bg_image_cv[y1:y2, x1:x2]
            cv2.imwrite(filepath, cropped_img)

            result_data = {
                "x": int(center_x),
                "y": int(center_y),
                "r": int(r),
                "g": int(g),
                "b": int(b),
                "is_template": True,
                "template_path": relative_path,
                "box": (int(x1), int(y1), int(x2), int(y2))
            }
        else:
            result_data = {
                "x": int(center_x),
                "y": int(center_y),
                "r": int(r),
                "g": int(g),
                "b": int(b),
                "is_template": False
            }

        if self.success_callback:
            self.success_callback(result_data)

        self.start_x = None
        self.start_y = None
        self.destroy()