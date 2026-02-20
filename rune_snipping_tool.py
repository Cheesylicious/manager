import customtkinter as ctk
import tkinter as tk
import cv2
import numpy as np
import mss
import os
from PIL import Image, ImageTk


class RuneSnippingTool(ctk.CTkToplevel):
    def __init__(self, parent, rune_name, folder_path, success_callback):
        """
        Ein Vollbild-Overlay, das den aktuellen Bildschirm einfriert,
        damit der Nutzer das Runen-Icon mit der Maus wie in einem Snipping Tool ausschneiden kann.
        """
        super().__init__(parent)
        self.rune_name = rune_name
        self.folder_path = folder_path
        self.success_callback = success_callback

        # Fenster als rahmenloses Vollbild-Overlay konfigurieren
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 1.0)
        self.configure(cursor="crosshair")

        # Mache sofort einen Screenshot vom aktuellen Bildschirmzustand
        with mss.mss() as sct:
            monitor = sct.monitors[1]  # Primärer Monitor
            self.geometry(f"{monitor['width']}x{monitor['height']}+0+0")
            sct_img = sct.grab(monitor)
            self.bg_image_cv = np.array(sct_img)[:, :, :3]

            # Konvertiere das Bild für das Tkinter Canvas
            rgb_image = cv2.cvtColor(self.bg_image_cv, cv2.COLOR_BGR2RGB)
            self.bg_image_pil = Image.fromarray(rgb_image)
            self.bg_image_tk = ImageTk.PhotoImage(self.bg_image_pil)

        # Canvas für das Standbild und zum Zeichnen des Rechtecks
        self.canvas = tk.Canvas(self, width=monitor["width"], height=monitor["height"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_image(0, 0, image=self.bg_image_tk, anchor="nw")

        # UI-Hinweis für den Nutzer einblenden
        instruction_text = f"Markiere das Icon für: {self.rune_name}\n(Klicken & Ziehen. ESC zum Abbrechen)"
        box_width = 400
        center_x = monitor["width"] // 2

        # Hintergrundbox für Text
        self.canvas.create_rectangle(center_x - box_width // 2, 20, center_x + box_width // 2, 90,
                                     fill="#1a1a1a", outline="#FFD700", width=2)
        self.canvas.create_text(center_x, 55, text=instruction_text, fill="#FFD700",
                                font=("Arial", 14, "bold"), justify="center")

        # Variablen initialisieren (wichtig gegen NoneType Error)
        self.rect = None
        self.start_x = None
        self.start_y = None

        # Mauseingaben binden
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Escape>", lambda e: self.destroy())

    def on_press(self, event):
        """Startpunkt für das Ausschneiden setzen."""
        self.start_x = event.x
        self.start_y = event.y
        if self.rect:
            self.canvas.delete(self.rect)
        # Erstelle ein winziges Rechteck als visuelles Feedback
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y,
                                                 outline="#2da44e", width=3)

    def on_drag(self, event):
        """Rechteck während der Mausbewegung aktualisieren."""
        if self.start_x is None or self.start_y is None:
            return

        cur_x, cur_y = event.x, event.y
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_release(self, event):
        """Ausschneiden und Speichern bei Loslassen der Maustaste."""
        # Sicherheitscheck: Falls on_press nicht korrekt getriggert wurde
        if self.start_x is None or self.start_y is None:
            return

        end_x, end_y = event.x, event.y

        # Koordinaten ordnen, damit auch "rückwärts" ziehen funktioniert
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)

        # Verhindern, dass zu kleine Bereiche (Versehentliche Klicks) gespeichert werden
        if (x2 - x1) > 5 and (y2 - y1) > 5:
            cropped_img = self.bg_image_cv[y1:y2, x1:x2]
            self.save_snip(cropped_img)
        else:
            if self.rect:
                self.canvas.delete(self.rect)

        # Variablen zurücksetzen für den nächsten Versuch
        self.start_x = None
        self.start_y = None

    def save_snip(self, cropped_img):
        """Speichert den markierten Bereich."""
        if not os.path.exists(self.folder_path):
            try:
                os.makedirs(self.folder_path)
            except:
                pass

        filename = f"{self.rune_name.lower()}.png"
        save_path = os.path.join(self.folder_path, filename)

        try:
            # Speicherung als Graustufen für den Inventar-Scanner
            gray_img = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2GRAY)
            cv2.imwrite(save_path, gray_img)

            if self.success_callback:
                self.success_callback(self.rune_name)
        except Exception as e:
            print(f"[RuneSnippingTool] Fehler beim Speichern: {e}")

        self.destroy()