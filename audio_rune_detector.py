import threading
import time
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sd = None


class AudioRuneDetector(threading.Thread):
    """
    Ein asynchroner Audio-Listener, der nach dem spezifischen Frequenzmuster
    von Runen-Drops sucht. Enthält jetzt absolute Fehler-Toleranz gegen NaN/Inf-Werte
    und Stille-Ausreißer.
    """

    def __init__(self, on_rune_detected_callback, config_data=None):
        super().__init__(daemon=True)
        self.callback = on_rune_detected_callback
        self.config_data = config_data or {}
        self.running = False
        self.samplerate = 44100
        self.chunk_size = 2048

        self._load_config()
        self.last_detection = 0

    def _load_config(self):
        self.target_freqs = self.config_data.get("audio_target_freqs", [9500.0])
        if not isinstance(self.target_freqs, list):
            self.target_freqs = [float(self.target_freqs)]

        self.min_energy = self.config_data.get("audio_min_energy", 10.0)
        self.min_ratio = self.config_data.get("audio_min_ratio", 0.25)
        self.device_id = self.config_data.get("audio_input_device_id", None)

    def run(self):
        if sd is None:
            print("[Audio-Erkennung] 'sounddevice' nicht gefunden. Modul deaktiviert.")
            return

        self.running = True
        try:
            with sd.InputStream(samplerate=self.samplerate, channels=1,
                                blocksize=self.chunk_size, device=self.device_id, callback=self._audio_callback):
                while self.running:
                    self._load_config()
                    time.sleep(0.5)
        except Exception as e:
            print(f"[Audio-Erkennung] Fehler beim Starten des Audio-Streams: {e}")

    def _audio_callback(self, indata, frames, time_info, status):
        if not self.running:
            raise sd.CallbackStop()

        # FIX: Eingangsdaten zwingend bereinigen (ersetzt NaN/Inf durch 0) und in Float64 wandeln
        audio_data = np.nan_to_num(indata[:, 0]).astype(np.float64)

        # Überspringe den kompletten Chunk, wenn er absolut leer/kaputt ist
        if np.max(np.abs(audio_data)) == 0.0:
            return

        fft_result = np.fft.rfft(audio_data)
        frequencies = np.fft.rfftfreq(len(audio_data), 1.0 / self.samplerate)
        magnitudes = np.abs(fft_result)

        hf_mask = (frequencies >= 4000) & (frequencies <= 16000)
        hf_energy = float(np.sum(magnitudes[hf_mask]))

        # FIX: Harte Blockade gegen Stille-Rauschen (max-Vergleich)
        # Stellt sicher, dass das Audiosignal stark genug ist und keine fehlerhaften Werte aufweist.
        if hf_energy > max(self.min_energy, 10.0) and not np.isnan(hf_energy) and not np.isinf(hf_energy):
            peak_mask = np.zeros_like(hf_mask, dtype=bool)
            for f in self.target_freqs:
                peak_mask |= (frequencies >= f - 200) & (frequencies <= f + 200)

            peak_energy = float(np.sum(magnitudes[peak_mask & hf_mask]))
            ratio = peak_energy / hf_energy

            now = time.time()
            if ratio > self.min_ratio and not np.isnan(ratio) and (now - self.last_detection) > 2.5:
                self.last_detection = now
                self.callback()

    def stop(self):
        self.running = False