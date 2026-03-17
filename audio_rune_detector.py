import threading
import time
import numpy as np

try:
    import pyaudiowpatch as pyaudio
except ImportError:
    pyaudio = None


class AudioRuneDetector(threading.Thread):
    """
    Ein asynchroner Audio-Listener. Verwendet den spektralen DNA-Abgleich (FFT).
    Liest den Audiostream im sicheren Blockier-Modus, um Buffer-Overflows und Frame-Drops
    im Live-Spiel vollständig auszuschließen.
    """

    def __init__(self, on_rune_detected_callback, config_data=None):
        super().__init__(daemon=True)
        self.callback = on_rune_detected_callback
        self.config_data = config_data or {}
        self.running = False
        self.chunk_size = 2048

        self._load_config()
        self.last_detection = 0

    def _load_config(self):
        self.target_freqs = self.config_data.get("audio_target_freqs", [9500.0])
        if not isinstance(self.target_freqs, list):
            self.target_freqs = [float(self.target_freqs)]

        self.min_energy = self.config_data.get("audio_min_energy", 0.5)
        self.min_ratio = self.config_data.get("audio_min_ratio", 0.20)
        self.target_spk_name = self.config_data.get("audio_output_device_name", "")

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

            # FIX: Auch hier direkter, stotterfreier Blockier-Modus ohne Callback
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
                    # Blockierendes Auslesen (exception_on_overflow=False verhindert Ruckler)
                    in_data = stream.read(self.chunk_size, exception_on_overflow=False)
                    new_data = np.frombuffer(in_data, dtype=np.float32)

                    if channels > 1:
                        new_data = new_data.reshape(-1, channels)
                        new_data = new_data[:, 0]

                    # Buffer weiterschieben (Rolling Window)
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
        fft_result = np.fft.rfft(audio_data)
        frequencies = np.fft.rfftfreq(len(audio_data), 1.0 / samplerate)
        magnitudes = np.abs(fft_result)

        hf_mask = (frequencies >= 4000) & (frequencies <= 16000)
        current_hf_energy = float(np.sum(magnitudes[hf_mask]))

        if current_hf_energy < self.min_energy:
            return

        peak_energy = 0.0
        local_energy = 0.0

        for f in self.target_freqs:
            p_mask = (frequencies >= f - 50) & (frequencies <= f + 50)
            l_mask = (frequencies >= f - 500) & (frequencies <= f + 500)

            peak_energy += float(np.sum(magnitudes[p_mask]))
            local_energy += float(np.sum(magnitudes[l_mask]))

        ratio = peak_energy / local_energy if local_energy > 0 else 0.0

        now = time.time()

        if ratio > self.min_ratio and not np.isnan(ratio) and (now - self.last_detection) > 2.5:
            self.last_detection = now
            self.callback()

    def stop(self):
        self.running = False