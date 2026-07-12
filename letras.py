"""Letras sincronizadas de canciones (fuente: LRCLIB).

LRCLIB (https://lrclib.net) es una base de datos libre y gratuita de letras
sincronizadas en formato LRC, sin necesidad de API key. La API oficial de
Spotify NO ofrece letras, así que se usa esta fuente y se sincroniza con el
progreso de reproducción que sí entrega Spotify (``progress_ms``).

Todo el acceso a red es bloqueante (``requests``); llamarlo en un executor.
"""

from __future__ import annotations

import re
from typing import Optional

import requests

_API_GET = "https://lrclib.net/api/get"
_API_SEARCH = "https://lrclib.net/api/search"
_UA = "LLeD (https://github.com/Moren0k/LLeD)"
_RE_MARCA = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")

# Caché de sesión por canción para no volver a descargar en repeticiones.
_CACHE: dict = {}
_CACHE_MAX = 64


def _parsear_lrc(texto: str) -> Optional[list[tuple[float, str]]]:
    """Convierte una letra en formato LRC a ``[(segundos, texto), ...]``."""
    lineas: list[tuple[float, str]] = []
    for cruda in (texto or "").splitlines():
        marcas = _RE_MARCA.findall(cruda)
        if not marcas:
            continue
        contenido = _RE_MARCA.sub("", cruda).strip()
        for minutos, segundos in marcas:
            t = int(minutos) * 60 + float(segundos)
            lineas.append((t, contenido))
    lineas.sort(key=lambda par: par[0])
    return lineas or None


def obtener_letra_sincronizada(
    artista: str,
    titulo: str,
    album: str = "",
    duracion_seg: int = 0,
    timeout: float = 5.0,
) -> Optional[list[tuple[float, str]]]:
    """Busca la letra sincronizada de una canción. Devuelve ``[(t, texto)]`` o None.

    Bloqueante: debe llamarse dentro de un executor, no en el event loop.
    Cachea el resultado por canción (incluido "sin letra") durante la sesión.
    """
    if not titulo:
        return None
    clave = (artista or "", titulo, album or "", int(duracion_seg))
    if clave in _CACHE:
        return _CACHE[clave]
    resultado = _buscar_lrclib(artista, titulo, album, duracion_seg, timeout)
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.clear()
    _CACHE[clave] = resultado
    return resultado


def _buscar_lrclib(artista, titulo, album, duracion_seg, timeout):
    cabeceras = {"User-Agent": _UA}

    # 1) Coincidencia exacta (artista + título + duración).
    try:
        params = {"track_name": titulo, "artist_name": artista or ""}
        if album:
            params["album_name"] = album
        if duracion_seg:
            params["duration"] = int(duracion_seg)
        r = requests.get(_API_GET, params=params, headers=cabeceras, timeout=timeout)
        if r.status_code == 200:
            sincronizada = (r.json() or {}).get("syncedLyrics")
            parseada = _parsear_lrc(sincronizada) if sincronizada else None
            if parseada:
                return parseada
    except Exception:
        pass

    # 2) Búsqueda difusa: primer resultado con letra sincronizada.
    try:
        params = {"track_name": titulo, "artist_name": artista or ""}
        r = requests.get(_API_SEARCH, params=params, headers=cabeceras, timeout=timeout)
        if r.status_code == 200:
            for item in (r.json() or []):
                sincronizada = item.get("syncedLyrics")
                parseada = _parsear_lrc(sincronizada) if sincronizada else None
                if parseada:
                    return parseada
    except Exception:
        pass

    return None


def indice_linea_actual(lineas: list[tuple[float, str]], t_seg: float) -> int:
    """Índice de la línea activa para el tiempo ``t_seg`` (o -1 si aún no empezó)."""
    idx = -1
    for i, (t, _) in enumerate(lineas):
        if t <= t_seg:
            idx = i
        else:
            break
    return idx
