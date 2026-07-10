"""Extrae colores dominantes desde imágenes de portadas de álbumes."""

import io
import os
import tempfile
from typing import Optional

import requests
from colorthief import ColorThief
from PIL import Image


def descargar_imagen(url: str, tiempo_limite: int = 10) -> Optional[bytes]:
    """Descarga una imagen desde una URL y devuelve sus bytes."""
    try:
        respuesta = requests.get(url, timeout=tiempo_limite)
        respuesta.raise_for_status()
        return respuesta.content
    except requests.RequestException:
        return None


def extraer_color_dominante(datos_imagen: bytes, calidad: int = 10) -> Optional[tuple[int, int, int]]:
    """Extrae el color RGB dominante de una imagen.

    Args:
        datos_imagen: Bytes de la imagen (JPEG, PNG, etc.)
        calidad: Muestreo de píxeles (1=preciso, 10=rápido)

    Returns:
        Tupla (R, G, B) o None si falla.
    """
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(datos_imagen)
            ruta_tmp = tmp.name

        thief = ColorThief(ruta_tmp)
        color = thief.get_color(quality=calidad)
        os.unlink(ruta_tmp)
        return color
    except Exception:
        return None


def extraer_paleta(datos_imagen: bytes, cantidad: int = 6, calidad: int = 10) -> Optional[list[tuple[int, int, int]]]:
    """Extrae una paleta de colores de una imagen.

    Returns:
        Lista de tuplas (R, G, B) ordenadas por dominancia.
    """
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(datos_imagen)
            ruta_tmp = tmp.name

        thief = ColorThief(ruta_tmp)
        paleta = thief.get_palette(color_count=cantidad, quality=calidad)
        os.unlink(ruta_tmp)
        return paleta
    except Exception:
        return None


def extraer_color_promedio(datos_imagen: bytes) -> Optional[tuple[int, int, int]]:
    """Calcula el color promedio de toda la imagen."""
    try:
        img = Image.open(io.BytesIO(datos_imagen))
        img = img.convert("RGB")
        pixeles = list(img.getdata())
        total = len(pixeles)
        r = sum(p[0] for p in pixeles) // total
        g = sum(p[1] for p in pixeles) // total
        b = sum(p[2] for p in pixeles) // total
        return (r, g, b)
    except Exception:
        return None


def _rgb_a_hsv(r: int, g: int, b: int) -> tuple[float, float, float]:
    """Convierte RGB (0-255) a HSV (h=0-360, s=0-1, v=0-1)."""
    rn, gn, bn = r / 255, g / 255, b / 255
    mx = max(rn, gn, bn)
    mn = min(rn, gn, bn)
    df = mx - mn

    if mx == mn:
        h = 0.0
    elif mx == rn:
        h = (60 * ((gn - bn) / df) + 360) % 360
    elif mx == gn:
        h = (60 * ((bn - rn) / df) + 120) % 360
    else:
        h = (60 * ((rn - gn) / df) + 240) % 360

    s = 0.0 if mx == 0 else df / mx
    v = mx
    return h, s, v


def _hsv_a_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    """Convierte HSV (h=0-360, s=0-1, v=0-1) a RGB (0-255)."""
    i = int(h / 60) % 6
    f = (h / 60) - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    r, g, b = [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)][i]
    return int(r * 255), int(g * 255), int(b * 255)


def _hue_puro(h: float) -> tuple[int, int, int]:
    """Convierte un matiz HSV en un RGB 100% puro: saturación=1.0, brillo=1.0."""
    return _hsv_a_rgb(h, 1.0, 1.0)


def extraer_color_fuerte(datos_imagen: bytes, cantidad: int = 8, calidad: int = 5) -> Optional[tuple[int, int, int]]:
    """Extrae el color más intenso de la paleta y lo satura al máximo.

    1. Obtiene paleta de colores representativos del arte
    2. Filtra grises (saturación < 0.15) y negros (brillo < 0.15)
    3. Selecciona el de mayor saturación × brillo
    4. Devuelve ese MATIZ con saturación=1.0 y brillo=1.0 (color puro e intenso)

    Returns:
        Tupla (R, G, B) siempre con colores fuertes y nítidos, o None si falla.
    """
    paleta = extraer_paleta(datos_imagen, cantidad=cantidad, calidad=calidad)
    if not paleta:
        return None

    colores = []
    for r, g, b in paleta:
        h, s, v = _rgb_a_hsv(r, g, b)
        if s < 0.15 or v < 0.15:
            continue
        colores.append((h, s, v))

    if not colores:
        h, _, _ = _rgb_a_hsv(*paleta[0])
        return _hue_puro(h)

    mejor = max(colores, key=lambda x: x[1] * x[2])

    return _hue_puro(mejor[0])


_COLORES_BASICOS = [
    (0, 20, (255, 0, 0), "rojo"),
    (20, 50, (255, 128, 0), "naranja"),
    (50, 75, (255, 255, 0), "amarillo"),
    (75, 160, (0, 255, 0), "verde"),
    (160, 200, (0, 255, 255), "cian"),
    (200, 265, (0, 0, 255), "azul"),
    (265, 295, (128, 0, 255), "morado"),
    (295, 345, (255, 0, 255), "rosa"),
    (345, 360, (255, 0, 0), "rojo"),
]


def _hue_a_basico(h: float, s: float, v: float) -> tuple[int, int, int]:
    """Mapea un color HSV al color básico más cercano con RGB puro."""
    if s < 0.15:
        if v > 0.85:
            return (255, 255, 255)
        return (200, 200, 200)

    if v < 0.2:
        return (50, 50, 50)

    for inicio, fin, rgb, _ in _COLORES_BASICOS:
        if inicio <= h < fin:
            return rgb
    return (255, 0, 0)


def extraer_color_basico(datos_imagen: bytes, cantidad: int = 8, calidad: int = 5) -> Optional[tuple[int, int, int]]:
    """Extrae el color más FUERTE de la paleta y lo mapea a color básico.

    No elige por frecuencia (el que más aparece) sino por FUERZA
    (saturación × brillo). Así un azul oscuro y vibrante gana
    aunque haya más área blanca.

    Returns rojo, azul, verde, naranja, amarillo, morado, rosa o cian.
    NUNCA colores pastel o indefinidos.
    """
    paleta = extraer_paleta(datos_imagen, cantidad=cantidad, calidad=calidad)
    if not paleta:
        color = extraer_color_dominante(datos_imagen, calidad=calidad)
        if color is None:
            return (255, 0, 0)
        h, s, v = _rgb_a_hsv(*color)
        return _hue_a_basico(h, s, v)

    mejor_puntaje = -1
    mejor_h = 0.0
    mejor_s = 0.0
    mejor_v = 0.0

    for r, g, b in paleta:
        h, s, v = _rgb_a_hsv(r, g, b)
        if s < 0.1 or v < 0.1:
            continue
        puntaje = s * v
        if puntaje > mejor_puntaje:
            mejor_puntaje = puntaje
            mejor_h, mejor_s, mejor_v = h, s, v

    if mejor_puntaje < 0:
        h, _, _ = _rgb_a_hsv(*paleta[0])
        return _hue_a_basico(h, 1.0, 1.0)

    return _hue_a_basico(mejor_h, mejor_s, mejor_v)


def portada_a_rgb(url: str, metodo: str = "basico") -> Optional[tuple[int, int, int]]:
    """Flujo completo: descarga una portada y extrae su color.

    Args:
        url: URL de la imagen.
        metodo: "basico" (recomendado), "fuerte", "vibrante", "dominante" o "promedio".

    Returns:
        Tupla (R, G, B) — siempre color puro y reconocible, o None si falla.
    """
    datos = descargar_imagen(url)
    if datos is None:
        return None

    if metodo == "promedio":
        return extraer_color_promedio(datos)
    if metodo == "dominante":
        return extraer_color_dominante(datos)
    if metodo == "vibrante":
        color = extraer_color_dominante(datos)
        if color is None:
            return None
        h, s, v = _rgb_a_hsv(*color)
        return _hsv_a_rgb(h, 1.0, max(v, 0.85))
    if metodo == "fuerte":
        return extraer_color_fuerte(datos)

    return extraer_color_basico(datos)
