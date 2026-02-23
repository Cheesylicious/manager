import threading
import time
import re

try:
    import cloudscraper
except ImportError:
    cloudscraper = None


class TZFetcher:
    def __init__(self, stop_event, update_interval=300):
        self.update_interval = update_interval
        self.stop_event = stop_event
        self.next_tz_info = "Warte auf Daten..."
        self.thread = None
        self.callback = None
        self.scraper = cloudscraper.create_scraper() if cloudscraper else None

    def start(self, callback):
        self.callback = callback
        self.thread = threading.Thread(target=self._fetch_loop, daemon=True)
        self.thread.start()

    def stop(self):
        pass

    def _fetch_loop(self):
        while not self.stop_event.is_set():
            if not self.scraper:
                self.next_tz_info = "Fehler: cloudscraper Modul fehlt"
                if self.callback: self.callback(self.next_tz_info)
                time.sleep(10)
                continue

            tz_result = None
            try:
                # Wir rufen jetzt die offizielle Tracker-Seite von diablo2.io auf
                # Diese Seite enthält die RotW-Daten ohne harte Verschlüsselung
                response = self.scraper.get('https://diablo2.io/tracker/', timeout=15)

                if response.status_code == 200:
                    tz_result = self._parse_diablo2io(response.text)
            except Exception:
                pass

            # Fallback
            if not tz_result:
                try:
                    resp = self.scraper.get('https://d2runewizard.com/api/terror-zone', timeout=5)
                    if resp.status_code == 200:
                        nxt = resp.json().get('nextTerrorZone', {})
                        tz_result = f"Vanilla: {nxt.get('name') if isinstance(nxt, dict) else nxt}"
                except:
                    pass

            self.next_tz_info = tz_result if tz_result else "Warte auf Update..."

            if self.callback:
                self.callback(self.next_tz_info)

            for _ in range(self.update_interval):
                if self.stop_event.is_set(): break
                time.sleep(1)

    def _parse_diablo2io(self, html):
        """Liest die Terrorzonen direkt aus dem diablo2.io Quellcode."""

        # Suchen nach dem Block, der "Next Terror Zone" beschreibt
        match = re.search(r'Next Terror Zone:.*?class="zone-name[^>]*>([^<]+)</span>', html, re.IGNORECASE | re.DOTALL)

        if match:
            zone = match.group(1).strip()
            # Reinigen von überflüssigen Umbrüchen oder HTML-Resten
            zone = re.sub(r'\s+', ' ', zone)
            if len(zone) > 3:
                return zone

        # Alternative Suche, falls die Struktur leicht abweicht
        alt_match = re.search(r'Upcoming.*?<span class="tz-loc">([^<]+)</span>', html, re.IGNORECASE | re.DOTALL)
        if alt_match:
            return alt_match.group(1).strip()

        return None