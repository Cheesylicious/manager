import customtkinter as ctk
import threading
import numpy as np
import time
from overlay_config import TrackerConfig

try:
    import sounddevice as sd
except ImportError:
    sd = None


class AudioCaptureWindow(ctk.CTkToplevel):
    def __init__(self, parent, config_data, on_complete_callback=None):
        super().__init__(parent)
        self.parent_app = parent
        self.config_data = config_data
        self.on_complete_callback = on_complete_callback

        self.title("Runen-Sound anlernen")
        self.geometry("450x380")
        self.attributes("-topmost", True)
        self.grab_set()

        self.setup_ui()

    def setup_ui(self):
        self.configure(fg_color="#1a1a1a")

        lbl_title = ctk.CTkLabel(self, text="Audio-Sensor Kalibrierung", font=("Roboto", 16, "bold"),
                                 text_color="#00ccff")
        lbl_title.pack(pady=(15, 5))

        self.lbl_info = ctk.CTkLabel(
            self,
            text="Tipp: Wähle unten 'Stereomix' (PC-Sound) aus.\nFalls es fehlt, in Windows aktivieren:\n(Sound-Systemsteuerung -> Aufnahme -> Deaktivierte anzeigen)",
            font=("Roboto", 11), text_color="#aaaaaa", justify="center"
        )
        self.lbl_info.pack(pady=5)

        self.device_list = []
        self.device_names = []
        if sd is not None:
            try:
                devices = sd.query_devices()
                for idx, d in enumerate(devices):
                    if d['max_input_channels'] > 0:
                        name = f"{d['name']} (ID: {idx})"
                        self.device_list.append(idx)
                        self.device_names.append(name)
            except:
                pass

        if not self.device_names:
            self.device_names = ["Kein Mikrofon gefunden"]

        self.device_var = ctk.StringVar(value=self.device_names[0])

        saved_device = self.config_data.get("audio_input_device_name", "")
        for name in self.device_names:
            if saved_device and saved_device in name:
                self.device_var.set(name)
                break
            elif "stereo" in name.lower() or "mix" in name.lower():
                self.device_var.set(name)

        self.dropdown_device = ctk.CTkOptionMenu(
            self, variable=self.device_var, values=self.device_names, width=300
        )
        self.dropdown_device.pack(pady=10)

        self.btn_start = ctk.CTkButton(self, text="🔴 Aufnahme starten (4 Sek)", height=32,
                                       fg_color="#cf222e", hover_color="#a40e26", font=("Roboto", 12, "bold"),
                                       command=self.start_recording)
        self.btn_start.pack(pady=15)

        self.progress_bar = ctk.CTkProgressBar(self, width=250)
        self.progress_bar.set(0)
        self.progress_bar.pack_forget()

    def start_recording(self):
        if sd is None:
            self.lbl_info.configure(text="Fehler: Python-Modul 'sounddevice' fehlt.", text_color="#cf222e")
            return

        self.btn_start.configure(state="disabled", text="Nimmt auf...")
        self.progress_bar.pack(pady=5)
        self.progress_bar.set(0)

        threading.Thread(target=self._record_and_analyze, daemon=True).start()

    def _record_and_analyze(self):
        samplerate = 44100
        duration = 4.0

        selected_name = self.device_var.get()
        selected_id = None
        if "(ID: " in selected_name:
            try:
                selected_id = int(selected_name.split("(ID: ")[1].replace(")", ""))
            except:
                selected_id = None

        self.after(0, lambda: self.lbl_info.configure(text="Aufnahme läuft... Lasse jetzt eine Rune fallen!",
                                                      text_color="#FFD700"))

        try:
            def update_progress():
                for i in range(40):
                    time.sleep(0.1)
                    if self.winfo_exists():
                        self.after(0, lambda val=i: self.progress_bar.set(val / 40.0))

            threading.Thread(target=update_progress, daemon=True).start()

            recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='float32',
                               device=selected_id)
            sd.wait()
        except Exception as e:
            self.after(0, lambda: self.lbl_info.configure(text=f"Aufnahmefehler: {e}", text_color="#cf222e"))
            self.after(0, lambda: self.btn_start.configure(state="normal", text="🔴 Erneut versuchen"))
            return

        self.after(0, lambda: self.lbl_info.configure(text="Analysiere Energie-Konzentration...", text_color="#aaaaaa"))

        # FIX: Daten bereinigen (verhindert NaN/Inf) und in 64-Bit konvertieren (verhindert Overflow)
        audio_data = np.nan_to_num(recording[:, 0]).astype(np.float64)
        chunk_size = 2048

        best_chunk_mags = None
        max_hf_energy = 0.0
        best_frequencies = None

        for i in range(0, len(audio_data) - chunk_size, chunk_size):
            chunk = audio_data[i:i + chunk_size]
            fft_result = np.fft.rfft(chunk)
            frequencies = np.fft.rfftfreq(len(chunk), 1.0 / samplerate)
            magnitudes = np.abs(fft_result)

            hf_mask = (frequencies >= 4000) & (frequencies <= 16000)
            energy = float(np.sum(magnitudes[hf_mask]))

            if energy > max_hf_energy and not np.isnan(energy) and not np.isinf(energy):
                max_hf_energy = energy
                best_chunk_mags = magnitudes
                best_frequencies = frequencies

        # Ein harter Schwellenwert, um Fehler bei totaler Stille zu verhindern
        if max_hf_energy < 10.0 or best_chunk_mags is None:
            self.after(0, lambda: self.lbl_info.configure(
                text="Kein deutliches Drop-Geräusch erkannt.\nBitte SFX Ingame lauter stellen.", text_color="#cf222e"))
            self.after(0, lambda: self.btn_start.configure(state="normal", text="🔴 Erneut versuchen"))
            self.after(0, lambda: self.progress_bar.pack_forget())
            return

        hf_mask = (best_frequencies >= 4000) & (best_frequencies <= 16000)
        valid_freqs = best_frequencies[hf_mask]
        valid_mags = best_chunk_mags[hf_mask]

        sorted_indices = np.argsort(valid_mags)[::-1]
        top_freqs = []

        for idx in sorted_indices:
            f = float(valid_freqs[idx])
            is_distinct = True
            for picked_f in top_freqs:
                if abs(f - picked_f) < 400:
                    is_distinct = False
                    break
            if is_distinct:
                top_freqs.append(f)
            if len(top_freqs) >= 3:
                break

        peak_mask = np.zeros_like(hf_mask, dtype=bool)
        for f in top_freqs:
            peak_mask |= (best_frequencies >= f - 200) & (best_frequencies <= f + 200)

        peak_energy = float(np.sum(best_chunk_mags[peak_mask & hf_mask]))
        tonality_ratio = peak_energy / max_hf_energy if max_hf_energy > 0 else 0.0

        min_energy = max(10.0, max_hf_energy * 0.20)
        min_ratio = max(0.15, tonality_ratio * 0.45)

        self.config_data["audio_target_freqs"] = top_freqs
        self.config_data["audio_min_energy"] = float(min_energy)
        self.config_data["audio_min_ratio"] = float(min_ratio)
        self.config_data["audio_input_device_name"] = selected_name.split(" (ID:")[
            0] if " (ID:" in selected_name else selected_name
        self.config_data["audio_input_device_id"] = selected_id

        TrackerConfig.save(self.config_data)

        freq_str = ", ".join([f"{int(f)}" for f in top_freqs])
        success_msg = f"Perfekt!\nFrequenzen: [{freq_str}] Hz\nKlarheit (Ratio): {tonality_ratio:.2f} -> Min: {min_ratio:.2f}"

        self.after(0, lambda: self.lbl_info.configure(text=success_msg, text_color="#2da44e"))
        self.after(0, lambda: self.btn_start.configure(state="normal", text="✅ Fertig", fg_color="#2da44e",
                                                       hover_color="#238636", command=self.destroy))
        self.after(0, lambda: self.progress_bar.set(1.0))

        if self.on_complete_callback:
            self.after(0, self.on_complete_callback)