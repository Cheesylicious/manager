import re
import datetime

try:
    import cloudscraper
except ImportError:
    cloudscraper = None


class D2EmuParser:
    def __init__(self, log_file="tracker_log.txt"):
        self.log_file = log_file
        self.scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
        ) if cloudscraper else None

    def log(self, message):
        """Schreibt ressourcenschonend Logs im Hintergrund."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")
        except:
            pass

    def get_next_zone(self):
        if not self.scraper:
            self.log("Fehler: cloudscraper fehlt.")
            return "pip install cloudscraper"

        self.log("Scanne d2emu nach versteckten RotW-Arrays...")
        html = self._fetch_html('https://www.d2emu.com/tz')

        if not html:
            return "Netzwerkfehler"

        # 1. Bruteforce-Suche nach versteckten RotW-Daten im gesamten Quelltext
        rotw_zone = self._bruteforce_rotw(html)
        if rotw_zone:
            return rotw_zone

        # 2. Fallback-Kennzeichnung, wenn nur Vanilla gefunden wird
        self.log("RotW-Zonen nicht im Basis-HTML. Lade Standard-API...")
        rw_zone = self._fetch_runewizard()
        if rw_zone:
            self.log(f"Standard-Zone gefunden: {rw_zone}")
            return f"Vanilla: {rw_zone}"

        return None

    def _fetch_html(self, url):
        try:
            resp = self.scraper.get(url, timeout=15)
            if resp.status_code == 200:
                return resp.text
        except Exception as e:
            self.log(f"HTTP Fehler: {e}")
        return None

    def _bruteforce_rotw(self, html):
        """Durchsucht das Dokument nach alternativen Zonen-Arrays für RotW."""
        # Wir isolieren absolut alle JS-Arrays, die nach Zonen aussehen
        matches = re.findall(r"\[((?:['\"][a-zA-Z\s,]+['\"](?:,\s*)?)+)\]", html)

        rotw_keywords = ["Dry Hills", "Halls of the Dead", "Crypt", "Mausoleum"]

        for m in matches:
            if any(k in m for k in rotw_keywords):
                clean_elements = re.findall(r"['\"]([^'\"]+)['\"]", m)
                clean_list = [c.replace('\\x20', ' ').strip() for c in clean_elements]

                self.log(f"Verstecktes RotW Array gefunden: {clean_list}")
                if len(clean_list) > 1:
                    return clean_list[1]
                elif clean_list:
                    return clean_list[0]

        self.log("Keine RotW-spezifischen Zonen im HTML gefunden.")
        return None

    def _fetch_runewizard(self):
        try:
            resp = self.scraper.get('https://d2runewizard.com/api/terror-zone', timeout=5)
            if resp.status_code == 200:
                nxt = resp.json().get('nextTerrorZone', {})
                return nxt.get('name') if isinstance(nxt, dict) else nxt
        except:
            pass
        return None