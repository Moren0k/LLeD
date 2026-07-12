"""Registro (logging) central de LLeD.

En desarrollo muestra información útil por consola; en la aplicación compilada
(PyInstaller la marca con ``sys.frozen``) solo muestra advertencias y errores,
para no saturar la consola ni afectar el rendimiento. Nunca debe registrarse
algo por cada cambio de color: eso se elimina, no se baja de nivel.

Se puede forzar el modo detallado con la variable de entorno ``LLED_DEBUG``.
"""

import logging
import os
import sys


def _modo_desarrollo() -> bool:
    if os.environ.get("LLED_DEBUG"):
        return True
    return not getattr(sys, "frozen", False)


NIVEL = logging.INFO if _modo_desarrollo() else logging.WARNING

log = logging.getLogger("lled")
if not log.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    log.addHandler(_handler)
    log.propagate = False  # no duplica en el logger raíz
log.setLevel(NIVEL)
