import os
import sys

try:
    from rune_snipping_tool import RuneSnippingTool
except ImportError:
    RuneSnippingTool = None


class PendingRunesMixin:
    def add_pending_rune(self, rune_name):
        if rune_name not in self.pending_runes:
            self.pending_runes.append(rune_name)
            self.update_pending_ui()

    def update_pending_ui(self):
        if self.pending_runes:
            # Dropdown-Menü mit kombinierten Optionen aufbauen
            values = ["- Abbrechen -"]
            for rune in self.pending_runes:
                values.append(f"✂️ {rune} ausschneiden")
                values.append(f"❌ {rune} entfernen")

            self.pending_dropdown.configure(values=values)
            self.pending_var.set(f"📸 {len(self.pending_runes)} ausstehend")

            # FIX: Vor dem timer_container packen, da lbl_timer jetzt verschachtelt ist
            if hasattr(self, "timer_container"):
                self.pending_dropdown.pack(pady=(2, 2), before=self.timer_container)
            else:
                self.pending_dropdown.pack(pady=(2, 2), before=self.lbl_timer)
        else:
            self.pending_dropdown.pack_forget()

    def process_selected_pending_rune(self, selection):
        # Setzt die Anzeige sofort wieder auf "X ausstehend" zurück
        self.pending_var.set(f"📸 {len(self.pending_runes)} ausstehend")

        if selection == "- Abbrechen -":
            return

        # Die Auswahl anhand des Leerzeichens aufsplitten, z.B. "❌ Ber entfernen" -> ["❌", "Ber", "entfernen"]
        parts = selection.split(" ")
        if len(parts) < 3:
            return

        action = parts[0]
        rune_name = parts[1]

        # Wenn auf Löschen geklickt wurde:
        if action == "❌":
            if rune_name in self.pending_runes:
                self.pending_runes.remove(rune_name)
            self.update_pending_ui()
            return

        # Wenn auf Ausschneiden geklickt wurde:
        if action == "✂️":
            if RuneSnippingTool is None:
                print("[Tracker] Snipping Tool Modul konnte nicht geladen werden!")
                return

            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))

            folder_path = os.path.join(base_path, "runes_inventory")

            # Startet das Snipping Tool
            RuneSnippingTool(self, rune_name, folder_path, self.on_snip_success)

    def on_snip_success(self, rune_name):
        if rune_name in self.pending_runes:
            self.pending_runes.remove(rune_name)
        self.update_pending_ui()