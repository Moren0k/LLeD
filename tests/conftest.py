"""Utilidades y fixtures compartidas por la suite de pruebas."""

from __future__ import annotations

import os
import sys

import pytest

# Permite importar los módulos del proyecto (que viven en la raíz) desde tests/.
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


class TiraFake:
    """Tira LED simulada: registra cada color/estado en lugar de usar BLE.

    Permite probar transiciones y sincronización sin hardware real.
    """

    def __init__(self) -> None:
        self.enviados: list[tuple[int, int, int]] = []
        self.encendida = False
        self.conectada = False
        self.brillos: list[int] = []

    async def conectar(self) -> None:
        self.conectada = True

    async def desconectar(self) -> None:
        self.conectada = False

    async def encender(self) -> None:
        self.encendida = True

    async def apagar(self) -> None:
        self.encendida = False

    async def color(self, r: int, g: int, b: int) -> None:
        self.enviados.append((int(r), int(g), int(b)))

    async def brillo(self, valor: int) -> None:
        self.brillos.append(int(valor))

    async def probar_colores(self) -> None:
        pass

    async def arcoiris(self, pasos: int = 12, demora: float = 0.8) -> None:
        pass

    @property
    def ultimo(self) -> tuple[int, int, int] | None:
        return self.enviados[-1] if self.enviados else None


@pytest.fixture
def tira_fake() -> TiraFake:
    return TiraFake()
