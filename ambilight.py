"""Cine Mode: captura de pantalla → color ambiente para la tira LED.

Función SOLO LOCAL: analiza lo que se ve en esta PC y produce UN color (la tira
es monocromática) que sigue la escena, con intensidad dinámica. Pensado para
películas/series (YouTube directo; Netflix requiere desactivar la aceleración
por hardware del navegador, porque el DRM devuelve pantalla negra — no se hace
bypass de DRM).

Diseño: espeja el patrón de ``audio_ritmo_final.DetectorRitmo`` (hilo de captura
+ lock + ``get_color_info()``). El análisis de cada frame es una función pura y
vectorizada (numpy) para poder testearla sin pantalla real.
"""

from __future__ import annotations

import colorsys
import logging
import threading
import time
from typing import Optional

import numpy as np

try:
    import mss as _mss
    _MSS_DISPONIBLE = True
except Exception:  # pragma: no cover - depende del entorno
    _mss = None
    _MSS_DISPONIBLE = False

logger = logging.getLogger(__name__)


# ── Funciones puras (testeables sin pantalla) ────────────────────────────

def _media_rgb(bloque: np.ndarray) -> np.ndarray:
    """Media RGB (float 0-255) de un bloque HxWx3; seguro si está vacío."""
    if bloque.size == 0:
        return np.zeros(3, dtype=np.float64)
    return bloque.reshape(-1, 3).mean(axis=0)


def _saturacion_por_pixel(arr: np.ndarray) -> np.ndarray:
    """Saturación (0-1) por píxel de un arreglo HxWx3 (0-255)."""
    a = arr.astype(np.float64)
    mx = a.max(axis=2)
    mn = a.min(axis=2)
    return np.where(mx > 0, (mx - mn) / (mx + 1e-6), 0.0)


def boost_saturacion(rgb, factor: float) -> tuple[int, int, int]:
    """Aumenta la saturación de un color RGB (0-255) por ``factor``."""
    r, g, b = [max(0.0, min(1.0, c / 255.0)) for c in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    s = max(0.0, min(1.0, s * factor))
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))


def analizar_frame(
    arr_rgb: np.ndarray,
    peso_bordes: float = 0.5,
    peso_dominante: float = 0.3,
    saturacion: float = 1.4,
) -> dict:
    """Analiza un frame (HxWx3, uint8, RGB) y devuelve el color ambiente.

    Combina promedio global + franjas de borde + color dominante (saturado),
    aplica boost de saturación y calcula luminancia/saturación medias.

    Returns dict: {r,g,b, luminancia(0-1), saturacion(0-1), drm_negro(bool)}.
    """
    if arr_rgb.ndim != 3 or arr_rgb.shape[2] < 3:
        return {"r": 0, "g": 0, "b": 0, "luminancia": 0.0, "saturacion": 0.0, "drm_negro": True}

    arr = arr_rgb[:, :, :3]
    h, w = arr.shape[:2]

    promedio = _media_rgb(arr)

    # Franjas de borde (arriba/abajo/izq/der).
    bh = max(1, h // 6)
    bw = max(1, w // 6)
    bordes = np.mean([
        _media_rgb(arr[:bh, :]),
        _media_rgb(arr[-bh:, :]),
        _media_rgb(arr[:, :bw]),
        _media_rgb(arr[:, -bw:]),
    ], axis=0)

    # Color dominante = media de los píxeles más saturados.
    sat = _saturacion_por_pixel(arr)
    mask = sat > 0.33
    if mask.sum() >= max(4, arr[:, :, 0].size * 0.01):
        dominante = arr[mask].reshape(-1, 3).mean(axis=0)
    else:
        dominante = promedio

    # Fusión ponderada.
    peso_bordes = float(np.clip(peso_bordes, 0.0, 1.0))
    peso_dominante = float(np.clip(peso_dominante, 0.0, 1.0))
    base = promedio * (1.0 - peso_bordes) + bordes * peso_bordes
    color = base * (1.0 - peso_dominante) + dominante * peso_dominante
    color = np.clip(color, 0, 255)

    r, g, b = boost_saturacion(tuple(color), saturacion)

    luminancia = float((0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]).mean() / 255.0)
    saturacion_media = float(sat.mean())
    drm_negro = luminancia < 0.02

    return {
        "r": r, "g": g, "b": b,
        "luminancia": luminancia,
        "saturacion": saturacion_media,
        "drm_negro": drm_negro,
    }


def mezclar_ema(anterior: tuple, nuevo: tuple, suavizado: float) -> tuple[int, int, int]:
    """Suavizado exponencial entre dos colores RGB (suavizado 0..1, mayor=más lento)."""
    s = float(np.clip(suavizado, 0.0, 0.98))
    r = anterior[0] * s + nuevo[0] * (1 - s)
    g = anterior[1] * s + nuevo[1] * (1 - s)
    b = anterior[2] * s + nuevo[2] * (1 - s)
    return (int(round(r)), int(round(g)), int(round(b)))


def listar_monitores() -> list[dict]:
    """Devuelve los monitores disponibles (índice 0 = todos combinados)."""
    if not _MSS_DISPONIBLE:
        return []
    try:
        with _mss.mss() as sct:
            salida = []
            for i, m in enumerate(sct.monitors):
                salida.append({
                    "indice": i,
                    "ancho": m.get("width", 0),
                    "alto": m.get("height", 0),
                    "nombre": "Todos" if i == 0 else f"Monitor {i}",
                })
            return salida
    except Exception as e:  # pragma: no cover
        logger.warning("No se pudieron listar monitores: %s", e)
        return []


# ── Capturador (hilo, como DetectorRitmo) ────────────────────────────────

class CapturadorPantalla:
    """Captura la pantalla en un hilo y expone el color ambiente suavizado."""

    def __init__(
        self,
        monitor: int = 0,
        fps: int = 20,
        suavizado: float = 0.6,
        saturacion: float = 1.4,
        peso_bordes: float = 0.5,
        peso_dominante: float = 0.3,
        muestra: int = 24,
    ) -> None:
        self.monitor = int(monitor)
        self.fps = max(5, int(fps))
        self.suavizado = float(suavizado)
        self.saturacion = float(saturacion)
        self.peso_bordes = float(peso_bordes)
        self.peso_dominante = float(peso_dominante)
        self.muestra = max(4, int(muestra))  # stride de downsample

        self._corriendo = False
        self._hilo: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._info: dict = {"r": 0, "g": 0, "b": 0, "luminancia": 0.0, "saturacion": 0.0, "drm_negro": False}
        self._ema: Optional[tuple] = None

    @property
    def disponible(self) -> bool:
        return _MSS_DISPONIBLE

    def configurar(self, **kwargs) -> None:
        """Actualiza parámetros en caliente (fps, suavizado, saturacion, pesos, monitor)."""
        for clave in ("fps", "suavizado", "saturacion", "peso_bordes", "peso_dominante", "monitor", "muestra"):
            if clave in kwargs and kwargs[clave] is not None:
                setattr(self, clave, type(getattr(self, clave))(kwargs[clave]))
        self.fps = max(5, int(self.fps))
        self.muestra = max(4, int(self.muestra))

    def get_color_info(self) -> dict:
        with self._lock:
            return dict(self._info)

    def iniciar(self) -> bool:
        if not _MSS_DISPONIBLE:
            logger.error("mss no disponible")
            return False
        if self._corriendo:
            return True
        self._corriendo = True
        self._ema = None
        self._hilo = threading.Thread(target=self._bucle, daemon=True)
        self._hilo.start()
        return True

    def detener(self) -> None:
        self._corriendo = False
        if self._hilo and self._hilo.is_alive():
            self._hilo.join(timeout=2)
        self._hilo = None

    def _bucle(self) -> None:
        # mss debe instanciarse DENTRO del hilo (no es seguro compartirlo).
        try:
            sct = _mss.mss()
        except Exception as e:  # pragma: no cover
            logger.error("No se pudo iniciar la captura: %s", e)
            self._corriendo = False
            return
        try:
            while self._corriendo:
                t0 = time.time()
                try:
                    mons = sct.monitors
                    idx = self.monitor if 0 <= self.monitor < len(mons) else 0
                    crudo = np.asarray(sct.grab(mons[idx]))  # BGRA
                    # Downsample por stride + BGRA->RGB
                    peq = crudo[:: self.muestra, :: self.muestra, :3][:, :, ::-1]
                    info = analizar_frame(peq, self.peso_bordes, self.peso_dominante, self.saturacion)
                    nuevo = (info["r"], info["g"], info["b"])
                    if self._ema is None:
                        self._ema = nuevo
                    else:
                        self._ema = mezclar_ema(self._ema, nuevo, self.suavizado)
                    info["r"], info["g"], info["b"] = self._ema
                    with self._lock:
                        self._info = info
                except Exception:
                    pass
                # Ritmo objetivo de fps
                dt = time.time() - t0
                espera = max(0.0, (1.0 / self.fps) - dt)
                time.sleep(espera)
        finally:
            try:
                sct.close()
            except Exception:
                pass
