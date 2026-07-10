"""Pruebas del módulo de rutas (dev vs env var)."""

from __future__ import annotations

import os
import importlib


def test_dir_datos_usa_env(monkeypatch, tmp_path):
    destino = str(tmp_path / "datos")
    monkeypatch.setenv("LLED_DATA_DIR", destino)
    import rutas
    importlib.reload(rutas)
    assert rutas.dir_datos() == destino
    assert os.path.isdir(destino)
    assert rutas.ruta_datos("config.json") == os.path.join(destino, "config.json")


def test_dir_datos_dev_es_proyecto(monkeypatch):
    monkeypatch.delenv("LLED_DATA_DIR", raising=False)
    import rutas
    importlib.reload(rutas)
    # En desarrollo (no congelado, sin env) es la carpeta del proyecto.
    assert rutas.dir_datos() == rutas._DIR_PROYECTO
    assert rutas.es_congelado() is False


def test_ruta_recurso(monkeypatch):
    monkeypatch.delenv("LLED_DATA_DIR", raising=False)
    import rutas
    importlib.reload(rutas)
    assert rutas.ruta_recurso("motor_visual.js").endswith("motor_visual.js")
