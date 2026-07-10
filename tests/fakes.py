"""Dobles de prueba (fakes) para Spotify y WebSocket."""

from __future__ import annotations

import json
from typing import Optional


class SpotifyFake:
    """Cliente de Spotify simulado. El test controla ``actual`` a mano."""

    def __init__(self) -> None:
        self.autenticado = True
        self.actual: Optional[dict] = None
        self.caracteristicas = {
            "energia": 0.5, "valencia": 0.5, "bailabilidad": 0.5, "tempo": 120.0,
        }
        self.tokens_refrescados = 0

    def tiene_credenciales(self) -> bool:
        return True

    def esta_autenticado(self) -> bool:
        return self.autenticado

    def refrescar_token(self) -> None:
        self.tokens_refrescados += 1

    async def obtener_cancion_actual(self):
        return self.actual

    async def obtener_caracteristicas(self, cancion_id):
        return dict(self.caracteristicas)

    def cerrar_sesion(self) -> None:
        self.autenticado = False


class WebSocketFake:
    """WebSocket simulado: guarda cada mensaje JSON enviado por el servidor."""

    def __init__(self) -> None:
        self.enviados: list[dict] = []

    async def send(self, texto: str) -> None:
        self.enviados.append(json.loads(texto))

    def eventos(self, nombre: str) -> list[dict]:
        return [e for e in self.enviados if e.get("evento") == nombre]

    def ultimo(self, nombre: str):
        ev = self.eventos(nombre)
        return ev[-1] if ev else None


def cancion(cid: str, nombre: str = "Tema", artista: str = "Artista", portada: str = "http://x/p.jpg") -> dict:
    return {
        "cancion_id": cid,
        "nombre": nombre,
        "artista": artista,
        "url_portada": portada,
        "reproduciendo": True,
    }
