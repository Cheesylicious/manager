import customtkinter as ctk


class TutorialAssistant(ctk.CTkToplevel):
    def __init__(self, parent, steps):
        super().__init__(parent)
        self.parent = parent
        self.steps = steps
        self.current_step = 0

        # Fenster-Setup
        self.overrideredirect(True)
        self.attributes('-topmost', True)

        # Windows Transparency Hack
        chroma_key = "#000001"
        self.configure(fg_color=chroma_key)
        try:
            self.attributes("-transparentcolor", chroma_key)
        except:
            self.configure(fg_color="#222222")

        # Hauptcontainer
        self.container = ctk.CTkFrame(self, fg_color="#2b2b2b", border_width=2, border_color="#FFD700",
                                      corner_radius=10)
        self.container.pack(fill="both", expand=True, padx=10, pady=10)

        self.container.grid_columnconfigure(1, weight=1)

        # Inhalt - JETZT MIT ROTER SCHRIFT BEIM TITEL
        self.lbl_title = ctk.CTkLabel(self.container, text="Titel", font=("Segoe UI", 18, "bold"), text_color="#FF3333",
                                      anchor="w")
        self.lbl_text = ctk.CTkLabel(self.container, text="Text", font=("Segoe UI", 14), text_color="#dddddd",
                                     wraplength=350, justify="left", anchor="w")

        # Navigation
        self.btn_next = ctk.CTkButton(self.container, text="Weiter", width=100, height=30, fg_color="#007acc",
                                      hover_color="#005f9e", command=self.next_step)
        self.btn_skip = ctk.CTkButton(self.container, text="Beenden", width=80, height=30, fg_color="transparent",
                                      border_width=1, text_color="#aaaaaa", hover_color="#444444",
                                      command=self.close_tutorial)

        # Pfeile
        self.arrow_labels = {
            "left": ctk.CTkLabel(self, text="◄", font=("Arial", 32, "bold"), text_color="#FFD700",
                                 fg_color="transparent"),
            "right": ctk.CTkLabel(self, text="►", font=("Arial", 32, "bold"), text_color="#FFD700",
                                  fg_color="transparent"),
            "top": ctk.CTkLabel(self, text="▲", font=("Arial", 32, "bold"), text_color="#FFD700",
                                fg_color="transparent"),
            "bottom": ctk.CTkLabel(self, text="▼", font=("Arial", 32, "bold"), text_color="#FFD700",
                                   fg_color="transparent")
        }

        # Start
        self.after(100, self.show_step)

    def highlight_widget(self, widget):
        if widget:
            try:
                self.original_border = widget._border_color
                self.original_width = widget._border_width
                widget.configure(border_color="#FFD700", border_width=3)
                self.highlighted_widget = widget
            except:
                pass

    def clear_highlight(self):
        if hasattr(self, 'highlighted_widget') and self.highlighted_widget:
            try:
                self.highlighted_widget.configure(border_color=self.original_border, border_width=self.original_width)
            except:
                pass
            self.highlighted_widget = None

    def show_step(self):
        self.clear_highlight()

        for arrow in self.arrow_labels.values():
            arrow.place_forget()

        for widget in self.container.winfo_children():
            widget.grid_forget()

        if self.current_step < len(self.steps):
            step = self.steps[self.current_step]

            # Inhalt setzen
            self.lbl_title.configure(text=step['title'])
            self.lbl_text.configure(text=step['text'])

            if self.current_step == len(self.steps) - 1:
                self.btn_next.configure(text="Verstanden ✅", fg_color="#2e7d32")
            else:
                self.btn_next.configure(text="Weiter", fg_color="#007acc")

            # Layout aufbauen
            self.lbl_title.grid(row=0, column=0, columnspan=2, padx=20, pady=(15, 5), sticky="w")
            self.lbl_text.grid(row=1, column=0, columnspan=2, padx=20, pady=5, sticky="nw")
            self.btn_next.grid(row=2, column=1, padx=20, pady=15, sticky="e")
            self.btn_skip.grid(row=2, column=0, padx=20, pady=15, sticky="w")

            self.update_idletasks()
            req_w = self.container.winfo_reqwidth() + 40
            req_h = self.container.winfo_reqheight() + 40

            if "target" in step and step["target"]:
                self.place_smart(step["target"], req_w, req_h, step.get("pos", "right"))
            else:
                self.center_screen(req_w, req_h)

        else:
            self.close_tutorial()

    def place_smart(self, target, w, h, pref_pos):
        self.highlight_widget(target)

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()

        tx = target.winfo_rootx()
        ty = target.winfo_rooty()
        tw = target.winfo_width()
        th = target.winfo_height()

        x, y = 0, 0
        final_pos = pref_pos

        if pref_pos == "right":
            if tx + tw + w + 20 < sw:
                x = tx + tw + 15
                y = ty + (th // 2) - (h // 2)
                final_pos = "left"
            else:
                x = tx - w - 15
                y = ty + (th // 2) - (h // 2)
                final_pos = "right"

        elif pref_pos == "left":
            if tx - w - 20 > 0:
                x = tx - w - 15
                y = ty + (th // 2) - (h // 2)
                final_pos = "right"
            else:
                x = tx + tw + 15
                y = ty + (th // 2) - (h // 2)
                final_pos = "left"

        elif pref_pos == "bottom":
            if ty + th + h + 20 < sh:
                x = tx + (tw // 2) - (w // 2)
                y = ty + th + 15
                final_pos = "top"
            else:
                x = tx + (tw // 2) - (w // 2)
                y = ty - h - 15
                final_pos = "bottom"

        elif pref_pos == "top":
            if ty - h - 20 > 0:
                x = tx + (tw // 2) - (w // 2)
                y = ty - h - 15
                final_pos = "bottom"
            else:
                x = tx + (tw // 2) - (w // 2)
                y = ty + th + 15
                final_pos = "top"

        if x < 10: x = 10
        if y < 10: y = 10
        if x + w > sw: x = sw - w - 10
        if y + h > sh: y = sh - h - 10

        self.geometry(f"{w}x{h}+{x}+{y}")

        arrow = self.arrow_labels[final_pos]
        arrow.lift()

        if final_pos == "left":
            arrow.place(relx=0.0, rely=0.5, anchor="e", x=12)
        elif final_pos == "right":
            arrow.place(relx=1.0, rely=0.5, anchor="w", x=-12)
        elif final_pos == "top":
            arrow.place(relx=0.5, rely=0.0, anchor="s", y=12)
        elif final_pos == "bottom":
            arrow.place(relx=0.5, rely=1.0, anchor="n", y=-12)

    def center_screen(self, w, h):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def next_step(self):
        self.current_step += 1
        self.show_step()

    def close_tutorial(self):
        self.clear_highlight()
        if hasattr(self.parent, 'finish_tutorial'):
            self.parent.finish_tutorial()
        self.destroy()