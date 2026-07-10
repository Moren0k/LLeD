"""Pruebas del bucle de sincronización de Spotify (transiciones + cache).

Estas pruebas ejercen ``bucle_sincronizacion`` con una tira, un Spotify y un
WebSocket falsos, sin hardware ni red.
"""

from __future__ import annotations

import asyncio

import pytest

import servidor
from ajustes import Ajustes
from cache_colores import CacheColores
from transiciones import MotorTransiciones

from fakes import SpotifyFake, WebSocketFake, cancion


async def _esperar(condicion, timeout=2.0, intervalo=0.01):
    """Espera hasta que ``condicion()`` sea verdadera o venza el timeout."""
    limite = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < limite:
        if condicion():
            return True
        await asyncio.sleep(intervalo)
    return False


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    """Prepara estado, cache y ajustes rápidos para el bucle de sync."""
    monkeypatch.setattr(servidor, "INTERVALO_VERIFICACION", 0.02)
    cache = CacheColores(str(tmp_path / "c.json"))
    ajustes = Ajustes(str(tmp_path / "a.json"))
    ajustes.actualizar({
        "duracion_crossfade": 0.03,
        "duracion_fade_out": 0.03,
        "duracion_fade_in": 0.03,
        "fps_transicion": 60,
        "intervalo_spotify": 0.03,
    })
    from conftest import TiraFake
    tira = TiraFake()
    motor = MotorTransiciones(tira, fps=60)
    estado = servidor.EstadoLED(tira, motor)
    spotify = SpotifyFake()
    ws = WebSocketFake()
    return {
        "cache": cache, "ajustes": ajustes, "tira": tira,
        "motor": motor, "estado": estado, "spotify": spotify, "ws": ws,
    }


def _lanzar(entorno, modo="portada"):
    return asyncio.create_task(servidor.bucle_sincronizacion(
        entorno["ws"], entorno["estado"], entorno["spotify"],
        entorno["cache"], entorno["ajustes"], lambda: modo,
    ))


async def test_cache_miss_hace_fade_out_y_fade_in(entorno, monkeypatch):
    async def fake_calc(sp, c, modo):
        return (255, 0, 0)
    monkeypatch.setattr(servidor, "calcular_color_cancion", fake_calc)

    tarea = _lanzar(entorno)
    entorno["spotify"].actual = cancion("s1")
    # Esperamos a la notificación, que ocurre DESPUÉS de completar el fade-in.
    ok = await _esperar(lambda: entorno["ws"].ultimo("spotify_color") is not None)
    tarea.cancel()
    assert ok

    tira = entorno["tira"]
    # Debe haber pasado por negro (bajada de brillo) antes de llegar al color.
    assert (0, 0, 0) in tira.enviados
    idx_negro = tira.enviados.index((0, 0, 0))
    assert tira.enviados[-1] == (255, 0, 0)
    assert tira.enviados.index((255, 0, 0)) > idx_negro
    # Notificó el color con fuente automática.
    ev = entorno["ws"].ultimo("spotify_color")
    assert ev and ev["fuente"] == "auto" and (ev["r"], ev["g"], ev["b"]) == (255, 0, 0)


async def test_cache_hit_es_transicion_directa_sin_negro(entorno, monkeypatch):
    colores = {"s1": (255, 0, 0), "s2": (0, 0, 255)}

    async def fake_calc(sp, c, modo):
        return colores.get(c["cancion_id"])
    monkeypatch.setattr(servidor, "calcular_color_cancion", fake_calc)

    tarea = _lanzar(entorno)
    sp = entorno["spotify"]

    # s1 (miss) -> se cachea
    sp.actual = cancion("s1")
    await _esperar(lambda: entorno["cache"].existe("s1"))
    # s2 (miss) -> cambia de canción
    sp.actual = cancion("s2")
    await _esperar(lambda: entorno["cache"].existe("s2"))

    # Volvemos a s1: ahora es HIT.
    entorno["tira"].enviados.clear()
    sp.actual = cancion("s1")
    ok = await _esperar(
        lambda: any(e.get("fuente") == "cache" for e in entorno["ws"].eventos("spotify_color"))
    )
    tarea.cancel()
    assert ok
    # En un HIT no debe apagarse a negro: va directo al color.
    assert (0, 0, 0) not in entorno["tira"].enviados
    assert entorno["tira"].enviados[-1] == (255, 0, 0)


async def test_modo_brusco_no_interpola(entorno, monkeypatch):
    entorno["ajustes"].set("modo_transicion", "brusco")

    async def fake_calc(sp, c, modo):
        return (10, 200, 30)
    monkeypatch.setattr(servidor, "calcular_color_cancion", fake_calc)

    tarea = _lanzar(entorno)
    entorno["spotify"].actual = cancion("s1")
    await _esperar(lambda: entorno["cache"].existe("s1"))
    tarea.cancel()

    # Sin gradiente: no baja a negro y aplica el color de una.
    assert (0, 0, 0) not in entorno["tira"].enviados
    assert entorno["tira"].enviados[-1] == (10, 200, 30)


async def test_color_de_usuario_tiene_prioridad_en_hit(entorno, monkeypatch):
    async def fake_calc(sp, c, modo):
        return (255, 0, 0)
    monkeypatch.setattr(servidor, "calcular_color_cancion", fake_calc)

    # El usuario ya fijó un color para s1.
    entorno["cache"].guardar_usuario("s1", 0, 255, 0, "Tema", "Artista")

    tarea = _lanzar(entorno)
    entorno["spotify"].actual = cancion("s1")
    ok = await _esperar(
        lambda: entorno["ws"].ultimo("spotify_color") is not None
    )
    tarea.cancel()
    assert ok
    ev = entorno["ws"].ultimo("spotify_color")
    assert (ev["r"], ev["g"], ev["b"]) == (0, 255, 0)
    assert ev["fuente"] == "usuario"


async def test_color_none_no_cachea_y_no_rompe(entorno, monkeypatch):
    async def fake_calc(sp, c, modo):
        return None
    monkeypatch.setattr(servidor, "calcular_color_cancion", fake_calc)

    tarea = _lanzar(entorno)
    entorno["spotify"].actual = cancion("s1")
    # Le damos tiempo a procesar unos ciclos.
    await asyncio.sleep(0.2)
    tarea.cancel()
    assert not entorno["cache"].existe("s1")


async def test_cambio_de_cancion_a_ninguna_resetea(entorno, monkeypatch):
    async def fake_calc(sp, c, modo):
        return (1, 2, 3)
    monkeypatch.setattr(servidor, "calcular_color_cancion", fake_calc)

    tarea = _lanzar(entorno)
    sp = entorno["spotify"]
    sp.actual = cancion("s1")
    await _esperar(lambda: entorno["estado"].cancion_actual_id == "s1")
    sp.actual = None
    ok = await _esperar(lambda: entorno["estado"].cancion_actual_id is None)
    tarea.cancel()
    assert ok
