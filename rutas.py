"""Resolución central de rutas para desarrollo y para el binario congelado.

Distingue dos tipos de ubicación:

- **Recursos de solo lectura** (p. ej. ``motor_visual.js``): viajan dentro del
  paquete. Congelado con PyInstaller están en ``sys._MEIPASS``; en desarrollo,
  junto al código.
- **Datos escribibles** (``config.json``, ``ajustes.json``, ``color_cache.json``,
  ``.spotify_cache``): NO pueden vivir en la carpeta de instalación (Program
  Files es de solo lectura). Van a una carpeta del usuario.

Prioridad de la carpeta de datos:
  1. Variable de entorno ``LLED_DATA_DIR`` (la fija Electron con
     ``app.getPath('userData')``) → coherente con instalación/desinstalación.
  2. Si el backend está congelado: ``%APPDATA%/LLeD``.
  3. En desarrollo: la carpeta del proyecto (igual que siempre; no rompe los
     tests, que además pasan sus propias rutas temporales).
"""

from __future__ import annotations

import os
import sys

_DIR_PROYECTO = os.path.dirname(os.path.abspath(__file__))


def es_congelado() -> bool:
    """True si corre dentro de un binario PyInstaller."""
    return bool(getattr(sys, "frozen", False))


def dir_recursos() -> str:
    """Carpeta de recursos de solo lectura empaquetados."""
    if es_congelado():
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return _DIR_PROYECTO


def dir_datos() -> str:
    """Carpeta escribible para config/cache/ajustes. Se crea si no existe."""
    env = os.environ.get("LLED_DATA_DIR")
    if env:
        destino = env
    elif es_congelado():
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        destino = os.path.join(base, "LLeD")
    else:
        destino = _DIR_PROYECTO

    try:
        os.makedirs(destino, exist_ok=True)
    except OSError:
        destino = _DIR_PROYECTO
    return destino


def ruta_datos(nombre: str) -> str:
    """Ruta absoluta de un archivo escribible dentro de la carpeta de datos."""
    return os.path.join(dir_datos(), nombre)


def ruta_recurso(nombre: str) -> str:
    """Ruta absoluta de un recurso de solo lectura empaquetado."""
    return os.path.join(dir_recursos(), nombre)
