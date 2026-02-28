import threading
import time
import urllib.request
import json
import urllib.error

# =========================================================
# D2RUNEWIZARD API TOKEN
# https://d2runewizard.com/profile/api
# =========================================================
API_TOKEN = "T41jagcO0UcTLKJiC5UOmDCdGtS2"


class TZFetcher:
    def __init__(self, stop_event, update_interval=60):
        self.update_interval = update_interval
        self.stop_event = stop_event
        self.next_tz = "Lade..."
        self.thread = None
        self.callback = None

    def start(self, callback):
        self.callback = callback
        self.thread = threading.Thread(target=self._fetch_loop, daemon=True)
        self.thread.start()

    def stop(self):
        pass

    def _fetch_loop(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36',
            'D2R-Contact': 'admin@d2r-manager.local',
            'D2R-Platform': 'Desktop Overlay App',
            'D2R-Repo': 'https://github.com/cheesylicious/manager'
        }

        while not self.stop_event.is_set():
            if not API_TOKEN or API_TOKEN == "DEIN_TOKEN_HIER":
                self.next_tz = "API Token fehlt!"
            else:
                try:
                    url = f'https://d2runewizard.com/api/terror-zone?token={API_TOKEN}'
                    req = urllib.request.Request(url, headers=headers)

                    with urllib.request.urlopen(req, timeout=10) as response:
                        data = json.loads(response.read().decode('utf-8'))

                        # LOGIK-ÄNDERUNG: Wir priorisieren jetzt die VORHERSAGE
                        # damit wir nicht auf langsame User-Reports angewiesen sind.

                        zone = ""

                        # 1. Versuche das Feld 'next' (Die nächste geplante Zone laut API)
                        next_obj = data.get('next', {})
                        if next_obj and isinstance(next_obj, dict):
                            zone = next_obj.get('name', '')

                        # 2. Falls 'next' leer ist, schaue in die 'highestProbabilityZone'
                        if not zone:
                            prob_zone = data.get('terrorZone', {}).get('highestProbabilityZone', {})
                            if isinstance(prob_zone, dict):
                                zone = prob_zone.get('zone', '')

                        # 3. Letzter Versuch: Die aktuelle Zone (falls wir wissen wollen, was JETZT ist)
                        if not zone:
                            current_zone = data.get('terrorZone', {}).get('currentZone', '')
                            if current_zone:
                                zone = f"Jetzt: {current_zone}"

                        if zone:
                            # "The " entfernen und Namen kürzen für das Overlay
                            self.next_tz = str(zone).replace("The ", "").strip()
                        else:
                            self.next_tz = "Suche Zone..."

                except Exception:
                    self.next_tz = "Verbindung..."

            if self.callback:
                self.callback({"next": self.next_tz})

            # Kurzes Intervall für schnellere Updates bei Zonenwechsel
            for _ in range(self.update_interval):
                if self.stop_event.is_set(): break
                time.sleep(1)