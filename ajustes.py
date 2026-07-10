"""Preferencias del usuario persistentes en ``ajustes.json``.

Separadas de ``config.json`` (que guarda credenciales y la MAC del dispositivo)
para no mezclar secretos con preferencias de interfaz.

Ajustes disponibles:

- ``modo_transicion``     : ``"gradiente"`` | ``"brusco"``. Controla si los
  cambios de color son suaves (interpolados) o instantáneos.
- ``duracion_crossfade``  : segundos de un cambio directo de color a color.
- ``duracion_fade_out``   : segundos de la bajada de brillo al detectar una
  canción nueva sin color en cache.
- ``duracion_fade_in``    : segundos de la subida de brillo al color recién
  calculado.
- ``fps_transicion``      : cuadros por segundo del motor de transiciones.
- ``sync_modo``           : último modo de sincronización usado (``"portada"``
  | ``"humor"``).
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from typing import Any


MODO_GRADIENTE = "gradiente"
MODO_BRUSCO = "brusco"

DEFAULTS: dict[str, Any] = {
    "modo_transicion": MODO_GRADIENTE,
    "duracion_crossfade": 0.6,
    "duracion_fade_out": 0.35,
    "duracion_fade_in": 0.5,
    "fps_transicion": 30,
    "sync_modo": "portada",
    "intervalo_spotify": 0.8,
    # Tarjeta con el nombre de la canción en los visuales.
    "visual_titulo": True,
    "visual_titulo_escala": 1.0,   # 0.5 - 3.0
    "visual_titulo_x": 0.5,        # 0 (izq) - 1 (der)
    "visual_titulo_y": 0.85,       # 0 (arriba) - 1 (abajo)
    # Tipo de visual y si los elementos se desplazan por la pantalla.
    "visual_tipo": "aurora",       # "aurora" | "orbes" | "ondas"
    "visual_movimiento": True,
    # Cine Mode (ambilight): color ambiente según la pantalla.
    "ambilight_fps": 15,               # 10 - 30
    "ambilight_suavizado": 0.6,        # 0 - 0.95 (EMA, mayor = más suave)
    "ambilight_saturacion": 1.4,       # 1.0 - 2.5
    "ambilight_intensidad_min": 0.08,  # 0 - 1
    "ambilight_intensidad_max": 1.0,   # 0 - 1
    "ambilight_peso_bordes": 0.5,      # 0 - 1
    "ambilight_peso_dominante": 0.3,   # 0 - 1
    "ambilight_reactivo_audio": True,
    "ambilight_sensibilidad_audio": 0.6,  # 0 - 1 (sensibilidad a golpes/impactos)
    "ambilight_monitor": 0,            # índice de monitor (0 = todos)
}

VISUALES_VALIDOS = ("aurora", "orbes", "ondas")


def _clamp_float(valor: Any, minimo: float, maximo: float, defecto: float) -> float:
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return defecto
    return max(minimo, min(maximo, v))


def _clamp_int(valor: Any, minimo: int, maximo: int, defecto: int) -> int:
    try:
        v = int(valor)
    except (TypeError, ValueError):
        return defecto
    return max(minimo, min(maximo, v))


def _validar(clave: str, valor: Any) -> Any:
    """Normaliza/valida un valor según la clave. Devuelve el valor saneado."""
    if clave == "modo_transicion":
        return valor if valor in (MODO_GRADIENTE, MODO_BRUSCO) else DEFAULTS[clave]
    if clave == "duracion_crossfade":
        return _clamp_float(valor, 0.0, 5.0, DEFAULTS[clave])
    if clave == "duracion_fade_out":
        return _clamp_float(valor, 0.0, 5.0, DEFAULTS[clave])
    if clave == "duracion_fade_in":
        return _clamp_float(valor, 0.0, 5.0, DEFAULTS[clave])
    if clave == "fps_transicion":
        return _clamp_int(valor, 5, 60, DEFAULTS[clave])
    if clave == "intervalo_spotify":
        return _clamp_float(valor, 0.3, 3.0, DEFAULTS[clave])
    if clave == "visual_titulo":
        return bool(valor)
    if clave == "visual_titulo_escala":
        return _clamp_float(valor, 0.5, 3.0, DEFAULTS[clave])
    if clave == "visual_titulo_x":
        return _clamp_float(valor, 0.0, 1.0, DEFAULTS[clave])
    if clave == "visual_titulo_y":
        return _clamp_float(valor, 0.0, 1.0, DEFAULTS[clave])
    if clave == "visual_tipo":
        return valor if valor in VISUALES_VALIDOS else DEFAULTS[clave]
    if clave == "visual_movimiento":
        return bool(valor)
    if clave == "ambilight_fps":
        return _clamp_int(valor, 10, 30, DEFAULTS[clave])
    if clave == "ambilight_suavizado":
        return _clamp_float(valor, 0.0, 0.95, DEFAULTS[clave])
    if clave == "ambilight_saturacion":
        return _clamp_float(valor, 1.0, 2.5, DEFAULTS[clave])
    if clave in ("ambilight_intensidad_min", "ambilight_intensidad_max",
                 "ambilight_peso_bordes", "ambilight_peso_dominante",
                 "ambilight_sensibilidad_audio"):
        return _clamp_float(valor, 0.0, 1.0, DEFAULTS[clave])
    if clave == "ambilight_reactivo_audio":
        return bool(valor)
    if clave == "ambilight_monitor":
        return _clamp_int(valor, 0, 16, DEFAULTS[clave])
    if clave == "sync_modo":
        return valor if valor in ("portada", "humor") else DEFAULTS[clave]
    return valor


class Ajustes:
    """Almacén de preferencias con validación y persistencia atómica."""

    def __init__(self, ruta: str = "ajustes.json", autosave: bool = True) -> None:
        self.ruta = ruta
        self.autosave = autosave
        self._lock = threading.RLock()
        self._datos: dict[str, Any] = dict(DEFAULTS)
        self._cargar()

    def _cargar(self) -> None:
        if not os.path.exists(self.ruta):
            return
        try:
            with open(self.ruta, encoding="utf-8") as f:
                datos = json.load(f)
            if isinstance(datos, dict):
                for clave in DEFAULTS:
                    if clave in datos:
                        self._datos[clave] = _validar(clave, datos[clave])
        except (json.JSONDecodeError, OSError, ValueError):
            self._datos = dict(DEFAULTS)

    def _persistir(self) -> None:
        directorio = os.path.dirname(os.path.abspath(self.ruta))
        os.makedirs(directorio, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=directorio, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._datos, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.ruta)
        except OSError:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass

    def guardar(self) -> None:
        with self._lock:
            self._persistir()

    # ── Acceso ────────────────────────────────────────────────────

    def get(self, clave: str) -> Any:
        with self._lock:
            return self._datos.get(clave, DEFAULTS.get(clave))

    def set(self, clave: str, valor: Any) -> Any:
        """Fija un ajuste validado. Ignora claves desconocidas. Devuelve el valor final."""
        if clave not in DEFAULTS:
            return None
        with self._lock:
            self._datos[clave] = _validar(clave, valor)
            if self.autosave:
                self._persistir()
            return self._datos[clave]

    def resetear(self) -> dict[str, Any]:
        """Restablece todos los ajustes a los valores por defecto."""
        with self._lock:
            self._datos = dict(DEFAULTS)
            if self.autosave:
                self._persistir()
            return dict(self._datos)

    def actualizar(self, cambios: dict[str, Any]) -> dict[str, Any]:
        """Aplica varios ajustes de una vez. Devuelve el diccionario completo resultante."""
        with self._lock:
            for clave, valor in (cambios or {}).items():
                if clave in DEFAULTS:
                    self._datos[clave] = _validar(clave, valor)
            if self.autosave:
                self._persistir()
            return dict(self._datos)

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._datos)

    # ── Atajos de conveniencia ────────────────────────────────────

    @property
    def es_gradiente(self) -> bool:
        return self.get("modo_transicion") == MODO_GRADIENTE
