"""Motor de transiciones suaves de color para la tira LED.

Da tres primitivas sobre cualquier objeto "tira" que exponga una corrutina
``color(r, g, b)``:

- :meth:`MotorTransiciones.crossfade`  — interpola gradualmente del color
  actual a uno nuevo (cambio de color a color, directo y suave).
- :meth:`MotorTransiciones.fade_a_negro`      — baja el brillo hasta apagar.
- :meth:`MotorTransiciones.fade_desde_negro`  — sube el brillo desde apagado
  hasta un color objetivo.

Con esto el servidor arma el comportamiento pedido:

- Color en cache  → ``crossfade`` directo del color viejo al nuevo.
- Color por calcular → ``fade_a_negro`` mientras se analiza y ``fade_desde_negro``
  al color resuelto.
- Modo "brusco" → :meth:`aplicar` (cambio instantáneo, sin pasos intermedios).

El ritmo de envío se limita para no saturar el enlace BLE (que tiene latencia
propia): nunca se mandan más de ``fps`` cuadros por segundo. Todas las
corrutinas son cancelables; al cancelarse dejan la tira en el último color
enviado y actualizan el estado interno en consecuencia.
"""

from __future__ import annotations

import asyncio


def _clamp(valor: float) -> int:
    return max(0, min(255, int(round(valor))))


class MotorTransiciones:
    """Interpola colores en el tiempo respetando un límite de cuadros/segundo."""

    def __init__(self, tira, fps: int = 30, r: int = 0, g: int = 0, b: int = 0) -> None:
        self.tira = tira
        self.fps = max(1, int(fps))
        self._intervalo_min = 1.0 / self.fps
        # Estado del color actualmente mostrado.
        self.r = _clamp(r)
        self.g = _clamp(g)
        self.b = _clamp(b)
        # Último color realmente enviado a la tira (para evitar duplicados).
        self._ultimo_enviado: tuple[int, int, int] | None = None
        # Callback opcional: se invoca con cada color enviado (r, g, b).
        # Sirve para reflejar la transición real en el visual remoto.
        self.on_color = None

    # ── Estado ────────────────────────────────────────────────────

    def set_actual(self, r: int, g: int, b: int) -> None:
        """Sincroniza el estado interno sin tocar la tira (p. ej. tras un flash)."""
        self.r, self.g, self.b = _clamp(r), _clamp(g), _clamp(b)

    def set_fps(self, fps: int) -> None:
        """Ajusta la tasa máxima de cuadros por segundo del motor."""
        self.fps = max(1, int(fps))
        self._intervalo_min = 1.0 / self.fps

    @property
    def color_actual(self) -> tuple[int, int, int]:
        return (self.r, self.g, self.b)

    # ── Envío de bajo nivel ───────────────────────────────────────

    async def _enviar(self, r: int, g: int, b: int) -> None:
        """Envía un color a la tira, saltando repeticiones consecutivas."""
        color = (r, g, b)
        if color != self._ultimo_enviado:
            await self.tira.color(r, g, b)
            self._ultimo_enviado = color
            if self.on_color is not None:
                self.on_color(r, g, b)
        self.r, self.g, self.b = r, g, b

    async def aplicar(self, r: int, g: int, b: int) -> None:
        """Cambio INSTANTÁNEO (modo brusco): fija el color sin interpolar."""
        await self._enviar(_clamp(r), _clamp(g), _clamp(b))

    # ── Transiciones ──────────────────────────────────────────────

    def _calcular_pasos(self, duracion: float, pasos: int | None) -> int:
        if duracion <= 0:
            return 1
        if pasos is not None:
            maximo = max(1, int(duracion / self._intervalo_min))
            return max(1, min(int(pasos), maximo))
        return max(1, int(round(duracion * self.fps)))

    async def crossfade(
        self,
        r: int,
        g: int,
        b: int,
        duracion: float = 0.5,
        pasos: int | None = None,
    ) -> None:
        """Interpola linealmente del color actual al objetivo en ``duracion`` seg.

        Es el "cambio gradual directo de un color a otro". Si ``duracion`` es 0
        equivale a un cambio instantáneo.
        """
        destino = (_clamp(r), _clamp(g), _clamp(b))
        origen = (self.r, self.g, self.b)

        if duracion <= 0 or origen == destino:
            await self._enviar(*destino)
            return

        n = self._calcular_pasos(duracion, pasos)
        intervalo = duracion / n
        r0, g0, b0 = origen
        r1, g1, b1 = destino

        try:
            for i in range(1, n + 1):
                t = i / n
                await self._enviar(
                    _clamp(r0 + (r1 - r0) * t),
                    _clamp(g0 + (g1 - g0) * t),
                    _clamp(b0 + (b1 - b0) * t),
                )
                if i < n:
                    await asyncio.sleep(intervalo)
        except asyncio.CancelledError:
            # Deja la tira donde quedó; el estado ya está actualizado por _enviar.
            raise

    async def fade_a_negro(self, duracion: float = 0.35, pasos: int | None = None) -> None:
        """Baja gradualmente el brillo del color actual hasta apagar (0,0,0)."""
        await self.crossfade(0, 0, 0, duracion=duracion, pasos=pasos)

    async def fade_desde_negro(
        self,
        r: int,
        g: int,
        b: int,
        duracion: float = 0.45,
        pasos: int | None = None,
    ) -> None:
        """Enciende desde apagado (0,0,0) subiendo el brillo hasta el color dado."""
        self.set_actual(0, 0, 0)
        await self.crossfade(r, g, b, duracion=duracion, pasos=pasos)
