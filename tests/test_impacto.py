"""Pruebas del detector de impactos (Cine Mode): golpes fuertes sí, diálogo no."""

from __future__ import annotations

import numpy as np

from dsp_engine_v3 import DetectorImpacto

N = 2049  # bins de un rfft con n_fft=4096
SR = 48000
_FREQS = np.fft.rfftfreq((N - 1) * 2, 1 / SR)
_VOZ = (_FREQS > 250) & (_FREQS <= 4000)


def _asentar(det, mag, n=60):
    for _ in range(n):
        det.analyze(mag, SR)


def test_golpe_fuerte_se_detecta():
    det = DetectorImpacto(SR)
    _asentar(det, np.ones(N) * 2.0)          # fondo tranquilo
    r = det.analyze(np.ones(N) * 400.0, SR)  # golpe broadband
    assert r["es_impacto"] is True
    assert r["fuerza"] > 0.0


def test_sonido_estable_no_dispara():
    # Diálogo/ambiente estable en banda de voz: sin subida brusca => sin impacto.
    det = DetectorImpacto(SR)
    voz = np.zeros(N)
    voz[_VOZ] = 40.0
    ultimo = None
    for _ in range(80):
        ultimo = det.analyze(voz, SR)
    assert ultimo["es_impacto"] is False


def test_broadband_gana_a_voz_misma_intensidad():
    nivel = 30.0
    det_v = DetectorImpacto(SR)
    _asentar(det_v, np.ones(N) * 2.0)
    voz = np.zeros(N)
    voz[_VOZ] = nivel
    r_voz = det_v.analyze(voz, SR)

    det_b = DetectorImpacto(SR)
    _asentar(det_b, np.ones(N) * 2.0)
    r_broad = det_b.analyze(np.ones(N) * nivel, SR)

    assert r_broad["es_impacto"] is True
    assert r_broad["fuerza"] >= r_voz["fuerza"]


def test_sensibilidad_cambia_umbral():
    det = DetectorImpacto(SR)
    det.set_sensibilidad(0.0)
    poco = det.umbral_db
    det.set_sensibilidad(1.0)
    mucho = det.umbral_db
    assert mucho < poco  # más sensible => umbral más bajo


def test_silencio_marca_nivel_bajo():
    det = DetectorImpacto(SR)
    r = None
    for _ in range(30):
        r = det.analyze(np.ones(N) * 0.001, SR)
    assert r["silencio"] is True
