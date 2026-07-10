"""Cliente para la API de Spotify: autenticación (PKCE), track actual y features.

Usa el flujo **Authorization Code with PKCE**, pensado para apps instaladas en el
equipo del usuario: solo necesita el ``client_id`` (público), NO un
``client_secret``. Así el instalador puede traer horneado el ``client_id`` sin
exponer ningún secreto.

Flujo:
  1. autenticar() abre el navegador (Spotipy) y levanta un server local.
  2. El usuario acepta los permisos con SU cuenta de Spotify.
  3. Spotify redirige a http://127.0.0.1:8888/callback y se obtiene el token.
  El token queda cacheado (en la carpeta de datos) para no re-loguear cada vez.
"""

import asyncio
import json
import os
from typing import Optional

import spotipy
from spotipy.oauth2 import SpotifyPKCE

from rutas import ruta_datos


ALCANCES = "user-read-playback-state user-read-currently-playing"
REDIRECT_POR_DEFECTO = "http://127.0.0.1:8888/callback"

# client_id horneado (es público, no es un secreto). Se usa si no hay config.
CLIENTE_ID_POR_DEFECTO = "79c19a6f6db34dad9d69bfcb036233eb"


def cargar_config_spotify(ruta: str = "config.json") -> dict:
    """Lee el client_id de Spotify desde config.json, env, o el horneado.

    Con PKCE no hace falta client_secret; se mantiene la clave por
    compatibilidad, pero puede ir vacía.
    """
    cliente_id = ""
    cliente_secreto = ""
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
        cliente_id = datos.get("spotify_cliente_id", "")
        cliente_secreto = datos.get("spotify_cliente_secreto", "")

    cliente_id = cliente_id or os.getenv("SPOTIFY_CLIENTE_ID", "") or CLIENTE_ID_POR_DEFECTO
    cliente_secreto = cliente_secreto or os.getenv("SPOTIFY_CLIENTE_SECRETO", "")
    return {"cliente_id": cliente_id, "cliente_secreto": cliente_secreto}


class ClienteSpotify:
    """Maneja la autenticación (PKCE) y consultas a la API de Spotify."""

    def __init__(self, cliente_id: str, cliente_secreto: str = "", redirect_uri: str = REDIRECT_POR_DEFECTO) -> None:
        self._cliente_id = cliente_id
        self._cliente_secreto = cliente_secreto  # no se usa con PKCE (compat)
        self._redirect_uri = redirect_uri
        self._cache_path = ruta_datos(".spotify_cache")
        self._oauth: Optional[SpotifyPKCE] = None
        self._spotify: Optional[spotipy.Spotify] = None
        self._autenticado = False
        self._token_info = None

    def _crear_oauth(self) -> SpotifyPKCE:
        """Crea (o reusa) el objeto de autenticación PKCE."""
        if self._oauth is None:
            self._oauth = SpotifyPKCE(
                client_id=self._cliente_id,
                redirect_uri=self._redirect_uri,
                scope=ALCANCES,
                cache_path=self._cache_path,
                open_browser=True,
            )
        return self._oauth

    def tiene_credenciales(self) -> bool:
        """Con PKCE basta el client_id."""
        return bool(self._cliente_id)

    def obtener_url_auth(self) -> str:
        """Genera la URL que debe abrir el usuario en el navegador."""
        return self._crear_oauth().get_authorize_url()

    async def autenticar(self, url_callback=None) -> bool:
        """Inicia el flujo PKCE en un hilo separado (abre navegador)."""
        if not self.tiene_credenciales():
            return False

        def _bloqueante():
            token = self._crear_oauth().get_access_token()
            # SpotifyPKCE.get_access_token puede devolver el string del token.
            access = token["access_token"] if isinstance(token, dict) else token
            if access:
                self._token_info = token
                self._spotify = spotipy.Spotify(auth=access)
                self._autenticado = True
            return self._autenticado

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _bloqueante)

    def autenticar_desde_cache(self) -> bool:
        """Restaura la sesión desde la caché en disco SIN abrir el navegador."""
        if not self.tiene_credenciales():
            return False

        oauth = self._crear_oauth()
        token_info = None
        try:
            if hasattr(oauth, "cache_handler"):
                token_info = oauth.cache_handler.get_cached_token()
            else:  # compatibilidad con versiones viejas de spotipy
                token_info = oauth.get_cached_token()
        except Exception:
            token_info = None

        if not token_info:
            return False

        try:
            if oauth.is_token_expired(token_info):
                token_info = oauth.refresh_access_token(token_info["refresh_token"])
            self._token_info = token_info
            self._spotify = spotipy.Spotify(auth=token_info["access_token"])
            self._autenticado = True
            return True
        except Exception:
            return False

    async def obtener_cancion_actual(self) -> Optional[dict]:
        """Obtiene información del track que está sonando ahora."""
        if not self._autenticado or not self._spotify:
            return None

        def _bloqueante():
            try:
                resultado = self._spotify.current_user_playing_track()
                if resultado is None or resultado.get("item") is None:
                    return None

                item = resultado["item"]
                imagenes = item.get("album", {}).get("images", [])
                url_portada = imagenes[0]["url"] if imagenes else ""

                return {
                    "cancion_id": item["id"],
                    "nombre": item["name"],
                    "artista": ", ".join(a["name"] for a in item.get("artists", [])),
                    "url_portada": url_portada,
                    "reproduciendo": resultado.get("is_playing", False),
                    "progress_ms": resultado.get("progress_ms", 0) or 0,
                    "duration_ms": item.get("duration_ms", 0) or 0,
                }
            except spotipy.exceptions.SpotifyException:
                return None

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _bloqueante)

    async def obtener_caracteristicas(self, cancion_id: str) -> Optional[dict]:
        """Obtiene las características de audio de una canción."""
        if not self._autenticado or not self._spotify:
            return None

        def _bloqueante():
            try:
                features = self._spotify.audio_features(cancion_id)
                if features and features[0]:
                    f = features[0]
                    return {
                        "energia": f["energy"],
                        "valencia": f["valence"],
                        "bailabilidad": f["danceability"],
                        "tempo": f["tempo"],
                    }
            except spotipy.exceptions.SpotifyException:
                pass
            return None

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _bloqueante)

    def refrescar_token(self) -> None:
        """Refresca el token si está expirado."""
        if self._oauth and self._token_info:
            if self._oauth.is_token_expired(self._token_info):
                self._token_info = self._oauth.refresh_access_token(
                    self._token_info["refresh_token"]
                )
                access = (self._token_info["access_token"]
                          if isinstance(self._token_info, dict) else self._token_info)
                if self._spotify:
                    self._spotify.set_auth(access)

    def esta_autenticado(self) -> bool:
        return self._autenticado

    def cerrar_sesion(self) -> None:
        """Limpia la autenticación y borra la caché."""
        self._autenticado = False
        self._spotify = None
        self._token_info = None
        self._oauth = None
        if os.path.exists(self._cache_path):
            os.remove(self._cache_path)
