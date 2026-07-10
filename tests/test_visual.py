"""Pruebas del hub del visual remoto (sin abrir sockets reales)."""

from __future__ import annotations

import json

import pytest

import visual_server
from visual_server import VisualHub, _pagina_html, lan_ip, PUERTO_WS


class WSFake:
    """WebSocket simulado que además es async-iterable y se cierra de una."""
    def __init__(self):
        self.enviados = []
    async def send(self, texto):
        self.enviados.append(json.loads(texto))
    def __aiter__(self):
        return self
    async def __anext__(self):
        raise StopAsyncIteration


def test_set_color_actualiza_estado():
    hub = VisualHub()
    hub.set_color(10, 20, 30)
    assert hub.estado["r"] == 10 and hub.estado["g"] == 20 and hub.estado["b"] == 30


def test_set_ritmo_actualiza_estado():
    hub = VisualHub()
    hub.set_ritmo(True)
    assert hub.estado["ritmo"] is True


def test_emitir_sin_clientes_no_falla():
    hub = VisualHub()
    hub.set_color(1, 2, 3)  # sin loop ni clientes: no debe lanzar
    hub.pulse(0.5)


async def test_broadcast_a_clientes():
    hub = VisualHub()
    a, b = WSFake(), WSFake()
    hub._clientes.update({a, b})
    await hub._broadcast({"t": "beat", "e": 0.9})
    assert a.enviados[-1] == {"t": "beat", "e": 0.9}
    assert b.enviados[-1] == {"t": "beat", "e": 0.9}


async def test_handler_envia_estado_inicial():
    hub = VisualHub()
    hub.set_color(5, 6, 7)
    ws = WSFake()
    await hub._handler(ws)
    assert ws.enviados[0]["t"] == "estado"
    assert ws.enviados[0]["r"] == 5


def test_pagina_incluye_puerto_ws():
    html = _pagina_html()
    assert f":{PUERTO_WS}" in html
    assert "__WS_PORT__" not in html


def test_lan_ip_es_cadena():
    ip = lan_ip()
    assert isinstance(ip, str) and ip.count(".") == 3


def test_info():
    hub = VisualHub()
    info = hub.info()
    assert info["activo"] is False
    assert info["url"].startswith("http://")


def test_set_cancion_actualiza_estado():
    hub = VisualHub()
    hub.set_cancion("Tema", "Artista")
    assert hub.estado["cancion"] == "Tema"
    assert hub.estado["artista"] == "Artista"


def test_set_visual_actualiza_estado():
    hub = VisualHub()
    hub.set_visual("orbes", False)
    assert hub.estado["tipo"] == "orbes"
    assert hub.estado["movimiento"] is False


def test_pagina_incluye_motor():
    html = _pagina_html()
    assert "CrearVisual" in html  # el motor quedó inyectado en la página


def test_set_titulo_actualiza_estado():
    hub = VisualHub()
    hub.set_titulo({"titulo": False, "titulo_escala": 2.0, "titulo_x": 0.2, "titulo_y": 0.3})
    assert hub.estado["titulo"] is False
    assert hub.estado["titulo_escala"] == 2.0
    assert hub.estado["titulo_x"] == 0.2


async def test_estado_inicial_incluye_titulo_y_cancion():
    hub = VisualHub()
    hub.set_cancion("X", "Y")
    hub.set_titulo({"titulo_escala": 1.5})
    ws = WSFake()
    await hub._handler(ws)
    estado = ws.enviados[0]
    assert estado["t"] == "estado"
    assert estado["cancion"] == "X"
    assert estado["titulo_escala"] == 1.5
