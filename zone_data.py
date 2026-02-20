# zone_data.py
"""
Dieses Modul enthält die strukturierten Gebietsdaten geordnet nach Akten.
Durch die Auslagerung vermeiden wir einen Monolithen im UI-Code und
sorgen für extrem schnelle Zugriffszeiten im Dropdown-Menü.
"""

ACT_ZONES = {
    "A1": [
        "Lager der Jägerinnen",
        "Blutmoor",
        "Kalte Ebene",
        "Feld der Steine",
        "Dunkelwald",
        "Schwarzmoor",
        "Tamo-Hochland",
        "Klosterpforte",
        "Äußeres Kloster",
        "Gefängnis",
        "Inneres Kloster",
        "Katakomben"
    ],
    "A2": [
        "Lut Gholein",
        "Kanalisation",
        "Felsige Öde",
        "Verdorrte Hügel",
        "Ferne Oase",
        "Vergessene Stadt",
        "Tal der Schlangen",
        "Zuflucht",
        "Schlucht der Magier"
    ],
    "A3": [
        "Kurast-Docks",
        "Spinnenwald",
        "Großes Moor",
        "Schinderdschungel",
        "Unter-Kurast",
        "Basar von Kurast",
        "Ober-Kurast",
        "Travincal",
        "Kerker des Hasses"
    ],
    "A4": [
        "Festung des Wahnsinns",
        "Äußere Steppe",
        "Ebene der Verzweiflung",
        "Stadt der Verdammten",
        "Flammenfluss",
        "Chaos-Sanktarium"
    ],
    "A5": [
        "Harrogath",
        "Blutiges Vorgebirge",
        "Eishochland",
        "Arreat-Hochebene",
        "Kristalldurchgang",
        "Gletscherweg",
        "Gefrorene Tundra",
        "Weg der Urahnen",
        "Weltsteinturm",
        "Thron der Zerstörung"
    ]
}

def get_zones_for_act(act_name: str) -> list:
    """
    Gibt die Liste der Wegpunkte/Gebiete für einen bestimmten Akt zurück.
    Gibt eine leere Liste zurück, falls der Akt nicht gefunden wird.
    """
    return ACT_ZONES.get(act_name, [])