"""Pruebas de integración sobre un WebSocket real (comandos petición/respuesta).

Levanta el servidor en un puerto efímero con tira y Spotify falsos, y verifica
el protocolo de comandos que usa el frontend.
"""

from __future__ import annotations

import json

import pytest
import websockets

import servidor
from ajustes import Ajustes, MODO_BRUSCO
from cache_colores import CacheColores

from conftest import TiraFake
from fakes import SpotifyFake, CapturadorFake


@pytest.fixture
async def servidor_ws(tmp_path, monkeypatch):
    """Arranca el servidor con dependencias falsas y devuelve (uri, recursos)."""
    monkeypatch.setattr(servidor, "cargar_config", lambda: {"direccion_mac": "AA:BB:CC"})
    monkeypatch.setattr(servidor, "guardar_config", lambda cfg: None)
    monkeypatch.setattr(servidor, "cargar_config_spotify", lambda *a, **k: {"cliente_id": "x", "cliente_secreto": "y"})

    tira = TiraFake()
    spotify = SpotifyFake()
    monkeypatch.setattr(servidor, "_crear_tira", lambda direccion: tira)
    monkeypatch.setattr(servidor, "_crear_spotify", lambda creds: spotify)

    cache = CacheColores(str(tmp_path / "c.json"))
    ajustes = Ajustes(str(tmp_path / "a.json"))
    monkeypatch.setattr(servidor, "_cache_colores", cache)
    monkeypatch.setattr(servidor, "_ajustes_usuario", ajustes)

    async with websockets.serve(servidor.manejar_cliente, "localhost", 0) as srv:
        puerto = srv.sockets[0].getsockname()[1]
        yield {
            "uri": f"ws://localhost:{puerto}",
            "tira": tira, "spotify": spotify, "cache": cache, "ajustes": ajustes,
        }


async def _recibir_evento(ws, evento, timeout=2.0):
    """Lee mensajes hasta encontrar el evento buscado."""
    import asyncio
    async def _loop():
        while True:
            datos = json.loads(await ws.recv())
            if datos.get("evento") == evento:
                return datos
    return await asyncio.wait_for(_loop(), timeout)


async def test_conexion_y_color(servidor_ws):
    async with websockets.connect(servidor_ws["uri"]) as ws:
        await _recibir_evento(ws, "conectado")
        await ws.send(json.dumps({"comando": "color", "r": 12, "g": 34, "b": 56}))
        ev = await _recibir_evento(ws, "color")
        assert (ev["r"], ev["g"], ev["b"]) == (12, 34, 56)
        assert servidor_ws["tira"].ultimo == (12, 34, 56)


async def test_ping(servidor_ws):
    async with websockets.connect(servidor_ws["uri"]) as ws:
        await _recibir_evento(ws, "conectado")
        await ws.send(json.dumps({"comando": "ping"}))
        assert (await _recibir_evento(ws, "pong"))["ok"] is True


async def test_ajustes_obtener_y_guardar(servidor_ws):
    async with websockets.connect(servidor_ws["uri"]) as ws:
        await _recibir_evento(ws, "conectado")
        await ws.send(json.dumps({"comando": "ajustes_obtener"}))
        ev = await _recibir_evento(ws, "ajustes")
        assert ev["ajustes"]["modo_transicion"] == "gradiente"

        await ws.send(json.dumps({
            "comando": "ajustes_guardar",
            "cambios": {"modo_transicion": MODO_BRUSCO, "duracion_crossfade": 1.0}
        }))
        ev = await _recibir_evento(ws, "ajustes")
        assert ev["ajustes"]["modo_transicion"] == MODO_BRUSCO
        assert ev["ajustes"]["duracion_crossfade"] == 1.0
        # Persistió en el objeto compartido.
        assert servidor_ws["ajustes"].get("modo_transicion") == MODO_BRUSCO


async def test_cache_listar_editar_eliminar(servidor_ws):
    cache = servidor_ws["cache"]
    cache.guardar_auto("s1", 255, 0, 0, "Tema1", "Art1")
    cache.guardar_auto("s2", 0, 255, 0, "Tema2", "Art2")

    async with websockets.connect(servidor_ws["uri"]) as ws:
        await _recibir_evento(ws, "conectado")

        await ws.send(json.dumps({"comando": "cache_listar"}))
        ev = await _recibir_evento(ws, "cache_lista")
        assert len(ev["canciones"]) == 2

        # Editar color de s1 (pasa a fuente usuario).
        await ws.send(json.dumps({"comando": "cache_editar", "cancion_id": "s1", "r": 1, "g": 2, "b": 3}))
        ev = await _recibir_evento(ws, "cache_editado")
        assert (ev["r"], ev["g"], ev["b"]) == (1, 2, 3)
        assert cache.es_de_usuario("s1")

        # Editar una canción inexistente falla.
        await ws.send(json.dumps({"comando": "cache_editar", "cancion_id": "noexiste", "r": 1, "g": 1, "b": 1}))
        datos = json.loads(await ws.recv())
        assert datos["ok"] is False

        # Eliminar s2.
        await ws.send(json.dumps({"comando": "cache_eliminar", "cancion_id": "s2"}))
        ev = await _recibir_evento(ws, "cache_eliminado")
        assert ev["ok"] is True
        assert not cache.existe("s2")


async def test_spotify_estado_incluye_ajustes(servidor_ws):
    async with websockets.connect(servidor_ws["uri"]) as ws:
        await _recibir_evento(ws, "conectado")
        await ws.send(json.dumps({"comando": "spotify_estado"}))
        ev = await _recibir_evento(ws, "spotify_estado")
        assert "ajustes" in ev
        assert ev["tiene_credenciales"] is True


async def test_escanear(servidor_ws, monkeypatch):
    async def fake_scan(tiempo=8):
        return [
            {"nombre": "ELK-BLEDOM", "direccion": "AA:11", "probable_led": True},
            {"nombre": "Auriculares", "direccion": "BB:22", "probable_led": False},
        ]
    monkeypatch.setattr(servidor.TiraLED, "escanear_todos", staticmethod(fake_scan))
    async with websockets.connect(servidor_ws["uri"]) as ws:
        await _recibir_evento(ws, "conectado")
        await ws.send(json.dumps({"comando": "escanear"}))
        ev = await _recibir_evento(ws, "dispositivos")
        assert len(ev["lista"]) == 2
        assert ev["lista"][0]["probable_led"] is True


async def test_conectar_dispositivo(servidor_ws):
    async with websockets.connect(servidor_ws["uri"]) as ws:
        await _recibir_evento(ws, "conectado")
        await ws.send(json.dumps({"comando": "conectar_dispositivo", "direccion": "CC:33:44"}))
        ev = await _recibir_evento(ws, "dispositivo_conectado")
        assert ev["ok"] is True
        assert ev["dispositivo"]["direccion"] == "CC:33:44"
        assert ev["dispositivo"]["conectado"] is True


async def test_conectar_dispositivo_sin_direccion(servidor_ws):
    async with websockets.connect(servidor_ws["uri"]) as ws:
        await _recibir_evento(ws, "conectado")
        await ws.send(json.dumps({"comando": "conectar_dispositivo"}))
        datos = json.loads(await ws.recv())
        assert datos["ok"] is False


async def test_visual_estado_inactivo(servidor_ws):
    async with websockets.connect(servidor_ws["uri"]) as ws:
        await _recibir_evento(ws, "conectado")
        await ws.send(json.dumps({"comando": "visual_estado"}))
        ev = await _recibir_evento(ws, "visual")
        assert ev["activo"] is False
        assert ev["url"].startswith("http://")


async def test_ambilight_monitores(servidor_ws, monkeypatch):
    monkeypatch.setattr(servidor, "listar_monitores", lambda: [{"indice": 0, "nombre": "Todos", "ancho": 1920, "alto": 1080}])
    async with websockets.connect(servidor_ws["uri"]) as ws:
        await _recibir_evento(ws, "conectado")
        await ws.send(json.dumps({"comando": "ambilight_monitores"}))
        ev = await _recibir_evento(ws, "ambilight_monitores")
        assert len(ev["monitores"]) == 1


async def test_ambilight_iniciar_detener(servidor_ws, monkeypatch):
    # Capturador falso y sin capa de audio para un test determinista.
    monkeypatch.setattr(servidor, "CapturadorPantalla", CapturadorFake)
    servidor_ws["ajustes"].set("ambilight_reactivo_audio", False)
    async with websockets.connect(servidor_ws["uri"]) as ws:
        await _recibir_evento(ws, "conectado")
        await ws.send(json.dumps({"comando": "ambilight_iniciar"}))
        await _recibir_evento(ws, "ambilight_activado")
        # Debe emitir color ambiente.
        ev = await _recibir_evento(ws, "ambilight_color")
        assert "r" in ev and "intensidad" in ev
        await ws.send(json.dumps({"comando": "ambilight_detener"}))
        await _recibir_evento(ws, "ambilight_detenido")


async def test_ambilight_config(servidor_ws):
    async with websockets.connect(servidor_ws["uri"]) as ws:
        await _recibir_evento(ws, "conectado")
        await ws.send(json.dumps({"comando": "ambilight_config", "cambios": {"ambilight_saturacion": 2.0, "ambilight_fps": 25}}))
        ev = await _recibir_evento(ws, "ajustes")
        assert ev["ajustes"]["ambilight_saturacion"] == 2.0
        assert ev["ajustes"]["ambilight_fps"] == 25


async def test_comando_desconocido(servidor_ws):
    async with websockets.connect(servidor_ws["uri"]) as ws:
        await _recibir_evento(ws, "conectado")
        await ws.send(json.dumps({"comando": "inventado"}))
        datos = json.loads(await ws.recv())
        assert datos["ok"] is False
        assert "desconocido" in datos["error"].lower()
