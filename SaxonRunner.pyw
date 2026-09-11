# Avvio con doppio clic senza finestra console (pythonw.exe).
# Il programma vero sta in saxon_runner.py; questo file e' anche il punto
# d'ingresso di PyInstaller.
from saxon_runner import main

if __name__ == "__main__":
    raise SystemExit(main())
