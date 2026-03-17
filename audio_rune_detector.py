import threading
import time
import numpy as np
import collections
import ctypes

try:
    import pyaudiowpatch as pyaudio
except ImportError:
    pyaudio = None


class AudioRuneDetector(threading.Thread):
    """
    Ein asynchroner Audio-Listener.
    Löst Problem 1: Scannt nur, wenn D2R im Vordergrund ist (ignoriert Discord/Tippen).
    Löst Problem 2: Ignoriert alles unter 1000 Hz, filtert so das Aufheben von Items & Würfel heraus.
    """

    def __init__(self, on_rune_detected_callback, config_data=None):
        super().__init__(daemon=True)
        self.callback = on_rune_detected_callback
        self.config_data = config_data or {}
        self.running = False
        self.chunk_size = 2048

        self.history_len = 15
        self.peak_history = collections.deque(maxlen=self.history_len)
        self.local_history = collections.deque(maxlen=self.history_len)

        self._load_config()
        self.last_detection = 0

    def _load_config(self):
        self.target_freqs = self.config_data.get("audio_target_freqs", [9500.0])
        if not isinstance(self.target_freqs, list):
            self.target_freqs = [float(self.target_freqs)]

        self.min_energy = self.config_data.get("audio_min_energy", 0.05)
        self.min_ratio = self.config_data.get("audio_min_ratio", 0.20)
        self.min_global_ratio = self.config_data.get("audio_min_global_ratio", 0.10)
        self.target_spk_name = self.config_data.get("audio_output_device_name", "")

    def _is_d2r_foreground(self):
        """Prüft, ob Diablo 2 Resurrected gerade das aktive Fenster ist."""
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return False
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return False
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            return "Diablo" in buff.value
        except:
            return False

    def run(self):
        if pyaudio is None:
            print("[Audio-Erkennung] 'pyaudiowpatch' nicht gefunden. Modul deaktiviert.")
            return

        self.running = True
        p = pyaudio.PyAudio()

        try:
            device_idx = None

            for loopback in p.get_loopback_device_info_generator():
                if loopback["name"] == self.target_spk_name:
                    device_idx = loopback["index"]
                    break

            if device_idx is None:
                try:
                    wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
                    default_out = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
                    for loopback in p.get_loopback_device_info_generator():
                        if default_out["name"] in loopback["name"]:
                            device_idx = loopback["index"]
                            break
                except:
                    pass

            if device_idx is None:
                print("[Audio-Erkennung] Fehler: Konnte WASAPI-Loopback nicht finden.")
                return

            device_info = p.get_device_info_by_index(device_idx)
            channels = device_info["maxInputChannels"]
            samplerate = int(device_info["defaultSampleRate"])

            print(f"✅ [Audio-Sensor] Verbunden mit: {device_info['name']}")

            buffer_frames = 4096
            audio_buffer = np.zeros(buffer_frames, dtype=np.float32)

            stream = p.open(format=pyaudio.paFloat32,
                            channels=channels,
                            rate=samplerate,
                            input=True,
                            input_device_index=device_idx,
                            frames_per_buffer=self.chunk_size)

            stream.start_stream()

            while self.running and stream.is_active():
                try:
                    self._load_config()
                    in_data = stream.read(self.chunk_size, exception_on_overflow=False)
                    new_data = np.frombuffer(in_data, dtype=np.float32)

                    if channels > 1:
                        new_data = new_data.reshape(-1, channels)
                        new_data = new_data[:, 0]

                    audio_buffer[:-self.chunk_size] = audio_buffer[self.chunk_size:]
                    audio_buffer[-self.chunk_size:] = new_data

                    if np.max(np.abs(new_data)) > 0.005:
                        self._process_spectral_dna(audio_buffer, samplerate)
                except Exception:
                    pass

            stream.stop_stream()
            stream.close()

        except Exception as e:
            print(f"[Audio-Erkennung] Stream-Fehler: {e}")
        finally:
            p.terminate()

    def _process_spectral_dna(self, audio_data, samplerate):
        # Wenn wir nicht im Spiel sind (z.B. Desktop/Browser), ignorieren wir sämtlichen Ton!
        if not self._is_d2r_foreground():
            return

        fft_result = np.fft.rfft(audio_data)
        frequencies = np.fft.rfftfreq(len(audio_data), 1.0 / samplerate)
        magnitudes = np.abs(fft_result)

        # Fokus strictly auf metallische Töne (1000 Hz bis 12000 Hz),
        # das filtert "Wusch"- und Inventar-Geräusche (meist < 1000 Hz) komplett raus.
        search_mask = (frequencies >= 1000) & (frequencies <= 12000)
        current_target_energy = float(np.sum(magnitudes[search_mask]))

        if current_target_energy < self.min_energy:
            return

        peak_energy = 0.0
        local_energy = 0.0

        for f in self.target_freqs:
            p_mask = (frequencies >= f - 120) & (frequencies <= f + 120)
            l_mask = (frequencies >= f - 600) & (frequencies <= f + 600)

            peak_energy += float(np.sum(magnitudes[p_mask]))
            local_energy += float(np.sum(magnitudes[l_mask]))

        ratio = peak_energy / local_energy if local_energy > 0 else 0.0
        global_ratio = peak_energy / current_target_energy if current_target_energy > 0 else 0.0

        self.peak_history.append(peak_energy)
        self.local_history.append(local_energy)

        is_rune_detected = False

        if ratio >= self.min_ratio and global_ratio >= self.min_global_ratio and not np.isnan(ratio):
            is_rune_detected = True

        # Dynamische Analyse für das Chaos Sanctuary (Kampflärm)
        if len(self.peak_history) >= 5 and not is_rune_detected:
            past_peaks = list(self.peak_history)[:-1]
            past_locals = list(self.local_history)[:-1]

            baseline_peak = np.mean(past_peaks)
            baseline_local = np.mean(past_locals)

            spike_peak = peak_energy / baseline_peak if baseline_peak > 0.01 else 1.0
            spike_local = local_energy / baseline_local if baseline_local > 0.01 else 1.0

            if (spike_peak > 1.8) and (spike_peak > spike_local * 1.5) and global_ratio > (self.min_global_ratio * 0.7):
                is_rune_detected = True

        now = time.time()

        if is_rune_detected and (now - self.last_detection) > 2.5:
            self.last_detection = now
            self.callback()

    def stop(self):
        self.running = False