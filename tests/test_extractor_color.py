"""Pruebas de extracción de color (funciones puras, sin red)."""

from __future__ import annotations

import io

import pytest

from PIL import Image

import extractor_color as ec


def _imagen_bytes(color, tamano=(64, 64)) -> bytes:
    img = Image.new("RGB", tamano, color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def test_rgb_hsv_ida_y_vuelta():
    h, s, v = ec._rgb_a_hsv(255, 0, 0)
    assert round(h) == 0 and round(s, 2) == 1.0 and round(v, 2) == 1.0
    r, g, b = ec._hsv_a_rgb(h, s, v)
    assert (r, g, b) == (255, 0, 0)


def test_hue_a_basico_mapea_rojo():
    # matiz ~0 => rojo puro
    assert ec._hue_a_basico(0, 1.0, 1.0) == (255, 0, 0)


def test_hue_a_basico_gris_claro_es_blanco():
    assert ec._hue_a_basico(0, 0.05, 0.95) == (255, 255, 255)


def test_hue_a_basico_azul():
    assert ec._hue_a_basico(220, 1.0, 1.0) == (0, 0, 255)


def test_color_basico_imagen_roja():
    datos = _imagen_bytes((255, 0, 0))
    assert ec.extraer_color_basico(datos) == (255, 0, 0)


def test_color_basico_imagen_azul():
    datos = _imagen_bytes((0, 0, 255))
    assert ec.extraer_color_basico(datos) == (0, 0, 255)


def test_color_promedio_imagen_solida():
    datos = _imagen_bytes((100, 150, 200))
    r, g, b = ec.extraer_color_promedio(datos)
    assert abs(r - 100) <= 3 and abs(g - 150) <= 3 and abs(b - 200) <= 3


def test_extraer_color_fuerte_satura():
    # Un color apagado debe salir como matiz puro (saturado al máximo).
    datos = _imagen_bytes((120, 60, 60))
    color = ec.extraer_color_fuerte(datos)
    assert color is not None
    # El componente dominante debe ir a 255.
    assert max(color) == 255
