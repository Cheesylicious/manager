class FalseAlarmLearner:
    """
    Nimmt Fehlalarme auf, lernt den neuen Item-Namen und kommuniziert
    mit der Datenbank und der UI.
    """

    def __init__(self, db_manager, ui_updater_callback=None):
        self.db_manager = db_manager
        self.ui_updater_callback = ui_updater_callback

    def register_new_item(self, user_input_name, image_context=None):
        """
        Wird aufgerufen, wenn der Nutzer im Eingabefeld einen Namen für den Fehlalarm eingibt.
        image_context kann in Zukunft genutzt werden, um KI-Modelle nachzutrainieren.
        """
        if not user_input_name or user_input_name.strip() == "":
            return False

        clean_name = user_input_name.strip()

        # In die Datenbank und den RAM-Cache aufnehmen (standardmäßig Auto-Loot an)
        self.db_manager.add_learned_item(clean_name, auto_loot=True)

        # Wenn eine UI verbunden ist, liste sofort aktualisieren
        if self.ui_updater_callback:
            self.ui_updater_callback()

        return True