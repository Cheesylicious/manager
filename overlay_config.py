import os
import json

TRACKER_CONFIG_FILE = "overlay_config.json"

STEPS_INFO = {
    "char_sel_1": (
        "Charakter-Menü (Punkt 1)",
        "Gehe ins Spiel-Hauptmenü, wo dein Charakter am Lagerfeuer steht.\n\nZiehe mit der Maus einen kleinen Rahmen (wie beim Snipping Tool) um einen markanten Teil des Buttons 'Spielen' & 'Lobby', um ihn als Bildausschnitt zu speichern.",
        5
    ),
    "char_sel_2": (
        "Charakter-Menü (Punkt 2)",
        "Bleibe im Hauptmenü bei deinem Charakter.\n\nWähle als zweiten Punkt etwas absolut Unbewegliches.\nSchneide ein markantes Stück wie unten rechts wo man einen Char erstellt und löscht aus.",
        5
    ),
    "lobby_1": (
        "Online-Lobby (Punkt 1)",
        "Gehe in die Online-Lobby (falls du Online spielst).\n\nSchneide dort unten einen Teil des Juweils großflächig aus.\n(Spielst du nur Offline? Dann klicke auf 'Überspringen').",
        5
    ),
    "lobby_2": (
        "Online-Lobby (Punkt 2)",
        "Bleibe in der Online-Lobby.\n\nSchneide einen weiteren festen Punkt aus, zum Beispiel ein Stück vom goldenen Rahmen des Chat-Fensters.",
        5
    ),
    "loading_screen": (
        "Ladebildschirm - WÜRDE ICH ERST MAL ÜBERSPRINGEN",
        "Achtung, jetzt musst du WÄHREND des Ladens den Bildschirm abgreifen!\n\nWechsle ins Spiel und benutze einen Wegpunkt. WÄHREND der Ladebildschirm zu sehen ist (Bild ist komplett schwarz), klicke einmal irgendwo in das Schwarze (hier reicht ein Klick).",
        8
    ),
    "game_static": (
        "Spiel-Umgebung (Feste Steinfigur)",
        "Gehe nun RICHTIG ins Spiel hinein, sodass du herumlaufen kannst.\n\nSchneide unten links einen kleinen Bereich der grauen, steinernen Engels-Statue aus. Wichtig: Keine Kugel, kein Feuer, nur den festen grauen Stein markieren!",
        5
    ),
    "hp_sensor": (
        "Rote Lebenskugel (HP)",
        "Bewege den Mauszeiger direkt in das ROTE deiner Lebenskugel.\n\nKlicke genau auf die Höhe, bei der automatisch ein Heiltrank getrunken werden soll (z.B. bei ca. 30% Füllstand).",
        5
    ),
    "mana_sensor": (
        "Blaue Manakugel (MP)",
        "Bewege den Mauszeiger direkt in das BLAUE deiner Manakugel.\n\nKlicke genau auf die Höhe, bei der automatisch ein Manatrank eingeworfen werden soll.",
        5
    ),
    "merc_sensor": (
        "Söldner Lebensbalken (1/3 Regel)",
        "Bewege den Mauszeiger oben links auf den Lebensbalken deines Söldners (während er VOLLES Leben hat).\n\nKlicke auf ca. 1/3 des Balkens von links. Sobald das Leben unter diesen Punkt fällt, wird ein Trank verabreicht.",
        5
    ),
    "xp_start": (
        "Erfahrungsbalken - Start",
        "Wir messen deinen Fortschritt!\n\nKlicke ganz unten in der Mitte auf den allerersten Pixel (ganz links) deines Erfahrungs-Balkens.",
        5
    ),
    "xp_end": (
        "Erfahrungsbalken - Ende",
        "Fast fertig!\n\nKlicke nun ganz unten auf das absolute Ende (ganz rechts) deines Erfahrungs-Balkens.",
        5
    )
}


class TrackerConfig:
    @staticmethod
    def load():
        all_runes = [
            "El", "Eld", "Tir", "Nef", "Eth", "Ith", "Tal", "Ral", "Ort", "Thul", "Amn", "Sol", "Shael", "Dol", "Hel",
            "Io", "Lum", "Ko", "Fal", "Lem", "Pul", "Um", "Mal", "Ist", "Gul", "Vex", "Ohm", "Lo", "Sur", "Ber",
            "Jah", "Cham", "Zod"
        ]

        if os.path.exists(TRACKER_CONFIG_FILE):
            try:
                with open(TRACKER_CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    defaults = {
                        "hp_delay": "0.8", "mana_delay": "0.8", "merc_delay": "0.8",
                        "hp_key": "Aus", "mana_key": "Aus", "merc_key": "Aus",
                        "hp_sound": True, "mana_sound": False, "merc_sound": True, "drop_sound": True,
                        "width": 360, "height": 260, "alpha": 1.0,
                        "drop_alert_active": False, "auto_pickup": False,
                        "pickup_delay_min": 150, "pickup_delay_max": 350,
                        "xp_active": False, "clickthrough": False,
                        "allowed_runes": all_runes
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
            "width": 360, "height": 260, "drop_alert_active": False, "auto_pickup": False,
            "pickup_delay_min": 150, "pickup_delay_max": 350,
            "xp_active": False, "clickthrough": False,
            "allowed_runes": all_runes
        }

    @staticmethod
    def save(data):
        try:
            with open(TRACKER_CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except:
            pass