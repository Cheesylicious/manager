import sys
import ctypes
import os
import subprocess
from tkinter import messagebox


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_as_admin():
    """Startet das Skript mit Admin-Rechten neu."""
    script = os.path.abspath(sys.argv[0])
    params = ' '.join([script] + sys.argv[1:])
    try:
        # ShellExecute führt den "runas" Verb aus, was den UAC-Dialog triggert
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    except Exception as e:
        messagebox.showerror("Fehler", f"Konnte Admin-Rechte nicht anfordern:\n{e}")
    sys.exit()


def main():
    # 1. Admin-Check
    if not is_admin():
        run_as_admin()
        return

    # 2. Abhängigkeiten prüfen
    try:
        import customtkinter
        import PIL
    except ImportError as e:
        messagebox.showerror("Fehler",
                             f"Fehlende Module:\n{e}\n\nBitte installiere: pip install customtkinter pillow pypiwin32")
        return

    # 3. Hauptanwendung starten (Neue generische Namen)
    try:
        from core_ui import MainManager

        app = MainManager()
        app.mainloop()

    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(error_msg)
        messagebox.showerror("Kritischer Fehler", f"Die Anwendung ist abgestürzt:\n\n{e}")


if __name__ == "__main__":
    main()