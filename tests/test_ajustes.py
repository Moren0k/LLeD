"""Pruebas del sistema de ajustes/preferencias."""

from __future__ import annotations

import pytest

from ajustes import Ajustes, DEFAULTS, MODO_BRUSCO, MODO_GRADIENTE


@pytest.fixture
def ruta(tmp_path):
    return str(tmp_path / "ajustes.json")


def test_defaults(ruta):
    a = Ajustes(ruta)
    assert a.get("modo_transicion") == MODO_GRADIENTE
    assert a.to_dict() == DEFAULTS
    assert a.es_gradiente is True


def test_set_y_persistencia(ruta):
    a = Ajustes(ruta)
    a.set("modo_transicion", MODO_BRUSCO)
    assert a.get("modo_transicion") == MODO_BRUSCO
    a2 = Ajustes(ruta)
    assert a2.get("modo_transicion") == MODO_BRUSCO
    assert a2.es_gradiente is False


def test_modo_invalido_cae_a_default(ruta):
    a = Ajustes(ruta)
    resultado = a.set("modo_transicion", "arcoiris")
    assert resultado == MODO_GRADIENTE


def test_duracion_se_limita(ruta):
    a = Ajustes(ruta)
    assert a.set("duracion_crossfade", 999) == 5.0
    assert a.set("duracion_crossfade", -3) == 0.0
    assert a.set("duracion_crossfade", "no numero") == DEFAULTS["duracion_crossfade"]


def test_fps_se_limita(ruta):
    a = Ajustes(ruta)
    assert a.set("fps_transicion", 5000) == 60
    assert a.set("fps_transicion", 1) == 5


def test_clave_desconocida_se_ignora(ruta):
    a = Ajustes(ruta)
    assert a.set("clave_inventada", 123) is None
    assert "clave_inventada" not in a.to_dict()


def test_actualizar_varios(ruta):
    a = Ajustes(ruta)
    resultado = a.actualizar({
        "modo_transicion": MODO_BRUSCO,
        "duracion_fade_in": 1.2,
        "ignorame": "x",
    })
    assert resultado["modo_transicion"] == MODO_BRUSCO
    assert resultado["duracion_fade_in"] == 1.2
    assert "ignorame" not in resultado


def test_archivo_corrupto_usa_defaults(ruta):
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("no soy json")
    a = Ajustes(ruta)
    assert a.to_dict() == DEFAULTS


def test_sync_modo_validado(ruta):
    a = Ajustes(ruta)
    assert a.set("sync_modo", "humor") == "humor"
    assert a.set("sync_modo", "loquesea") == "portada"


def test_visual_tipo_validado(ruta):
    a = Ajustes(ruta)
    assert a.set("visual_tipo", "orbes") == "orbes"
    assert a.set("visual_tipo", "inexistente") == "aurora"


def test_visual_movimiento_bool(ruta):
    a = Ajustes(ruta)
    assert a.set("visual_movimiento", False) is False
    assert a.set("visual_movimiento", 1) is True
