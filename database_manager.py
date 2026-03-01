import sqlite3
import threading

class ItemDatabaseManager:
    """
    Verwaltet die angelernten Items.
    Nutzt einen In-Memory-Cache, um Datenbankwartezeiten während des Trackings zu eliminieren.
    """
    def __init__(self, db_path="learned_items.db"):
        self.db_path = db_path
        self._cache = {}
        self._lock = threading.Lock()
        self._init_db()
        self.load_cache()

    def _init_db(self):
        """Erstellt die Tabelle, falls sie noch nicht existiert."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    auto_loot BOOLEAN DEFAULT 1
                )
            ''')

    def load_cache(self):
        """Lädt alle Items in den RAM für sofortigen O(1) Zugriff."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT name, auto_loot FROM items")
                self._cache = {row[0]: bool(row[1]) for row in cursor.fetchall()}

    def add_learned_item(self, name, auto_loot=True):
        """Fügt ein neues Item in die DB und den Cache ein."""
        with self._lock:
            if name not in self._cache:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "INSERT INTO items (name, auto_loot) VALUES (?, ?)",
                        (name, int(auto_loot))
                    )
                self._cache[name] = auto_loot

    def update_loot_status(self, name, auto_loot):
        """Aktualisiert den Loot-Status per Checkbox in der UI."""
        with self._lock:
            if name in self._cache:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "UPDATE items SET auto_loot = ? WHERE name = ?",
                        (int(auto_loot), name)
                    )
                self._cache[name] = auto_loot

    def get_auto_loot_items(self):
        """
        WICHTIG: Diese Funktion wird vom Tracker aufgerufen.
        Greift nur auf den RAM-Cache zu -> Keine Datenbankwartezeit, keine Ruckler.
        """
        with self._lock:
            return {name for name, is_looted in self._cache.items() if is_looted}