"""Cache local de color por canción para acelerar la sincronización.

Guarda un color RGB por cada ``cancion_id`` de Spotify. El color puede ser:

- ``"auto"``   : calculado automáticamente por el sistema (portada/humor).
- ``"usuario"``: elegido manualmente por el usuario. Tiene prioridad y NUNCA
  es sobreescrito por un cálculo automático.

El cache vive en memoria (un ``dict``) para consultas instantáneas —esto es lo
que permite cambiar el color al instante cuando una canción ya fue analizada—
y se persiste en un archivo JSON en disco. Es seguro para acceso concurrente
desde varios hilos gracias a un lock reentrante.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from typing import Optional


FUENTE_AUTO = "auto"
FUENTE_USUARIO = "usuario"


def _clamp(valor: int) -> int:
    """Restringe un canal de color al rango válido 0-255."""
    try:
        valor = int(valor)
    except (TypeError, ValueError):
        valor = 0
    return max(0, min(255, valor))


class CacheColores:
    """Almacén rápido de color por canción con persistencia en JSON.

    Uso típico::

        cache = CacheColores("color_cache.json")
        color = cache.obtener_color(cancion_id)   # None si no está
        if color is None:
            color = calcular_color_lento(...)      # análisis costoso
            cache.guardar_auto(cancion_id, *color, nombre, artista)
    """

    def __init__(self, ruta: str = "color_cache.json", autosave: bool = True) -> None:
        self.ruta = ruta
        self.autosave = autosave
        self._lock = threading.RLock()
        self._datos: dict[str, dict] = {}
        self._cargar()

    # ── Persistencia ──────────────────────────────────────────────

    def _cargar(self) -> None:
        """Carga el cache desde disco. Si el archivo está corrupto, empieza limpio."""
        if not os.path.exists(self.ruta):
            return
        try:
            with open(self.ruta, encoding="utf-8") as f:
                datos = json.load(f)
            if isinstance(datos, dict):
                # Normaliza cada entrada para tolerar archivos viejos/parciales.
                for cid, entrada in datos.items():
                    if isinstance(entrada, dict) and {"r", "g", "b"} <= entrada.keys():
                        self._datos[str(cid)] = self._normalizar(entrada)
        except (json.JSONDecodeError, OSError, ValueError):
            # Cache ilegible: no es fatal, arrancamos con cache vacío.
            self._datos = {}

    def _persistir(self) -> None:
        """Escribe el cache a disco de forma atómica (temp + replace)."""
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
        """Fuerza la escritura del cache a disco (útil con ``autosave=False``)."""
        with self._lock:
            self._persistir()

    # ── Normalización ─────────────────────────────────────────────

    @staticmethod
    def _normalizar(entrada: dict) -> dict:
        return {
            "r": _clamp(entrada.get("r", 0)),
            "g": _clamp(entrada.get("g", 0)),
            "b": _clamp(entrada.get("b", 0)),
            "nombre": str(entrada.get("nombre", "")),
            "artista": str(entrada.get("artista", "")),
            "fuente": entrada.get("fuente", FUENTE_AUTO),
            "actualizado": float(entrada.get("actualizado", 0.0) or 0.0),
        }

    # ── Consultas ─────────────────────────────────────────────────

    def obtener(self, cancion_id: str) -> Optional[dict]:
        """Devuelve una copia de la entrada de una canción, o None."""
        if not cancion_id:
            return None
        with self._lock:
            entrada = self._datos.get(str(cancion_id))
            return dict(entrada) if entrada else None

    def obtener_color(self, cancion_id: str) -> Optional[tuple[int, int, int]]:
        """Atajo: devuelve solo la tupla (r, g, b) o None si no está cacheada."""
        entrada = self.obtener(cancion_id)
        if entrada is None:
            return None
        return (entrada["r"], entrada["g"], entrada["b"])

    def existe(self, cancion_id: str) -> bool:
        with self._lock:
            return str(cancion_id) in self._datos

    def es_de_usuario(self, cancion_id: str) -> bool:
        """True si el color de la canción fue fijado manualmente por el usuario."""
        entrada = self.obtener(cancion_id)
        return bool(entrada and entrada.get("fuente") == FUENTE_USUARIO)

    # ── Escritura ─────────────────────────────────────────────────

    def guardar_auto(
        self,
        cancion_id: str,
        r: int,
        g: int,
        b: int,
        nombre: str = "",
        artista: str = "",
    ) -> tuple[int, int, int]:
        """Guarda un color calculado automáticamente.

        Respeta la elección del usuario: si la canción ya tiene un color de
        fuente ``"usuario"``, NO lo sobreescribe y devuelve ese color de usuario.
        Devuelve el color efectivo que debería mostrarse.
        """
        if not cancion_id:
            return (_clamp(r), _clamp(g), _clamp(b))
        cid = str(cancion_id)
        with self._lock:
            existente = self._datos.get(cid)
            if existente and existente.get("fuente") == FUENTE_USUARIO:
                # El usuario mandó: conservamos su color, solo refrescamos metadatos.
                if nombre:
                    existente["nombre"] = str(nombre)
                if artista:
                    existente["artista"] = str(artista)
                if self.autosave:
                    self._persistir()
                return (existente["r"], existente["g"], existente["b"])

            entrada = {
                "r": _clamp(r),
                "g": _clamp(g),
                "b": _clamp(b),
                "nombre": str(nombre) if nombre else (existente or {}).get("nombre", ""),
                "artista": str(artista) if artista else (existente or {}).get("artista", ""),
                "fuente": FUENTE_AUTO,
                "actualizado": time.time(),
            }
            self._datos[cid] = entrada
            if self.autosave:
                self._persistir()
            return (entrada["r"], entrada["g"], entrada["b"])

    def guardar_usuario(
        self,
        cancion_id: str,
        r: int,
        g: int,
        b: int,
        nombre: str = "",
        artista: str = "",
    ) -> tuple[int, int, int]:
        """Fija un color elegido por el usuario. Tiene prioridad sobre el automático."""
        if not cancion_id:
            return (_clamp(r), _clamp(g), _clamp(b))
        cid = str(cancion_id)
        with self._lock:
            existente = self._datos.get(cid, {})
            entrada = {
                "r": _clamp(r),
                "g": _clamp(g),
                "b": _clamp(b),
                "nombre": str(nombre) if nombre else existente.get("nombre", ""),
                "artista": str(artista) if artista else existente.get("artista", ""),
                "fuente": FUENTE_USUARIO,
                "actualizado": time.time(),
            }
            self._datos[cid] = entrada
            if self.autosave:
                self._persistir()
            return (entrada["r"], entrada["g"], entrada["b"])

    def eliminar(self, cancion_id: str) -> bool:
        """Borra una canción del cache. Devuelve True si existía."""
        cid = str(cancion_id)
        with self._lock:
            existia = cid in self._datos
            self._datos.pop(cid, None)
            if existia and self.autosave:
                self._persistir()
            return existia

    def limpiar(self) -> None:
        """Vacía todo el cache."""
        with self._lock:
            self._datos.clear()
            if self.autosave:
                self._persistir()

    # ── Listado ───────────────────────────────────────────────────

    def listar(self) -> list[dict]:
        """Devuelve todas las canciones cacheadas, más recientes primero.

        Cada elemento incluye ``cancion_id`` además de los campos de color.
        """
        with self._lock:
            items = []
            for cid, entrada in self._datos.items():
                item = dict(entrada)
                item["cancion_id"] = cid
                items.append(item)
        items.sort(key=lambda e: e.get("actualizado", 0.0), reverse=True)
        return items

    def __len__(self) -> int:
        with self._lock:
            return len(self._datos)
