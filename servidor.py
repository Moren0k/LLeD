"""Servidor WebSocket para controlar la tira LED desde Electron.

Comandos BLE:
  encender, apagar, color, brillo, probar, arcoiris, ping

Comandos Spotify:
  spotify_login, spotify_logout, spotify_estado,
  spotify_iniciar, spotify_detener, spotify_info, spotify_modo

Comandos Ritmo:
  ritmo_iniciar, ritmo_detener, ritmo_flash_color,
  ritmo_modo_deteccion, ritmo_flash_only

Comandos Ajustes:
  ajustes_obtener, ajustes_guardar

Comandos Cache de colores:
  cache_listar, cache_editar, cache_eliminar, cache_limpiar

── Comportamiento de color al cambiar de canción ────────────────────────
Cuando suena una canción nueva:
  • Si su color ya está en cache  → transición directa color→color
    (crossfade en modo gradiente, o cambio instantáneo en modo brusco).
  • Si el color hay que calcularlo → baja el brillo (fade a negro) MIENTRAS
    se analiza la portada, y al terminar sube el brillo con el color nuevo
    (fade desde negro). En modo brusco el cambio es instantáneo.
El color calculado se guarda en cache para que la próxima vez sea inmediato.
"""

import asyncio
import json
import math
import os
import random
import time

from typing import Optional

import websockets

from ajustes import Ajustes
from ambilight import CapturadorPantalla, listar_monitores
from timer import TemporizadorTimer
from audio_ritmo_final import DetectorRitmo
from cache_colores import CacheColores, FUENTE_AUTO, FUENTE_USUARIO
from extractor_color import portada_a_rgb
from led import TiraLED, _hsv_a_rgb
from rutas import ruta_datos
from spotify_cliente import ClienteSpotify, cargar_config_spotify
from transiciones import MotorTransiciones
from visual_server import hub as visual_hub

PUERTO = 8765
INTERVALO_VERIFICACION = 1.5
DURACION_PULSO = 0.08

RUTA_CACHE_COLORES = ruta_datos("color_cache.json")
RUTA_AJUSTES = ruta_datos("ajustes.json")


# ── Singletons de proceso (cache y ajustes son compartidos) ──────────────
# Se exponen a nivel de módulo para que las pruebas puedan sustituirlos.
_cache_colores: Optional[CacheColores] = None
_ajustes_usuario: Optional[Ajustes] = None


def obtener_cache() -> CacheColores:
    global _cache_colores
    if _cache_colores is None:
        _cache_colores = CacheColores(RUTA_CACHE_COLORES)
    return _cache_colores


def obtener_ajustes() -> Ajustes:
    global _ajustes_usuario
    if _ajustes_usuario is None:
        _ajustes_usuario = Ajustes(RUTA_AJUSTES)
    return _ajustes_usuario


# ── Fábricas inyectables (las pruebas las monkeypatchean) ────────────────
def _crear_tira(direccion: str) -> TiraLED:
    return TiraLED(direccion)


def _crear_spotify(creds: dict) -> ClienteSpotify:
    return ClienteSpotify(creds["cliente_id"], creds["cliente_secreto"])


async def calcular_color_cancion(spotify, cancion: dict, modo: str):
    """Calcula el color de una canción SIN bloquear el event loop.

    El trabajo pesado (descargar la portada y extraer el color) corre en un
    hilo aparte vía ``run_in_executor``. Devuelve (r, g, b) o None.
    """
    loop = asyncio.get_event_loop()
    if modo == "humor":
        caracteristicas = await spotify.obtener_caracteristicas(cancion["cancion_id"])
        if caracteristicas:
            return mapear_caracteristicas_a_rgb(caracteristicas)
        return None

    url = cancion.get("url_portada")
    if not url:
        return None
    return await loop.run_in_executor(None, portada_a_rgb, url, "basico")


class EstadoLED:
    """Estado por conexión: color base, flash de ritmo y motor de transiciones."""

    def __init__(self, tira: TiraLED, motor: MotorTransiciones) -> None:
        self.tira = tira
        self.motor = motor
        # Color base = color de la canción o selección manual actual.
        self.r_base = 0
        self.g_base = 0
        self.b_base = 0
        # Flash del modo ritmo.
        self.r_flash = 255
        self.g_flash = 255
        self.b_flash = 255
        self.flash_only = False
        self.modo_deteccion = "kick"
        # Canción sonando (para editar su color en caliente).
        self.cancion_actual_id: Optional[str] = None
        self.cancion_nombre: str = ""
        self.cancion_artista: str = ""
        self.cancion_portada: str = ""
        self.tarea_pulso: Optional[asyncio.Task] = None

    def set_base(self, r: int, g: int, b: int) -> None:
        self.r_base, self.g_base, self.b_base = r, g, b


async def _enviar_json(websocket, obj: dict) -> None:
    """Envía JSON tolerando que la conexión se haya cerrado."""
    try:
        await websocket.send(json.dumps(obj))
    except websockets.exceptions.ConnectionClosed:
        pass


async def _pulso_beat(estado: EstadoLED, energy_intensity: float = 1.0) -> None:
    """Flash dinámico con rango COMPLETO 0-100% de brillo.

    energy_intensity: 0-1 (0=apagado, 1=máximo)
    """
    tira = estado.tira
    try:
        intensity = energy_intensity  # 0-1 sin límite inferior

        r_intenso = int(estado.r_flash * intensity)
        g_intenso = int(estado.g_flash * intensity)
        b_intenso = int(estado.b_flash * intensity)

        await tira.color(r_intenso, g_intenso, b_intenso)

        pulse_duration = (0.03 * (1 - energy_intensity)) + (0.12 * energy_intensity)
        await asyncio.sleep(pulse_duration)

        if estado.flash_only:
            if energy_intensity < 0.2:
                await tira.color(0, 0, 0)
            else:
                dim_factor = max(1, int(20 / (energy_intensity + 0.1)))
                await tira.color(
                    max(0, estado.r_flash // dim_factor),
                    max(0, estado.g_flash // dim_factor),
                    max(0, estado.b_flash // dim_factor),
                )
        else:
            if energy_intensity < 0.15:
                await tira.color(0, 0, 0)
            else:
                await tira.color(estado.r_base, estado.g_base, estado.b_base)

    except asyncio.CancelledError:
        pass


def cargar_config() -> dict:
    """Lee config.json completo."""
    ruta = ruta_datos("config.json")
    if not os.path.exists(ruta):
        return {"direccion_mac": None}
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def guardar_config(config: dict) -> None:
    """Guarda config.json completo."""
    ruta = ruta_datos("config.json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


class _TiraNula:
    """Tira falsa usada cuando no hay dispositivo conectado (no-op seguro)."""

    async def conectar(self): pass
    async def desconectar(self): pass
    async def encender(self): pass
    async def apagar(self): pass
    async def color(self, r, g, b): pass
    async def brillo(self, valor): pass
    async def temperatura(self, calido=50, frio=50): pass
    async def probar_colores(self): pass
    async def arcoiris(self, *a, **k): pass


async def manejar_cliente(websocket):
    """Mantiene una conexión por cliente: BLE + Spotify + sincronización."""
    cache = obtener_cache()
    ajustes = obtener_ajustes()

    spotify_creds = cargar_config_spotify(ruta_datos("config.json"))
    spotify = _crear_spotify(spotify_creds)
    # Restaura la sesión de Spotify desde la caché (sin navegador) si existe.
    if hasattr(spotify, "autenticar_desde_cache"):
        try:
            spotify.autenticar_desde_cache()
        except Exception:
            pass

    config = cargar_config()
    direccion = config.get("direccion_mac")

    motor = MotorTransiciones(_TiraNula(), fps=ajustes.get("fps_transicion"))

    def _reflejar_color(r, g, b):
        # Cada paso real de la transición va al visual remoto y al fondo de la app.
        visual_hub.set_color(r, g, b)
        asyncio.create_task(_enviar_json(websocket, {
            "ok": True, "evento": "visual_color", "r": r, "g": g, "b": b
        }))

    motor.on_color = _reflejar_color
    estado = EstadoLED(_TiraNula(), motor)
    tira = estado.tira
    dispositivo_conectado = False

    async def conectar_a(nueva_direccion):
        """Conecta a una MAC concreta y actualiza motor/estado. Devuelve la tira."""
        nonlocal tira, dispositivo_conectado, direccion
        nueva = _crear_tira(nueva_direccion)
        await nueva.conectar()
        await nueva.encender()
        tira = nueva
        motor.tira = nueva
        motor._ultimo_enviado = None
        estado.tira = nueva
        dispositivo_conectado = True
        direccion = nueva_direccion
        return nueva

    def info_dispositivo():
        return {"direccion": direccion, "conectado": dispositivo_conectado}

    def cfg_titulo():
        return {
            "titulo": ajustes.get("visual_titulo"),
            "titulo_escala": ajustes.get("visual_titulo_escala"),
            "titulo_x": ajustes.get("visual_titulo_x"),
            "titulo_y": ajustes.get("visual_titulo_y"),
            "portada_tarjeta": ajustes.get("visual_portada"),
        }

    def cfg_portada():
        return {
            "portada_difuminado": ajustes.get("visual_portada_difuminado"),
            "portada_x": ajustes.get("visual_portada_x"),
            "portada_y": ajustes.get("visual_portada_y"),
        }

    tarea_sincronizacion: Optional[asyncio.Task] = None
    sincronizando = False
    sync_modo = ajustes.get("sync_modo")
    detector_ritmo = DetectorRitmo(modo_deteccion=estado.modo_deteccion)
    ritmo_activado = False
    tarea_ritmo: Optional[asyncio.Task] = None

    # Efectos de ambiente (vela, fuego, respiración, pulso, ciclo).
    ambiente_activado = False
    ambiente_efecto = "respiracion"
    tarea_ambiente: Optional[asyncio.Task] = None

    # Estado del visual del timer (elegido desde la sección Visuales del front).
    timer_visual_tipo = "splitflap"
    timer_visual_usar = True
    timer_fondo = {"r": 10, "g": 10, "b": 30}

    def _timer_feed_tick(progreso, restante):
        visual_hub.set_timer_tick(progreso, restante)

    def _timer_feed_fin():
        # Al completar o detener: oculta el timer y vuelve al visual normal.
        visual_hub.set_timer_estado(False)
        visual_hub.set_visual(ajustes.get("visual_tipo"), ajustes.get("visual_movimiento"), cfg_portada())

    def _timer_push_visual():
        # Refleja en el remoto qué visual va durante el timer (Reloj/Tarjeta o
        # el visual normal si el usuario lo eligió).
        visual_hub.set_timer_fondo(timer_fondo["r"], timer_fondo["g"], timer_fondo["b"])
        if timer_visual_usar:
            visual_hub.set_timer_estado(True)
            visual_hub.set_visual(timer_visual_tipo, False)
        else:
            visual_hub.set_timer_estado(False)
            visual_hub.set_visual(ajustes.get("visual_tipo"), ajustes.get("visual_movimiento"), cfg_portada())

    temporizador = TemporizadorTimer(
        websocket, motor, lambda: tira,
        on_tick=_timer_feed_tick, on_fin=_timer_feed_fin,
    )

    capturador = CapturadorPantalla()
    ambilight_activado = False
    ambilight_uso_audio = False
    tarea_ambilight: Optional[asyncio.Task] = None

    COMANDOS_LED = {"encender", "apagar", "color", "brillo", "probar", "arcoiris", "temperatura"}

    try:
        if direccion:
            try:
                await conectar_a(direccion)
                print("Cliente conectado. Tira lista.")
            except Exception as e:
                print(f"No se pudo conectar al dispositivo {direccion}: {e}")
        await websocket.send(json.dumps({
            "ok": True, "evento": "conectado", "dispositivo": info_dispositivo()
        }))

        async for mensaje in websocket:
            datos = json.loads(mensaje)
            comando = datos.get("comando")

            # Los comandos que tocan el LED requieren un dispositivo conectado.
            if comando in COMANDOS_LED and not dispositivo_conectado:
                await websocket.send(json.dumps({
                    "ok": False, "evento": "sin_dispositivo",
                    "error": "No hay ningún dispositivo LED conectado. Escaneá y conectá uno."
                }))
                continue

            # ── Comandos BLE ──────────────────────────────────────

            if comando == "encender":
                await tira.encender()
                await websocket.send(json.dumps({"ok": True, "evento": "encendido"}))

            elif comando == "apagar":
                await tira.apagar()
                await websocket.send(json.dumps({"ok": True, "evento": "apagado"}))

            elif comando == "color":
                r = datos["r"]
                g = datos["g"]
                b = datos["b"]
                estado.set_base(r, g, b)
                if estado.flash_only and ritmo_activado:
                    estado.r_flash, estado.g_flash, estado.b_flash = r, g, b
                    await tira.color(r, g, b)
                    await asyncio.sleep(0.15)
                    await tira.color(r // 50 or 1, g // 50 or 1, b // 50 or 1)
                else:
                    # Selección manual: cambio instantáneo (responsivo al arrastrar).
                    # (motor.on_color refleja el color en el visual remoto)
                    await motor.aplicar(r, g, b)
                await websocket.send(json.dumps({
                    "ok": True, "evento": "color", "r": r, "g": g, "b": b
                }))

            elif comando == "brillo":
                valor = datos["valor"]
                await tira.brillo(valor)
                await websocket.send(json.dumps({
                    "ok": True, "evento": "brillo", "valor": valor
                }))

            elif comando == "temperatura":
                # Blanco cálido/frío. Se recibe la "calidez" 0-100 y se reparte.
                calidez = max(0, min(100, int(datos.get("calidez", 50))))
                await tira.temperatura(calidez, 100 - calidez)
                await websocket.send(json.dumps({
                    "ok": True, "evento": "temperatura", "calidez": calidez
                }))

            elif comando == "probar":
                await tira.probar_colores()
                await websocket.send(json.dumps({"ok": True, "evento": "prueba_completada"}))

            elif comando == "arcoiris":
                pasos = datos.get("pasos", 12)
                demora = datos.get("demora", 0.8)
                await tira.arcoiris(pasos, demora)
                await websocket.send(json.dumps({"ok": True, "evento": "arcoiris_completado"}))

            elif comando == "ping":
                await websocket.send(json.dumps({"ok": True, "evento": "pong"}))

            # ── Comandos Spotify ──────────────────────────────────

            elif comando == "spotify_login":
                if not spotify.tiene_credenciales():
                    await websocket.send(json.dumps({
                        "ok": False, "evento": "spotify_error",
                        "error": "No se pudo iniciar sesión con Spotify. Intentá de nuevo más tarde."
                    }))
                    continue

                # URL de autorización para abrir manualmente si el navegador no
                # se abre solo (el servidor local igual captura la respuesta).
                try:
                    url_login = spotify.obtener_url_auth()
                except Exception:
                    url_login = ""

                await websocket.send(json.dumps({
                    "ok": True, "evento": "spotify_esperando",
                    "mensaje": "Abriendo el navegador para iniciar sesión con Spotify…",
                    "url": url_login,
                }))

                asyncio.create_task(_auth_spotify_task(websocket, spotify))

            elif comando == "spotify_logout":
                spotify.cerrar_sesion()
                if tarea_sincronizacion:
                    tarea_sincronizacion.cancel()
                    tarea_sincronizacion = None
                sincronizando = False
                await websocket.send(json.dumps({
                    "ok": True, "evento": "spotify_desconectado"
                }))

            elif comando == "spotify_estado":
                await websocket.send(json.dumps({
                    "ok": True, "evento": "spotify_estado",
                    "autenticado": spotify.esta_autenticado(),
                    "sincronizando": sincronizando,
                    "modo": sync_modo,
                    "tiene_credenciales": spotify.tiene_credenciales(),
                    "ritmo_activado": ritmo_activado,
                    "ritmo_disponible": detector_ritmo.disponible,
                    "flash_color": {"r": estado.r_flash, "g": estado.g_flash, "b": estado.b_flash},
                    "flash_only": estado.flash_only,
                    "modo_deteccion": estado.modo_deteccion,
                    "ajustes": ajustes.to_dict(),
                    "dispositivo": info_dispositivo(),
                    "visual": visual_hub.info(),
                    "ambilight_activado": ambilight_activado,
                    "ambilight_disponible": capturador.disponible,
                    "ambiente_activado": ambiente_activado,
                    "ambiente_efecto": ambiente_efecto,
                }))

            elif comando == "spotify_info":
                cancion = await spotify.obtener_cancion_actual()
                if cancion:
                    caracteristicas = await spotify.obtener_caracteristicas(cancion["cancion_id"])
                    await websocket.send(json.dumps({
                        "ok": True, "evento": "spotify_info",
                        "cancion": cancion,
                        "caracteristicas": caracteristicas,
                    }))
                else:
                    await websocket.send(json.dumps({
                        "ok": True, "evento": "spotify_info",
                        "cancion": None, "caracteristicas": None
                    }))

            elif comando == "spotify_iniciar":
                if not spotify.esta_autenticado():
                    await websocket.send(json.dumps({
                        "ok": False, "evento": "spotify_error",
                        "error": "Primero conectá tu cuenta de Spotify."
                    }))
                    continue

                if tarea_sincronizacion:
                    tarea_sincronizacion.cancel()
                sync_modo = datos.get("modo", sync_modo)
                ajustes.set("sync_modo", sync_modo)
                sincronizando = True
                tarea_sincronizacion = asyncio.create_task(
                    bucle_sincronizacion(
                        websocket, estado, spotify, cache, ajustes, lambda: sync_modo
                    )
                )
                await websocket.send(json.dumps({
                    "ok": True, "evento": "spotify_sincronizando",
                    "modo": sync_modo
                }))

            elif comando == "spotify_detener":
                if tarea_sincronizacion:
                    tarea_sincronizacion.cancel()
                    tarea_sincronizacion = None
                sincronizando = False
                await websocket.send(json.dumps({
                    "ok": True, "evento": "spotify_detenido"
                }))

            elif comando == "spotify_modo":
                sync_modo = datos.get("modo", "portada")
                ajustes.set("sync_modo", sync_modo)
                if sincronizando:
                    await websocket.send(json.dumps({
                        "ok": True, "evento": "spotify_modo_cambiado",
                        "modo": sync_modo
                    }))
                else:
                    await websocket.send(json.dumps({
                        "ok": True, "evento": "spotify_modo_cambiado",
                        "modo": sync_modo,
                        "nota": "Modo guardado. Inicia sincronización para activarlo."
                    }))

            # ── Comandos Ritmo ─────────────────────────────────────

            elif comando == "ritmo_iniciar":
                if not detector_ritmo.disponible:
                    await websocket.send(json.dumps({
                        "ok": False, "evento": "ritmo_error",
                        "error": "No se pudo acceder al audio del equipo. Activá la mezcla estéreo en la configuración de sonido de Windows."
                    }))
                    continue

                ok = detector_ritmo.iniciar()
                if ok:
                    ritmo_activado = True
                    visual_hub.set_ritmo(True)
                    if tarea_ritmo:
                        tarea_ritmo.cancel()
                    tarea_ritmo = asyncio.create_task(
                        _bucle_ritmo(websocket, estado, detector_ritmo)
                    )
                    await websocket.send(json.dumps({
                        "ok": True, "evento": "ritmo_activado"
                    }))
                else:
                    await websocket.send(json.dumps({
                        "ok": False, "evento": "ritmo_error",
                        "error": "No se pudo iniciar la captura de audio"
                    }))

            elif comando == "ritmo_detener":
                ritmo_activado = False
                visual_hub.set_ritmo(False)
                detector_ritmo.detener()
                if estado.tarea_pulso and not estado.tarea_pulso.done():
                    estado.tarea_pulso.cancel()
                    estado.tarea_pulso = None
                if tarea_ritmo:
                    tarea_ritmo.cancel()
                    tarea_ritmo = None
                await tira.color(estado.r_base, estado.g_base, estado.b_base)
                await websocket.send(json.dumps({
                    "ok": True, "evento": "ritmo_detenido"
                }))

            # ── Comandos Ambiente (efectos para el silencio) ──────────

            elif comando == "ambiente_iniciar":
                ef = datos.get("efecto", ambiente_efecto)
                ambiente_efecto = ef if ef in EFECTOS_AMBIENTE else "respiracion"
                ambiente_activado = True
                if tarea_ambiente:
                    tarea_ambiente.cancel()
                tarea_ambiente = asyncio.create_task(
                    _bucle_ambiente(websocket, estado, motor, lambda: ambiente_efecto)
                )
                await websocket.send(json.dumps({
                    "ok": True, "evento": "ambiente_iniciado", "efecto": ambiente_efecto
                }))

            elif comando == "ambiente_efecto":
                ef = datos.get("efecto", ambiente_efecto)
                if ef in EFECTOS_AMBIENTE:
                    ambiente_efecto = ef
                await websocket.send(json.dumps({
                    "ok": True, "evento": "ambiente_efecto_cambiado", "efecto": ambiente_efecto
                }))

            elif comando == "ambiente_detener":
                ambiente_activado = False
                if tarea_ambiente:
                    tarea_ambiente.cancel()
                    tarea_ambiente = None
                await websocket.send(json.dumps({
                    "ok": True, "evento": "ambiente_detenido"
                }))

            elif comando == "ritmo_flash_color":
                estado.r_flash = datos.get("r", 255)
                estado.g_flash = datos.get("g", 255)
                estado.b_flash = datos.get("b", 255)
                await websocket.send(json.dumps({
                    "ok": True, "evento": "ritmo_flash_color_actualizado",
                    "r": estado.r_flash, "g": estado.g_flash, "b": estado.b_flash
                }))

            elif comando == "ritmo_modo_deteccion":
                modo = datos.get("modo", "kick")
                if modo in ("kick", "bass", "full"):
                    estado.modo_deteccion = modo
                    detector_ritmo.modo = modo
                await websocket.send(json.dumps({
                    "ok": True, "evento": "ritmo_modo_deteccion_actualizado",
                    "modo": estado.modo_deteccion
                }))

            elif comando == "ritmo_flash_only":
                estado.flash_only = datos.get("activado", False)
                if estado.flash_only:
                    await tira.color(
                        estado.r_flash // 50 or 1,
                        estado.g_flash // 50 or 1,
                        estado.b_flash // 50 or 1,
                    )
                else:
                    await tira.color(estado.r_base, estado.g_base, estado.b_base)
                await websocket.send(json.dumps({
                    "ok": True, "evento": "ritmo_flash_only_actualizado",
                    "flash_only": estado.flash_only
                }))

            # ── Comandos Ajustes ───────────────────────────────────

            elif comando == "ajustes_obtener":
                await websocket.send(json.dumps({
                    "ok": True, "evento": "ajustes", "ajustes": ajustes.to_dict()
                }))

            elif comando == "ajustes_guardar":
                cambios = datos.get("cambios", {})
                resultado = ajustes.actualizar(cambios)
                motor.set_fps(resultado.get("fps_transicion", motor.fps))
                visual_hub.set_titulo(cfg_titulo())
                # No pisar el reloj/tarjeta del timer en el remoto.
                if not (temporizador.activo and timer_visual_usar):
                    visual_hub.set_visual(ajustes.get("visual_tipo"), ajustes.get("visual_movimiento"), cfg_portada())
                await websocket.send(json.dumps({
                    "ok": True, "evento": "ajustes", "ajustes": resultado
                }))

            elif comando == "ajustes_reset":
                resultado = ajustes.resetear()
                motor.set_fps(resultado.get("fps_transicion", motor.fps))
                visual_hub.set_titulo(cfg_titulo())
                if not (temporizador.activo and timer_visual_usar):
                    visual_hub.set_visual(ajustes.get("visual_tipo"), ajustes.get("visual_movimiento"), cfg_portada())
                detector_ritmo.set_sensibilidad_impacto(ajustes.get("ambilight_sensibilidad_audio"))
                capturador.configurar(
                    fps=ajustes.get("ambilight_fps"),
                    suavizado=ajustes.get("ambilight_suavizado"),
                    saturacion=ajustes.get("ambilight_saturacion"),
                    peso_bordes=ajustes.get("ambilight_peso_bordes"),
                    peso_dominante=ajustes.get("ambilight_peso_dominante"),
                    monitor=ajustes.get("ambilight_monitor"),
                )
                await websocket.send(json.dumps({
                    "ok": True, "evento": "ajustes", "ajustes": resultado, "reseteado": True
                }))

            # ── Comandos Cache de colores ──────────────────────────

            elif comando == "cache_listar":
                await websocket.send(json.dumps({
                    "ok": True, "evento": "cache_lista",
                    "canciones": cache.listar()
                }))

            elif comando == "cache_editar":
                cancion_id = datos.get("cancion_id")
                r = datos.get("r", 0)
                g = datos.get("g", 0)
                b = datos.get("b", 0)
                if not cancion_id or not cache.existe(cancion_id):
                    await websocket.send(json.dumps({
                        "ok": False, "error": "La canción no está en el cache"
                    }))
                    continue
                color = cache.guardar_usuario(cancion_id, r, g, b)
                # Si es la canción sonando, aplica el color al instante.
                if cancion_id == estado.cancion_actual_id:
                    estado.set_base(*color)
                    if ajustes.es_gradiente:
                        await motor.crossfade(*color, duracion=ajustes.get("duracion_crossfade"))
                    else:
                        await motor.aplicar(*color)
                await websocket.send(json.dumps({
                    "ok": True, "evento": "cache_editado",
                    "cancion_id": cancion_id, "r": color[0], "g": color[1], "b": color[2],
                    "canciones": cache.listar(),
                }))

            elif comando == "cache_eliminar":
                cancion_id = datos.get("cancion_id")
                existia = cache.eliminar(cancion_id)
                await websocket.send(json.dumps({
                    "ok": existia, "evento": "cache_eliminado",
                    "cancion_id": cancion_id,
                    "canciones": cache.listar(),
                }))

            elif comando == "cache_limpiar":
                cache.limpiar()
                await websocket.send(json.dumps({
                    "ok": True, "evento": "cache_limpiado", "canciones": []
                }))

            # ── Comandos Dispositivo BLE ───────────────────────────

            elif comando == "escanear":
                try:
                    lista = await TiraLED.escanear_todos(datos.get("tiempo", 8))
                    await websocket.send(json.dumps({
                        "ok": True, "evento": "dispositivos", "lista": lista
                    }))
                except Exception:
                    await websocket.send(json.dumps({
                        "ok": False, "evento": "dispositivos",
                        "error": "No se pudo buscar dispositivos. Intentá de nuevo.", "lista": []
                    }))

            elif comando == "conectar_dispositivo":
                nueva_mac = datos.get("direccion")
                if not nueva_mac:
                    await websocket.send(json.dumps({
                        "ok": False, "evento": "dispositivo_conectado",
                        "error": "No se pudo conectar con el dispositivo. Intentá de nuevo."
                    }))
                    continue
                try:
                    # Desconecta el anterior si había uno real.
                    try:
                        if dispositivo_conectado:
                            await tira.desconectar()
                    except Exception:
                        pass
                    await conectar_a(nueva_mac)
                    cfg = cargar_config()
                    cfg["direccion_mac"] = nueva_mac
                    guardar_config(cfg)
                    await websocket.send(json.dumps({
                        "ok": True, "evento": "dispositivo_conectado",
                        "dispositivo": info_dispositivo()
                    }))
                except Exception:
                    dispositivo_conectado = False
                    await websocket.send(json.dumps({
                        "ok": False, "evento": "dispositivo_conectado",
                        "error": "No se pudo conectar con el dispositivo. Intentá de nuevo.",
                        "dispositivo": info_dispositivo()
                    }))

            elif comando == "dispositivo_estado":
                await websocket.send(json.dumps({
                    "ok": True, "evento": "dispositivo", "dispositivo": info_dispositivo()
                }))

            # ── Comandos Visual remoto ─────────────────────────────

            elif comando == "visual_iniciar":
                info = await visual_hub.iniciar()
                # Sincroniza el estado actual de inmediato.
                visual_hub.set_color(estado.r_base, estado.g_base, estado.b_base)
                visual_hub.set_ritmo(ritmo_activado)
                visual_hub.set_titulo(cfg_titulo())
                visual_hub.set_visual(ajustes.get("visual_tipo"), ajustes.get("visual_movimiento"), cfg_portada())
                if estado.cancion_actual_id:
                    visual_hub.set_cancion(estado.cancion_nombre, estado.cancion_artista, estado.cancion_portada)
                await websocket.send(json.dumps({
                    "ok": True, "evento": "visual", **info
                }))

            elif comando == "visual_detener":
                visual_hub.detener()
                await websocket.send(json.dumps({
                    "ok": True, "evento": "visual", **visual_hub.info()
                }))

            elif comando == "visual_estado":
                await websocket.send(json.dumps({
                    "ok": True, "evento": "visual", **visual_hub.info()
                }))

            # ── Comandos Cine Mode (ambilight) ─────────────────────

            elif comando == "ambilight_monitores":
                await websocket.send(json.dumps({
                    "ok": True, "evento": "ambilight_monitores",
                    "monitores": listar_monitores()
                }))

            elif comando == "ambilight_iniciar":
                if not capturador.disponible:
                    await websocket.send(json.dumps({
                        "ok": False, "evento": "ambilight_error",
                        "error": "La captura de pantalla no está disponible en este equipo."
                    }))
                    continue
                if not dispositivo_conectado:
                    await websocket.send(json.dumps({
                        "ok": False, "evento": "ambilight_error",
                        "error": "Conectá un dispositivo LED primero"
                    }))
                    continue
                # Exclusión mutua con la sincronización de Spotify.
                if tarea_sincronizacion:
                    tarea_sincronizacion.cancel()
                    tarea_sincronizacion = None
                    sincronizando = False
                capturador.configurar(
                    fps=ajustes.get("ambilight_fps"),
                    suavizado=ajustes.get("ambilight_suavizado"),
                    saturacion=ajustes.get("ambilight_saturacion"),
                    peso_bordes=ajustes.get("ambilight_peso_bordes"),
                    peso_dominante=ajustes.get("ambilight_peso_dominante"),
                    monitor=ajustes.get("ambilight_monitor"),
                )
                capturador.iniciar()
                ambilight_uso_audio = bool(ajustes.get("ambilight_reactivo_audio")) and detector_ritmo.disponible
                if ambilight_uso_audio:
                    detector_ritmo.set_sensibilidad_impacto(ajustes.get("ambilight_sensibilidad_audio"))
                    if not ritmo_activado:
                        detector_ritmo.iniciar()
                ambilight_activado = True
                if tarea_ambilight:
                    tarea_ambilight.cancel()
                tarea_ambilight = asyncio.create_task(
                    _bucle_ambilight(websocket, estado, capturador,
                                     detector_ritmo if ambilight_uso_audio else None, ajustes)
                )
                await websocket.send(json.dumps({"ok": True, "evento": "ambilight_activado"}))

            elif comando == "ambilight_detener":
                ambilight_activado = False
                if tarea_ambilight:
                    tarea_ambilight.cancel()
                    tarea_ambilight = None
                capturador.detener()
                # Detener el detector solo si lo arrancó ambilight (no el modo ritmo).
                if ambilight_uso_audio and not ritmo_activado:
                    detector_ritmo.detener()
                ambilight_uso_audio = False
                await tira.color(estado.r_base, estado.g_base, estado.b_base)
                await websocket.send(json.dumps({"ok": True, "evento": "ambilight_detenido"}))

            elif comando == "ambilight_config":
                cambios = datos.get("cambios", {})
                ajustes.actualizar({k: v for k, v in cambios.items() if k.startswith("ambilight_")})
                if "ambilight_sensibilidad_audio" in cambios:
                    detector_ritmo.set_sensibilidad_impacto(ajustes.get("ambilight_sensibilidad_audio"))
                capturador.configurar(
                    fps=ajustes.get("ambilight_fps"),
                    suavizado=ajustes.get("ambilight_suavizado"),
                    saturacion=ajustes.get("ambilight_saturacion"),
                    peso_bordes=ajustes.get("ambilight_peso_bordes"),
                    peso_dominante=ajustes.get("ambilight_peso_dominante"),
                    monitor=ajustes.get("ambilight_monitor"),
                )
                await websocket.send(json.dumps({
                    "ok": True, "evento": "ajustes", "ajustes": ajustes.to_dict()
                }))

            # ── Comandos Timer ───────────────────────────────────────

            elif comando == "timer_iniciar":
                tiempo = int(datos.get("tiempo", 1500))
                color = datos.get("color", {"r": 255, "g": 0, "b": 0})
                accion = datos.get("accion", "blink")
                vis_cfg = datos.get("visual") or {}
                timer_visual_tipo = vis_cfg.get("tipo", timer_visual_tipo)
                timer_visual_usar = bool(vis_cfg.get("usar", True))
                if isinstance(vis_cfg.get("fondo"), dict):
                    f = vis_cfg["fondo"]
                    timer_fondo = {
                        "r": int(f.get("r", 10)),
                        "g": int(f.get("g", 10)),
                        "b": int(f.get("b", 30)),
                    }
                await temporizador.iniciar(tiempo, color, accion)
                _timer_push_visual()  # refleja el reloj/tarjeta en el remoto
                await websocket.send(json.dumps({
                    "ok": True, "evento": "timer_iniciado",
                    "tiempo": tiempo, "color": color, "accion": accion,
                }))

            elif comando == "timer_visual":
                # Cambio en vivo del visual del timer (desde la sección Visuales).
                timer_visual_tipo = datos.get("tipo", timer_visual_tipo)
                timer_visual_usar = bool(datos.get("usar", True))
                if isinstance(datos.get("fondo"), dict):
                    f = datos["fondo"]
                    timer_fondo = {
                        "r": int(f.get("r", 10)),
                        "g": int(f.get("g", 10)),
                        "b": int(f.get("b", 30)),
                    }
                if temporizador.activo:
                    _timer_push_visual()
                await websocket.send(json.dumps({
                    "ok": True, "evento": "timer_visual_actualizado",
                    "tipo": timer_visual_tipo, "usar": timer_visual_usar,
                }))

            elif comando == "timer_pausar":
                await temporizador.pausar()
                await websocket.send(json.dumps({
                    "ok": True, "evento": "timer_pausado",
                }))

            elif comando == "timer_reanudar":
                await temporizador.reanudar()
                await websocket.send(json.dumps({
                    "ok": True, "evento": "timer_reanudado",
                }))

            elif comando == "timer_detener":
                temporizador.detener()
                await websocket.send(json.dumps({
                    "ok": True, "evento": "timer_detenido",
                }))

            else:
                await websocket.send(json.dumps({
                    "ok": False, "error": f"Comando desconocido: {comando}"
                }))

    except websockets.exceptions.ConnectionClosed:
        print("Cliente desconectado.")
    finally:
        if tarea_sincronizacion:
            tarea_sincronizacion.cancel()
        ritmo_activado = False
        detector_ritmo.detener()
        if estado.tarea_pulso and not estado.tarea_pulso.done():
            estado.tarea_pulso.cancel()
            estado.tarea_pulso = None
        if tarea_ritmo:
            tarea_ritmo.cancel()
            tarea_ritmo = None
        temporizador.detener()
        ambilight_activado = False
        capturador.detener()
        if tarea_ambilight:
            tarea_ambilight.cancel()
            tarea_ambilight = None
        if tarea_ambiente:
            tarea_ambiente.cancel()
            tarea_ambiente = None
        await tira.desconectar()


EFECTOS_AMBIENTE = ("respiracion", "pulso", "vela", "fuego", "ciclo")


def _color_base_ambiente(estado: EstadoLED) -> tuple[int, int, int]:
    """Color sobre el que respiran/pulsan los efectos (cálido si está en negro)."""
    if estado.r_base or estado.g_base or estado.b_base:
        return (estado.r_base, estado.g_base, estado.b_base)
    return (255, 150, 60)


def _escala_rgb(col: tuple[int, int, int], f: float) -> tuple[int, int, int]:
    f = max(0.0, min(1.0, f))
    return (int(col[0] * f), int(col[1] * f), int(col[2] * f))


async def _bucle_ambiente(websocket, estado: EstadoLED, motor, obtener_efecto):
    """Efectos de ambiente para el silencio (sin música): respiración, pulso,
    vela, fuego y ciclo de color. Cambia el color de la tira de forma continua.
    """
    fps = 20
    t0 = time.time()
    flick = 1.0        # nivel actual del titileo (vela/fuego)
    flick_obj = 1.0    # objetivo del titileo
    try:
        while True:
            ahora = time.time() - t0
            efecto = obtener_efecto()

            if efecto == "respiracion":
                base = _color_base_ambiente(estado)
                f = 0.12 + 0.88 * (0.5 + 0.5 * math.sin(ahora * (2 * math.pi / 6.0)))
                r, g, b = _escala_rgb(base, f)
            elif efecto == "pulso":
                base = _color_base_ambiente(estado)
                s = 0.5 + 0.5 * math.sin(ahora * (2 * math.pi / 3.2))
                f = 0.08 + 0.92 * (s * s)  # curva más marcada que la respiración
                r, g, b = _escala_rgb(base, f)
            elif efecto == "ciclo":
                h = (ahora / 45.0 % 1.0) * 360.0
                r, g, b = _hsv_a_rgb(h, 0.85, 0.9)
            else:  # vela / fuego
                if efecto == "fuego":
                    lo, hi, col = 0.32, 1.0, (255, 65, 10)
                else:  # vela
                    lo, hi, col = 0.5, 1.0, (255, 130, 40)
                if random.random() < 0.25:
                    flick_obj = random.uniform(lo, hi)
                flick += (flick_obj - flick) * 0.35
                jitter = 1.0 + random.uniform(-0.05, 0.05)
                r, g, b = _escala_rgb(col, flick * jitter)

            await motor.aplicar(r, g, b)
            await asyncio.sleep(1.0 / fps)
    except asyncio.CancelledError:
        pass


async def _bucle_ritmo(websocket, estado: EstadoLED, detector):
    """Monitorea beats y pulsa dinámicamente según energía (rango 0-100%).

    El bucle NO termina en silencios: se mantiene activo (LED apagado) y vuelve
    a reaccionar en cuanto haya música. Solo se detiene con ritmo_detener.
    """
    import time
    _ultimo_beat = time.time()      # evita apagar/salir en el arranque
    _silencio_contador = 0
    _apagado = False                # evita reenviar (0,0,0) en bucle

    async def _apagar():
        nonlocal _apagado
        if not _apagado:
            await estado.tira.color(0, 0, 0)
            _apagado = True

    try:
        while True:
            ahora = time.time()
            beat_info = detector.get_beat_info()

            if beat_info.get("is_silent", False):
                _silencio_contador += 1
                if _silencio_contador > 2:
                    if estado.tarea_pulso and not estado.tarea_pulso.done():
                        estado.tarea_pulso.cancel()
                        estado.tarea_pulso = None
                    await _apagar()
                await asyncio.sleep(0.01)
                continue
            else:
                _silencio_contador = 0

            energy_intensity = beat_info.get("energy_intensity", 0.0)

            if detector.hubo_beat:
                if estado.tarea_pulso and not estado.tarea_pulso.done():
                    estado.tarea_pulso.cancel()
                estado.tarea_pulso = asyncio.create_task(
                    _pulso_beat(estado, energy_intensity=energy_intensity)
                )
                _ultimo_beat = ahora
                _apagado = False
                # Difunde el beat al visual remoto y a la app.
                visual_hub.pulse(energy_intensity)
                await _enviar_json(websocket, {
                    "ok": True, "evento": "beat", "energy": round(energy_intensity, 3)
                })

            elif ahora - _ultimo_beat > 2.0:
                # Mucho rato sin beats: apaga pero SIGUE escuchando.
                if estado.tarea_pulso and not estado.tarea_pulso.done():
                    estado.tarea_pulso.cancel()
                    estado.tarea_pulso = None
                await _apagar()

            else:
                if energy_intensity < 0.15:
                    if not (estado.tarea_pulso and not estado.tarea_pulso.done()):
                        await _apagar()
                elif energy_intensity < 0.4:
                    if not (estado.tarea_pulso and not estado.tarea_pulso.done()):
                        intensity = energy_intensity
                        await estado.tira.color(
                            int(estado.r_base * intensity),
                            int(estado.g_base * intensity),
                            int(estado.b_base * intensity),
                        )
                        _apagado = False
                elif energy_intensity < 0.7:
                    if not (estado.tarea_pulso and not estado.tarea_pulso.done()):
                        await estado.tira.color(estado.r_base, estado.g_base, estado.b_base)
                        _apagado = False

            await asyncio.sleep(0.01)
    except asyncio.CancelledError:
        pass


def _mapear_intensidad(luminancia, saturacion, imin, imax):
    """Escena oscura → tenue; brillante/vívida → intensa."""
    nivel = max(0.0, min(1.0, (luminancia ** 0.7) * 0.8 + saturacion * 0.2))
    return imin + (imax - imin) * nivel


async def _bucle_ambilight(websocket, estado: EstadoLED, capturador, detector, ajustes):
    """Cine Mode: fusiona color de pantalla + audio y aplica un color ambiente.

    - Color base = color de la escena escalado por una intensidad que sube con la
      luminancia/saturación (mar oscuro → tenue; cielo/sol → intenso).
    - Si hay audio (detector), la energía sube la intensidad y cada beat/onset
      dispara un flash teñido con el color de la escena (explosión, pasos, screamer).
    - Si la captura sale negra (DRM), degrada a solo-audio con un tono cálido tenue.
    """
    motor = estado.motor
    try:
        while True:
            info = capturador.get_color_info()
            r, g, b = info["r"], info["g"], info["b"]
            imin = ajustes.get("ambilight_intensidad_min")
            imax = ajustes.get("ambilight_intensidad_max")
            intensidad = _mapear_intensidad(info["luminancia"], info["saturacion"], imin, imax)
            fps = max(10, int(ajustes.get("ambilight_fps")))

            energia = 0.0
            hubo = False
            silencio = False
            fuerza = 0.0
            if detector is not None:
                # Cine Mode usa el detector de IMPACTOS (golpes fuertes repentinos),
                # con nivel refrescado cada frame — no los beats musicales.
                ii = detector.get_impacto_info()
                silencio = ii.get("silencio", False)
                energia = ii.get("nivel", 0.0)
                hubo = detector.hubo_impacto
                fuerza = ii.get("fuerza", 0.0)

            # Captura negra (DRM): usar solo audio si hay.
            if info.get("drm_negro"):
                if detector is not None and not silencio and energia > 0.05:
                    calido = (255, 120, 40)
                    inten = imin + (imax - imin) * energia
                    obj = tuple(int(c * inten) for c in calido)
                    await motor.aplicar(*obj)
                else:
                    await motor.aplicar(0, 0, 0)
                estado.set_base(motor.r, motor.g, motor.b)
                await _enviar_json(websocket, {
                    "ok": True, "evento": "ambilight_color",
                    "r": motor.r, "g": motor.g, "b": motor.b,
                    "intensidad": round(intensidad, 3), "drm": True,
                })
                await asyncio.sleep(1.0 / fps)
                continue

            # El audio sube la intensidad del ambiente.
            if detector is not None:
                intensidad = max(intensidad, energia)

            r2 = int(r * intensidad)
            g2 = int(g * intensidad)
            b2 = int(b * intensidad)

            if detector is not None and hubo:
                # Flash: color de escena a intensidad alta (instantáneo), según la
                # fuerza del impacto (golpe leve = destello suave; fuerte = full).
                inten_flash = min(1.0, intensidad + 0.35 + 0.65 * fuerza)
                await motor.aplicar(int(r * inten_flash), int(g * inten_flash), int(b * inten_flash))
            else:
                await motor.aplicar(r2, g2, b2)

            estado.set_base(r2, g2, b2)
            await _enviar_json(websocket, {
                "ok": True, "evento": "ambilight_color",
                "r": motor.r, "g": motor.g, "b": motor.b,
                "intensidad": round(intensidad, 3), "drm": False,
            })
            await asyncio.sleep(1.0 / fps)
    except asyncio.CancelledError:
        pass


async def bucle_sincronizacion(websocket, estado: EstadoLED, spotify, cache, ajustes, obtener_modo):
    """Monitorea Spotify y cambia el color de la tira con transiciones suaves.

    - Cache HIT  → transición directa color→color.
    - Cache MISS → baja el brillo mientras analiza la portada, luego sube el
      brillo con el color nuevo (y lo guarda en cache).
    El modo (gradiente/brusco) sale de los ajustes del usuario.
    """
    motor = estado.motor
    cancion_anterior_id = None

    def _intervalo(cancion):
        """Polling adaptativo: rápido cerca del final de la canción."""
        base = ajustes.get("intervalo_spotify")
        if cancion and cancion.get("reproduciendo", True):
            dur = cancion.get("duration_ms", 0) or 0
            prog = cancion.get("progress_ms", 0) or 0
            if dur and prog:
                restante = (dur - prog) / 1000.0
                if 0 <= restante < 2.5:
                    return 0.3
        return base

    try:
        while True:
            spotify.refrescar_token()

            cancion = await spotify.obtener_cancion_actual()
            if cancion and cancion["cancion_id"] != cancion_anterior_id:
                cancion_anterior_id = cancion["cancion_id"]
                estado.cancion_actual_id = cancion["cancion_id"]
                estado.cancion_nombre = cancion.get("nombre", "")
                estado.cancion_artista = cancion.get("artista", "")
                estado.cancion_portada = cancion.get("url_portada", "")
                modo = obtener_modo()
                gradiente = ajustes.es_gradiente

                color_cache = cache.obtener_color(cancion["cancion_id"])

                if color_cache is not None:
                    # ── CACHE HIT: cambio directo de un color a otro ──
                    r, g, b = color_cache
                    if gradiente:
                        await motor.crossfade(r, g, b, duracion=ajustes.get("duracion_crossfade"))
                    else:
                        await motor.aplicar(r, g, b)
                    estado.set_base(r, g, b)
                    fuente = "usuario" if cache.es_de_usuario(cancion["cancion_id"]) else "cache"
                    await _notificar_color(websocket, cancion, r, g, b, fuente)
                    await asyncio.sleep(_intervalo(cancion))
                    continue

                # ── CACHE MISS: bajar brillo mientras analiza, subir con color nuevo ──
                base_previa = motor.color_actual
                tarea_fade_out = None
                if gradiente:
                    tarea_fade_out = asyncio.create_task(
                        motor.fade_a_negro(duracion=ajustes.get("duracion_fade_out"))
                    )

                color = await calcular_color_cancion(spotify, cancion, modo)

                if gradiente and tarea_fade_out is not None:
                    # Asegura que el fade a negro terminó antes de subir de nuevo.
                    try:
                        await tarea_fade_out
                    except asyncio.CancelledError:
                        pass

                if color is None:
                    # No se pudo calcular: vuelve a la base previa (no cachea).
                    if gradiente:
                        await motor.crossfade(*base_previa, duracion=ajustes.get("duracion_fade_in"))
                    continue

                r, g, b = color
                # Guarda en cache (respeta un posible color de usuario previo).
                r, g, b = cache.guardar_auto(
                    cancion["cancion_id"], r, g, b,
                    cancion.get("nombre", ""), cancion.get("artista", ""),
                )

                if gradiente:
                    await motor.fade_desde_negro(r, g, b, duracion=ajustes.get("duracion_fade_in"))
                else:
                    await motor.aplicar(r, g, b)

                estado.set_base(r, g, b)
                fuente = "usuario" if cache.es_de_usuario(cancion["cancion_id"]) else "auto"
                await _notificar_color(websocket, cancion, r, g, b, fuente)

            elif cancion is None:
                cancion_anterior_id = None
                estado.cancion_actual_id = None

            await asyncio.sleep(_intervalo(cancion))

    except asyncio.CancelledError:
        print("Sincronización detenida.")


async def _notificar_color(websocket, cancion, r, g, b, fuente):
    visual_hub.set_cancion(cancion.get("nombre", ""), cancion.get("artista", ""),
                           cancion.get("url_portada", ""))
    await _enviar_json(websocket, {
        "ok": True, "evento": "spotify_color",
        "r": r, "g": g, "b": b,
        "cancion": cancion.get("nombre", ""),
        "artista": cancion.get("artista", ""),
        "cancion_id": cancion.get("cancion_id", ""),
        "url_portada": cancion.get("url_portada", ""),
        "fuente": fuente,
    })


def mapear_caracteristicas_a_rgb(caracteristicas: dict) -> tuple[int, int, int]:
    """Convierte características de audio en un color RGB.

    - energia → brillo (0-255)
    - valencia → matiz (0=azul frío, 1=rojo cálido)
    - bailabilidad → qué tanto mezclar con blanco
    """
    energia = caracteristicas.get("energia", 0.5)
    valencia = caracteristicas.get("valencia", 0.5)
    bailabilidad = caracteristicas.get("bailabilidad", 0.5)

    matiz = int(240 - (valencia * 240))
    saturacion = 200 + int(bailabilidad * 55)
    brillo = max(50, int(energia * 255))

    return hsv_a_rgb(matiz % 360, min(saturacion, 255), min(brillo, 255))


def hsv_a_rgb(h: int, s: int, v: int) -> tuple[int, int, int]:
    """Convierte HSV (h=0-360, s=0-255, v=0-255) a RGB."""
    if s == 0:
        return (v, v, v)

    region = h // 60
    resto = h % 60
    p = v * (255 - s) // 255
    q = v * (255 - (s * resto) // 60) // 255
    t = v * (255 - (s * (60 - resto)) // 60) // 255

    return [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)][region % 6]


async def _auth_spotify_task(websocket, spotify):
    """Ejecuta la autenticación en segundo plano y notifica al frontend."""
    try:
        exitoso = await spotify.autenticar()
        if exitoso:
            await _enviar_json(websocket, {"ok": True, "evento": "spotify_autenticado"})
        else:
            await _enviar_json(websocket, {
                "ok": False, "evento": "spotify_error",
                "error": "No se pudo conectar con Spotify. Intentá de nuevo."
            })
    except Exception:
        await _enviar_json(websocket, {
            "ok": False, "evento": "spotify_error",
            "error": "No se pudo conectar con Spotify. Intentá de nuevo."
        })


async def main():
    """Inicia el servidor WebSocket."""
    print(f"Servidor WebSocket iniciado en ws://localhost:{PUERTO}")
    async with websockets.serve(manejar_cliente, "localhost", PUERTO):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
