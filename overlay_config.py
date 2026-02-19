import os
import json

TRACKER_CONFIG_FILE = "overlay_config.json"

STEPS_INFO = {
    "char_sel_1": (
        "Charakter-Menü (Punkt 1)",
        "Gehe ins Spiel-Hauptmenü, wo dein Charakter am Lagerfeuer steht.\n\nNICHT KLICKEN! Bewege einfach nur den Mauszeiger ganz unten exakt in die Mitte des Buttons 'Spielen' und warte, bis der Countdown abläuft.",
        5
    ),
    "char_sel_2": (
        "Charakter-Menü (Punkt 2)",
        "Bleibe im Hauptmenü bei deinem Charakter.\n\nNICHT KLICKEN! Wähle als zweiten Punkt etwas absolut Unbewegliches.\nBewege den Mauszeiger auf den massiven, grauen Zierrahmen ganz links oder ganz rechts am Bildschirmrand und warte.",
        5
    ),
    "lobby_1": (
        "Online-Lobby (Punkt 1)",
        "Gehe in die Online-Lobby (falls du Online spielst).\n\nBewege den Mauszeiger dort unten auf den Button 'Spiel erstellen' und warte auf den Piepton.\n(Spielst du nur Offline? Dann klicke hier im Fenster auf 'Überspringen').",
        5
    ),
    "lobby_2": (
        "Online-Lobby (Punkt 2)",
        "Bleibe in der Online-Lobby.\n\nBewege den Mauszeiger auf einen weiteren festen Punkt, zum Beispiel den äußeren goldenen Rahmen des Chat-Fensters, und warte.",
        5
    ),
    "loading_screen": (
        "Ladebildschirm (KLICK-MODUS!)",
        "Achtung, jetzt musst du WÄHREND des Ladens klicken!\n\nDrücke hier auf Start, wechsle ins Spiel und benutze einen Wegpunkt. WÄHREND der Ladebildschirm zu sehen ist (Bild ist komplett schwarz), KLICKE 2 bis 3 Mal schnell hintereinander irgendwo in das Schwarze!\n\nDu hast ab jetzt 8 Sekunden Zeit dafür. Jeder Klick piept!",
        8
    ),
    "game_static": (
        "Spiel-Umgebung (Feste Steinfigur)",
        "Gehe nun RICHTIG ins Spiel hinein, sodass du herumlaufen kannst.\n\nBewege den Mauszeiger unten links auf die graue, steinerne Engels-Statue (die Figur, die die rote Kugel hält). Wichtig: Keine Kugel, kein Feuer, nur der feste graue Stein! Zeigen, warten, NICHT klicken!",
        5
    ),
    "hp_sensor": (
        "Rote Lebenskugel (HP)",
        "Bewege den Mauszeiger direkt in das ROTE deiner Lebenskugel.\n\nHalte die Maus genau auf die Höhe, bei der automatisch ein Heiltrank getrunken werden soll (z.B. bei ca. 30% Füllstand). Nicht klicken!",
        5
    ),
    "mana_sensor": (
        "Blaue Manakugel (MP)",
        "Bewege den Mauszeiger direkt in das BLAUE deiner Manakugel.\n\nHalte die Maus genau auf die Höhe, bei der automatisch ein Manatrank eingeworfen werden soll. Nur zielen, nicht klicken!",
        5
    ),
    "merc_sensor": (
        "Söldner Lebensbalken (1/3 Regel)",
        "Bewege den Mauszeiger oben links auf den Lebensbalken deines Söldners (während er VOLLES Leben hat).\n\nZiele auf ca. 1/3 des Balkens von links. Sobald das Leben unter diesen Punkt fällt (oder der Balken sich an dieser Stelle gelb/rot färbt), wird automatisch ein Trank verabreicht. Nicht klicken!",
        5
    ),
    "xp_start": (
        "Erfahrungsbalken - Start",
        "Wir messen deinen Fortschritt!\n\nBewege den Mauszeiger ganz unten in der Mitte auf den allerersten Pixel (ganz links) deines Erfahrungs-Balkens und warte.",
        5
    ),
    "xp_end": (
        "Erfahrungsbalken - Ende",
        "Fast fertig!\n\nBewege den Mauszeiger nun ganz unten auf das absolute Ende (ganz rechts) deines Erfahrungs-Balkens und warte auf den Piepton.",
        5
    )
}

class TrackerConfig:
    @staticmethod
    def load():
        if os.path.exists(TRACKER_CONFIG_FILE):
            try:
                with open(TRACKER_CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    defaults = {
                        "hp_delay": "0.8", "mana_delay": "0.8", "merc_delay": "0.8",
                        "hp_key": "Aus", "mana_key": "Aus", "merc_key": "Aus",
                        "hp_sound": True, "mana_sound": False, "merc_sound": True, "drop_sound": True,
                        "width": 360, "height": 260, "alpha": 1.0,
                        "drop_alert_active": False, "xp_active": False,
                        "min_rune": "Pul", "clickthrough": False
                    }
                    for k, v in defaults.items():
                        if k not in data: data[k] = v
                    return data
            except:
                pass
        return {
            "alpha": 1.0, "hp_key": "Aus", "mana_key": "Aus", "merc_key": "Aus",
            "hp_delay": "0.8", "mana_delay": "0.8", "merc_delay": "0.8",
            "hp_sound": True, "mana_sound": False, "merc_sound": True, "drop_sound": True,
            "width": 360, "height": 260, "drop_alert_active": False, "xp_active": False,
            "min_rune": "Pul", "clickthrough": False
        }

    @staticmethod
    def save(data):
        try:
            with open(TRACKER_CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except:
            pass