import customtkinter as ctk
import threading
import numpy as np
import time
import wave
import os
import sys
from overlay_config import TrackerConfig

# --- HOTFIX FÜR NUMPY 2.0+ KOMPATIBILITÄT ---
_original_fromstring = np.fromstring


def _compat_fromstring(string, dtype=float, count=-1, sep=''):
    if sep == '':
        return np.frombuffer(string, dtype=dtype, count=count)
    return _original_fromstring(string, dtype=dtype, count=count, sep=sep)


np.fromstring = _compat_fromstring
# --------------------------------------------

try:
    import pyaudiowpatch as pyaudio
except ImportError:
    pyaudio = None


class AudioCaptureWindow(ctk.CTkToplevel):
    def __init__(self, parent, config_data, on_complete_callback=None):
        super().__init__(parent)
        self.parent_app = parent
        self.config_data = config_data
        self.on_complete_callback = on_complete_callback

        self.title("Runen-Sound anlernen")
        self.geometry("420x390")
        self.attributes("-topmost", True)
        self.grab_set()

        self.setup_ui()

    def setup_ui(self):
        self.configure(fg_color="#1a1a1a")

        lbl_title = ctk.CTkLabel(self, text="Audio Fingerabdruck Scanner", font=("Roboto", 16, "bold"),
                                 text_color="#00ccff")
        lbl_title.pack(pady=(15, 5))

        self.lbl_info = ctk.CTkLabel(
            self,
            text="Wähle unten dein Ingame-Audiogerät aus.\nLasse eine Rune fallen. Das Tool filtert dumpfe UI-\nGeräusche heraus und extrahiert den reinen Ring.",
            font=("Roboto", 11), text_color="#aaaaaa", justify="center"
        )
        self.lbl_info.pack(pady=5)

        self.device_names = []
        self.device_mapping = {}

        if pyaudio is not None:
            p = pyaudio.PyAudio()
            try:
                for loopback in p.get_loopback_device_info_generator():
                    name = loopback["name"]
                    self.device_names.append(name)
                    self.device_mapping[name] = loopback["index"]
            except Exception as e:
                print(f"Fehler bei Gerätesuche: {e}")
            finally:
                p.terminate()

        if not self.device_names:
            self.device_names = ["Kein Loopback-Gerät gefunden"]

        self.device_var = ctk.StringVar(value=self.device_names[0])

        saved_device = self.config_data.get("audio_output_device_name", "")
        if saved_device in self.device_names:
            self.device_var.set(saved_device)

        self.dropdown_device = ctk.CTkOptionMenu(
            self, variable=self.device_var, values=self.device_names, width=350
        )
        self.dropdown_device.pack(pady=10)

        # NEU: Kontrollkästchen zum Ein-/Ausschalten des Alarms
        self.enable_var = ctk.BooleanVar(value=self.config_data.get("audio_popup_enabled", True))
        self.chk_enable = ctk.CTkCheckBox(
            self, text="Audio-Alarm im Spiel aktivieren",
            variable=self.enable_var,
            command=self._toggle_audio_alarm,
            text_color="#00ccff",
            font=("Roboto", 12, "bold")
        )
        self.chk_enable.pack(pady=(5, 15))

        self.btn_start = ctk.CTkButton(self, text="🔴 Aufnahme starten (4 Sek)", height=32,
                                       fg_color="#cf222e", hover_color="#a40e26", font=("Roboto", 12, "bold"),
                                       command=self.start_recording)
        self.btn_start.pack(pady=5)

        self.progress_bar = ctk.CTkProgressBar(self, width=250)
        self.progress_bar.set(0)
        self.progress_bar.pack_forget()

        self.lbl_vol = ctk.CTkLabel(self, text="Live-Pegel:", font=("Roboto", 10), text_color="#888888")
        self.lbl_vol.pack_forget()

        self.vol_bar = ctk.CTkProgressBar(self, width=250, progress_color="#555555")
        self.vol_bar.set(0)
        self.vol_bar.pack_forget()

    def _toggle_audio_alarm(self):
        self.config_data["audio_popup_enabled"] = self.enable_var.get()
        TrackerConfig.save(self.config_data)

    def start_recording(self):
        if pyaudio is None:
            self.lbl_info.configure(text="Fehler: Modul 'pyaudiowpatch' fehlt.", text_color="#cf222e")
            return

        self.btn_start.configure(state="disabled", text="Nimmt auf...")
        self.progress_bar.pack(pady=5)
        self.progress_bar.set(0)

        self.lbl_vol.pack(pady=(5, 0))
        self.vol_bar.pack(pady=(0, 5))
        self.vol_bar.set(0)

        threading.Thread(target=self._record_and_analyze, daemon=True).start()

    def _update_bars(self, progress, vol):
        self.progress_bar.set(progress)
        self.vol_bar.set(vol)
        if vol > 0.02:
            self.vol_bar.configure(progress_color="#2da44e")
        else:
            self.vol_bar.configure(progress_color="#555555")

    def _save_wav(self, filename, audio_data, samplerate):
        try:
            clipped = np.clip(audio_data, -1.0, 1.0)
            scaled = (clipped * 32767).astype(np.int16)

            base_path = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(
                os.path.abspath(__file__))
            filepath = os.path.join(base_path, filename)

            with wave.open(filepath, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(samplerate)
                wf.writeframes(scaled.tobytes())

        except Exception as e:
            print(f"❌ [Audio-Sensor] Fehler beim Speichern der WAV: {e}")

    def _record_and_analyze(self):
        duration = 4.0
        selected_spk_name = self.device_var.get()

        if selected_spk_name not in self.device_mapping:
            self.after(0, lambda: self.lbl_info.configure(text="Ungültiges Gerät.", text_color="#cf222e"))
            self.after(0, lambda: self.btn_start.configure(state="normal", text="🔴 Erneut versuchen"))
            return

        device_idx = self.device_mapping[selected_spk_name]
        self.after(0, lambda: self.lbl_info.configure(text="🔴 Aufnahme läuft... Lasse jetzt die Rune fallen!",
                                                      text_color="#FFD700"))

        p = pyaudio.PyAudio()
        try:
            device_info = p.get_device_info_by_index(device_idx)
            channels = device_info["maxInputChannels"]
            samplerate = int(device_info["defaultSampleRate"])

            chunk_size = 2048
            total_chunks = int((samplerate / chunk_size) * duration)
            frames = []

            stream = p.open(format=pyaudio.paFloat32,
                            channels=channels,
                            rate=samplerate,
                            input=True,
                            input_device_index=device_idx,
                            frames_per_buffer=chunk_size)

            stream.start_stream()

            for i in range(total_chunks):
                data = stream.read(chunk_size, exception_on_overflow=False)
                frames.append(data)

                audio_np = np.frombuffer(data, dtype=np.float32)
                vol = float(np.max(np.abs(audio_np))) if len(audio_np) > 0 else 0.0
                progress = (i + 1) / total_chunks

                if self.winfo_exists():
                    self.after(0, lambda p=progress, v=min(1.0, vol * 3.0): self._update_bars(p, v))

            stream.stop_stream()
            stream.close()

            raw_bytes = b''.join(frames)
            recording = np.frombuffer(raw_bytes, dtype=np.float32)

        except Exception as e:
            self.after(0, lambda: self.lbl_info.configure(text=f"Aufnahmefehler: {e}", text_color="#cf222e"))
            self.after(0, lambda: self.btn_start.configure(state="normal", text="🔴 Erneut versuchen"))
            return
        finally:
            p.terminate()

        self.after(0, lambda: self.lbl_info.configure(text="Lese DNA aus Audio-Schablone...", text_color="#aaaaaa"))

        if channels > 1:
            recording = recording.reshape(-1, channels)
            audio_data = recording[:, 0]
        else:
            audio_data = recording

        self._save_wav("letzte_aufnahme_test.wav", audio_data, samplerate)

        window_size = 4096
        step_size = 2048

        best_chunk_mags = None
        max_target_energy = 0.0
        best_frequencies = None

        for i in range(0, len(audio_data) - window_size, step_size):
            chunk = audio_data[i:i + window_size]
            if len(chunk) < window_size:
                break

            fft_result = np.fft.rfft(chunk)
            frequencies = np.fft.rfftfreq(len(chunk), 1.0 / samplerate)
            magnitudes = np.abs(fft_result)

            search_mask = (frequencies >= 1000) & (frequencies <= 12000)
            energy = float(np.sum(magnitudes[search_mask]))

            if energy > max_target_energy and not np.isnan(energy) and not np.isinf(energy):
                max_target_energy = energy
                best_chunk_mags = magnitudes
                best_frequencies = frequencies

        if max_target_energy < 0.1 or best_chunk_mags is None:
            self.after(0, lambda: self.lbl_info.configure(text="Stille! Blockiert Windows das Desktop-Audio?",
                                                          text_color="#cf222e"))
            self.after(0, lambda: self.btn_start.configure(state="normal", text="🔴 Erneut versuchen"))
            return

        search_mask = (best_frequencies >= 1000) & (best_frequencies <= 12000)
        valid_freqs = best_frequencies[search_mask]
        valid_mags = best_chunk_mags[search_mask]

        sorted_indices = np.argsort(valid_mags)[::-1]
        top_freqs = []
        for idx in sorted_indices:
            f = float(valid_freqs[idx])
            if all(abs(f - picked_f) > 200 for picked_f in top_freqs):
                top_freqs.append(f)
            if len(top_freqs) >= 3:
                break

        peak_energy = 0.0
        local_energy = 0.0
        for f in top_freqs:
            p_mask = (best_frequencies >= f - 50) & (best_frequencies <= f + 50)
            l_mask = (best_frequencies >= f - 500) & (best_frequencies <= f + 500)
            peak_energy += float(np.sum(best_chunk_mags[p_mask]))
            local_energy += float(np.sum(best_chunk_mags[l_mask]))

        tonality_ratio = peak_energy / local_energy if local_energy > 0 else 0.0

        total_target_energy = float(np.sum(best_chunk_mags[search_mask]))
        global_ratio = peak_energy / total_target_energy if total_target_energy > 0 else 0.0

        min_energy = max(0.1, max_target_energy * 0.08)
        min_ratio = max(0.20, tonality_ratio * 0.45)
        min_global_ratio = max(0.10, global_ratio * 0.35)

        self.config_data["audio_target_freqs"] = top_freqs
        self.config_data["audio_min_energy"] = float(min_energy)
        self.config_data["audio_min_ratio"] = float(min_ratio)
        self.config_data["audio_min_global_ratio"] = float(min_global_ratio)
        self.config_data["audio_output_device_name"] = selected_spk_name
        TrackerConfig.save(self.config_data)

        freq_str = ", ".join([f"{int(f)}" for f in top_freqs])
        success_msg = f"DNA extrahiert (Präzisions-Modus)!\nFreq: [{freq_str}] Hz"

        self.after(0, lambda: self.lbl_info.configure(text=success_msg, text_color="#2da44e"))
        self.after(0, lambda: self.btn_start.configure(state="normal", text="✅ Fertig", fg_color="#2da44e",
                                                       hover_color="#238636", command=self.destroy))

        if self.on_complete_callback:
            self.after(0, self.on_complete_callback)