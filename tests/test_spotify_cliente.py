"""Pruebas de restauración de sesión de Spotify desde la caché (sin red)."""

from __future__ import annotations

from spotify_cliente import ClienteSpotify


class _CacheHandler:
    def __init__(self, token):
        self._token = token

    def get_cached_token(self):
        return self._token


class _OAuthFake:
    def __init__(self, token=None, expirado=False):
        self.cache_handler = _CacheHandler(token)
        self._expirado = expirado
        self.refrescado = False

    def is_token_expired(self, token_info):
        return self._expirado

    def refresh_access_token(self, refresh_token):
        self.refrescado = True
        return {"access_token": "token_nuevo", "refresh_token": refresh_token}


def _cliente_con_oauth(oauth):
    c = ClienteSpotify("id", "secreto")
    c._crear_oauth = lambda: oauth
    return c


def test_sin_token_en_cache_no_autentica():
    c = _cliente_con_oauth(_OAuthFake(token=None))
    assert c.autenticar_desde_cache() is False
    assert c.esta_autenticado() is False


def test_token_valido_restaura_sesion():
    token = {"access_token": "abc", "refresh_token": "ref"}
    c = _cliente_con_oauth(_OAuthFake(token=token, expirado=False))
    assert c.autenticar_desde_cache() is True
    assert c.esta_autenticado() is True


def test_token_expirado_se_refresca():
    token = {"access_token": "viejo", "refresh_token": "ref"}
    oauth = _OAuthFake(token=token, expirado=True)
    c = _cliente_con_oauth(oauth)
    assert c.autenticar_desde_cache() is True
    assert oauth.refrescado is True
    assert c.esta_autenticado() is True


def test_sin_credenciales_no_autentica():
    c = ClienteSpotify("", "")
    assert c.autenticar_desde_cache() is False
