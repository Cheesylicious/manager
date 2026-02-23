import time
import threading
import sys
import os
import customtkinter as ctk
from overlay_config import TrackerConfig

class RunManagerMixin:
    def toggle_pause(self):
        self.paused = not self.paused
        self.lbl_status.configure(text="⏸️ PAUSIERT" if self.paused else "WARTEN...")

    def reset_current_run(self):
        self.start_time = 0
        self.in_game = False
        self.current_state = "UNKNOWN"
        self.current_run_drops = []
        self.lbl_timer.configure(text="00:00.00")
        self.lbl_live_loot.configure(text="")

    def reset_session(self):
        self.run_history, self.run_count = [], 0
        self.lbl_runs.configure(text="Runs: 0")
        self.lbl_last.configure(text="Letzter: --:--")
        self.lbl_avg.configure(text="Ø --:--")
        if self.xp_watcher:
            self.xp_watcher.session_start_xp = None
            self.xp_watcher.session_start_time = None
        self._update_xp_display(do_scan=False)
        self.reset_current_run()

    # ---- NEUE FUNKTIONEN FÜR DAS EXPANDED MENU ----
    def toggle_autopickup(self):
        """Speichert den Auto-Pickup Zustand sofort live in der Config."""
        self.config_data["auto_pickup"] = self.ap_var.get()
        TrackerConfig.save(self.config_data)

    def open_text_capture(self):
        """Öffnet das Tool zum Anlernen von Runen-Texten auf dem Boden."""
        try:
            from rune_capture_ui import RuneCaptureWindow
            # Callback aktualisiert die Scanner-Templates live nach dem Speichern
            cb = lambda: self.drop_watcher._load_templates() if self.drop_watcher else None
            RuneCaptureWindow(self, cb)
        except Exception as e:
            print(f"Fehler beim Öffnen des Text-Scanners: {e}")

    def open_icon_snipping(self):
        """Öffnet ein Dialogfenster und danach das Vollbild-Snipping-Tool für Inventar-Icons."""
        dialog = ctk.CTkInputDialog(text="Welche Rune möchtest du ausschneiden? (z.B. Ber)", title="Rune wählen")
        rune_name = dialog.get_input()
        if rune_name:
            rune_name = rune_name.strip().capitalize()
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            folder_path = os.path.join(base_path, "runes_inventory")

            try:
                from rune_snipping_tool import RuneSnippingTool
                RuneSnippingTool(self, rune_name, folder_path, self.on_snip_success)
            except Exception as e:
                print(f"Fehler beim Öffnen des Snipping Tools: {e}")
    # -----------------------------------------------

    def toggle_history(self, event=None):
        self.is_expanded = not self.is_expanded
        if self.is_expanded:
            self.btn_toggle_expand.configure(text="▲")
            # Wir geben dem Overlay 310 Pixel statt 250, damit Tools + Historie gut reinpassen
            self.geometry(f"{self.current_width}x{self.current_height + 310}")
            self.expanded_frame.pack(fill="both", expand=True, padx=5, pady=(0, 10), before=self.guardian_frame)
            self.update_history_list()
        else:
            self.btn_toggle_expand.configure(text="▼")
            self.geometry(f"{self.current_width}x{self.current_height}")
            self.expanded_frame.pack_forget()

    def update_history_list(self):
        for w in self.history_frame.winfo_children(): w.destroy()
        recent = self.run_history[-10:]
        recent.reverse()

        for i, run_data in enumerate(recent):
            row = ctk.CTkFrame(self.history_frame, fg_color="transparent")
            row.pack(fill="x", padx=5, pady=2)

            dur = run_data["duration"]
            drops = run_data.get("drops", [])

            ctk.CTkLabel(row, text=f"{len(self.run_history) - i}.", font=("Roboto Mono", 10)).pack(side="left")

            time_lbl = ctk.CTkLabel(row, text=f"{int(dur // 60):02}:{int(dur % 60):02}", font=("Roboto Mono", 10))
            time_lbl.pack(side="right")

            if drops:
                drop_str = " + ".join(drops)
                ctk.CTkLabel(row, text=f"[{drop_str}]", font=("Roboto", 10, "bold"), text_color="#FFD700").pack(
                    side="right", padx=(0, 10))

    def start_tracking(self):
        self.monitoring = True
        self.stop_event.clear()
        if self.drop_watcher: self.drop_watcher.start()
        if self.zone_watcher: self.zone_watcher.start()
        threading.Thread(target=self._logic_loop, daemon=True).start()
        self.update_timer_gui()

    def stop_tracking(self):
        self.monitoring = False
        self.stop_event.set()
        if self.drop_watcher: self.drop_watcher.stop()
        if self.zone_watcher: self.zone_watcher.stop()
        TrackerConfig.save(self.config_data)
        self.destroy()

    def finish_run(self):
        if self.start_time == 0: return
        dur = time.time() - self.start_time

        self.run_history.append({
            "duration": dur,
            "drops": list(self.current_run_drops)
        })

        self.run_count += 1
        self.lbl_runs.configure(text=f"Runs: {self.run_count}")
        self.lbl_last.configure(text=f"Letzter: {int(dur // 60):02}:{int(dur % 60):02}")

        avg = sum(r["duration"] for r in self.run_history) / max(1, self.run_count)
        self.lbl_avg.configure(text=f"Ø {int(avg // 60):02}:{int(avg % 60):02}")

        self._update_xp_display(do_scan=False)

        if self.is_expanded: self.update_history_list()

        self.start_time = 0
        self.current_run_drops = []
        self.lbl_live_loot.configure(text="")

    def _update_xp_display(self, do_scan=True):
        if self.xp_watcher and self.config_data.get("xp_active"):
            try:
                if do_scan:
                    xp, xph = self.xp_watcher.get_current_xp_percent()
                else:
                    xp = getattr(self.xp_watcher, 'current_xp', 0.0)
                    xph = getattr(self.xp_watcher, 'current_xph', "0.0")

                runs = self.xp_watcher.estimate_runs_to_level(self.run_count)
                self.lbl_xp.configure(text=f"EXP: {xp}% | {xph}%/h | RUNS: {runs}")
            except Exception:
                pass

    def update_timer_gui(self):
        if self.monitoring and not self.stop_event.is_set():
            # INNOVATION: Timer wird nur aktualisiert, wenn wir NICHT rausgetabbt sind.
            # Dadurch friert die Zeitanzeige für das Auge perfekt ein!
            if self.in_game and self.start_time > 0 and not self.paused and not getattr(self, "is_tabbed_out", False):
                dur = time.time() - self.start_time
                self.lbl_timer.configure(text=f"{int(dur // 60):02}:{int(dur % 60):02}.{int((dur % 1) * 100):02}")
            self.after(50, self.update_timer_gui)

    def on_drop_detected(self, drop_name):
        if self.in_game and drop_name not in self.current_run_drops:
            self.current_run_drops.append(drop_name)
            drop_str = ", ".join(self.current_run_drops)
            self.lbl_live_loot.configure(text=f"💎 Loot: [{drop_str}]")