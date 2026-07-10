"""Pruebas del análisis de Cine Mode (frames sintéticos, sin pantalla real)."""

from __future__ import annotations

import colorsys

import numpy as np

from ambilight import analizar_frame, boost_saturacion, mezclar_ema, CapturadorPantalla


def _frame(color, size=(60, 60)):
    arr = np.zeros((size[0], size[1], 3), dtype=np.uint8)
    arr[:, :] = color
    return arr


def test_frame_rojo():
    info = analizar_frame(_frame((255, 0, 0)))
    assert info["r"] > 200 and info["g"] < 40 and info["b"] < 40
    assert info["drm_negro"] is False
    assert 0.25 < info["luminancia"] < 0.35  # 0.299 para rojo puro


def test_frame_azul():
    info = analizar_frame(_frame((0, 0, 255)))
    assert info["b"] > 200 and info["r"] < 40


def test_frame_negro_marca_drm():
    info = analizar_frame(_frame((0, 0, 0)))
    assert info["drm_negro"] is True
    assert info["luminancia"] < 0.02


def test_luminancia_brillante_vs_oscuro():
    claro = analizar_frame(_frame((255, 255, 255)))
    oscuro = analizar_frame(_frame((20, 20, 20)))
    assert claro["luminancia"] > 0.9
    assert oscuro["luminancia"] < 0.15


def test_bordes_influyen():
    # Centro azul, bordes rojos: con peso_bordes alto debe tirar a rojo.
    arr = _frame((0, 0, 255), (60, 60))
    arr[:10, :] = (255, 0, 0)
    arr[-10:, :] = (255, 0, 0)
    arr[:, :10] = (255, 0, 0)
    arr[:, -10:] = (255, 0, 0)
    info = analizar_frame(arr, peso_bordes=1.0, peso_dominante=0.0)
    assert info["r"] > info["b"]


def test_boost_saturacion_aumenta_s():
    apagado = (150, 120, 120)
    _, s0, _ = colorsys.rgb_to_hsv(*[c / 255 for c in apagado])
    r, g, b = boost_saturacion(apagado, 2.0)
    _, s1, _ = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    assert s1 > s0


def test_mezclar_ema():
    # suavizado alto => se mueve poco hacia el nuevo
    r = mezclar_ema((0, 0, 0), (100, 100, 100), 0.9)
    assert all(0 < c < 30 for c in r)
    # suavizado 0 => salta al nuevo
    assert mezclar_ema((0, 0, 0), (100, 100, 100), 0.0) == (100, 100, 100)


def test_frame_invalido_es_seguro():
    info = analizar_frame(np.zeros((5, 5), dtype=np.uint8))
    assert info["drm_negro"] is True


def test_capturador_configurar():
    cap = CapturadorPantalla(fps=20)
    cap.configurar(fps=30, suavizado=0.8, monitor=1, saturacion=2.0)
    assert cap.fps == 30 and cap.suavizado == 0.8 and cap.monitor == 1
    cap.configurar(fps=1)  # se limita a min 5
    assert cap.fps == 5
