"""
Punto de entrada de DVD Saito.

Doble clic al ejecutable o `python main.py` abre la app con la pantalla de
arranque. Para saltarla, se puede crear la ventana con Saito(intro=False).
"""

from saito.app import Saito


if __name__ == "__main__":
    Saito(intro=True).mainloop()
