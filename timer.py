"""Temporizador Timer para LLeD.

Corre como overlay sobre otros modos (Spotify/Ritmo/Cine) sin cancelarlos.
Al expirar, ejecuta una alerta LED configurable (color + accion).
"""

import asyncio
import json
from typing import Callable, Optional


class TemporizadorTimer:
    """Timer no intrusivo con alerta LED al finalizar.

    No toma control exclusivo de los LEDs durante la cuenta.
    Solo al expirar ejecuta una secuencia de alerta y luego
    devuelve el control al modo que estuviera activo.
    """

    def __init__(
        self,
        websocket,
        motor,
        obtener_tira: Callable,
        on_tick: Optional[Callable] = None,
        on_fin: Optional[Callable] = None,
    ) -> None:
        self._ws = websocket
        self._motor = motor
        self._obtener_tira = obtener_tira
        # Callbacks opcionales para reflejar el timer en el visual remoto.
        # on_tick(progreso, restante); on_fin() al completar o detener.
        self._on_tick = on_tick
        self._on_fin = on_fin
        self._tarea: Optional[asyncio.Task] = None
        self.activo = False
        self.pausado = False
        self.tiempo_total = 0
        self.tiempo_restante = 0
        self._color_alerta = (255, 0, 0)
        self._accion = "blink"
        self._tick_interval = 0.25

    async def iniciar(self, tiempo_seg: int, color: dict, accion: str) -> None:
        self.detener()
        self.activo = True
        self.pausado = False
        self.tiempo_total = max(1, tiempo_seg)
        self.tiempo_restante = self.tiempo_total
        self._color_alerta = (
            color.get("r", 255),
            color.get("g", 0),
            color.get("b", 0),
        )
        self._accion = accion
        self._tarea = asyncio.create_task(self._bucle())

    async def pausar(self) -> None:
        self.pausado = True

    async def reanudar(self) -> None:
        self.pausado = False

    def detener(self) -> None:
        self.activo = False
        if self._tarea and not self._tarea.done():
            self._tarea.cancel()
            self._tarea = None

    async def _enviar(self, obj: dict) -> None:
        try:
            await self._ws.send(json.dumps(obj))
        except Exception:
            pass

    async def _bucle(self) -> None:
        try:
            while self.activo and self.tiempo_restante > 0:
                while self.pausado:
                    await asyncio.sleep(0.1)

                await asyncio.sleep(self._tick_interval)
                self.tiempo_restante -= self._tick_interval

                if self.tiempo_restante < 0:
                    self.tiempo_restante = 0

                progreso = 1.0 - (self.tiempo_restante / self.tiempo_total)

                await self._enviar({
                    "ok": True,
                    "evento": "timer_tick",
                    "restante": self.tiempo_restante,
                    "progreso": round(progreso, 4),
                })
                if self._on_tick:
                    try:
                        self._on_tick(round(progreso, 4), self.tiempo_restante)
                    except Exception:
                        pass

            if self.activo and self.tiempo_restante <= 0:
                await self._ejecutar_alerta()
                self.activo = False
                await self._enviar({"ok": True, "evento": "timer_completado"})

        except asyncio.CancelledError:
            pass
        finally:
            # Solo limpia si sigue siendo la tarea vigente: al reiniciar el timer
            # la tarea vieja (cancelándose) no debe pisar la referencia de la nueva.
            if asyncio.current_task() is self._tarea:
                self.activo = False
                self._tarea = None
                if self._on_fin:
                    try:
                        self._on_fin()
                    except Exception:
                        pass

    async def _ejecutar_alerta(self) -> None:
        """Ejecuta la secuencia de alerta directamente sobre la tira LED."""
        tira = self._obtener_tira()
        r, g, b = self._color_alerta

        if self._accion == "flash":
            await tira.color(r, g, b)
            await asyncio.sleep(0.5)
            await tira.color(0, 0, 0)

        elif self._accion == "blink":
            for _ in range(6):
                await tira.color(r, g, b)
                await asyncio.sleep(0.15)
                await tira.color(0, 0, 0)
                await asyncio.sleep(0.15)

        elif self._accion == "fade":
            await self._motor.crossfade(r, g, b, duracion=1.0)
            await asyncio.sleep(0.3)
            await self._motor.crossfade(0, 0, 0, duracion=1.0)
