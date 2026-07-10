"""Pruebas del cache de colores por canción."""

from __future__ import annotations

import json

import pytest

from cache_colores import CacheColores, FUENTE_AUTO, FUENTE_USUARIO


@pytest.fixture
def ruta_cache(tmp_path):
    return str(tmp_path / "color_cache.json")


def test_vacio_devuelve_none(ruta_cache):
    cache = CacheColores(ruta_cache)
    assert cache.obtener("abc") is None
    assert cache.obtener_color("abc") is None
    assert len(cache) == 0


def test_guardar_auto_y_recuperar(ruta_cache):
    cache = CacheColores(ruta_cache)
    color = cache.guardar_auto("song1", 255, 0, 0, "Tema", "Artista")
    assert color == (255, 0, 0)
    assert cache.obtener_color("song1") == (255, 0, 0)
    entrada = cache.obtener("song1")
    assert entrada["fuente"] == FUENTE_AUTO
    assert entrada["nombre"] == "Tema"
    assert entrada["artista"] == "Artista"


def test_persistencia_en_disco(ruta_cache):
    cache = CacheColores(ruta_cache)
    cache.guardar_auto("song1", 10, 20, 30, "N", "A")
    # Nueva instancia leyendo el mismo archivo.
    cache2 = CacheColores(ruta_cache)
    assert cache2.obtener_color("song1") == (10, 20, 30)


def test_clamp_de_valores_fuera_de_rango(ruta_cache):
    cache = CacheColores(ruta_cache)
    color = cache.guardar_auto("s", 300, -5, 999)
    assert color == (255, 0, 255)


def test_usuario_tiene_prioridad_sobre_auto(ruta_cache):
    cache = CacheColores(ruta_cache)
    cache.guardar_auto("s", 255, 0, 0)
    cache.guardar_usuario("s", 0, 0, 255)
    assert cache.obtener_color("s") == (0, 0, 255)
    assert cache.es_de_usuario("s") is True

    # Un guardado automático posterior NO debe pisar el color del usuario.
    efectivo = cache.guardar_auto("s", 0, 255, 0, "Nuevo", "Art")
    assert efectivo == (0, 0, 255)
    assert cache.obtener_color("s") == (0, 0, 255)
    # Pero sí refresca metadatos.
    assert cache.obtener("s")["nombre"] == "Nuevo"


def test_guardar_usuario_conserva_metadatos_previos(ruta_cache):
    cache = CacheColores(ruta_cache)
    cache.guardar_auto("s", 1, 2, 3, "Tema", "Artista")
    cache.guardar_usuario("s", 9, 9, 9)
    entrada = cache.obtener("s")
    assert entrada["nombre"] == "Tema"
    assert entrada["artista"] == "Artista"
    assert entrada["fuente"] == FUENTE_USUARIO


def test_eliminar(ruta_cache):
    cache = CacheColores(ruta_cache)
    cache.guardar_auto("s", 1, 2, 3)
    assert cache.eliminar("s") is True
    assert cache.obtener("s") is None
    assert cache.eliminar("s") is False


def test_limpiar(ruta_cache):
    cache = CacheColores(ruta_cache)
    cache.guardar_auto("a", 1, 1, 1)
    cache.guardar_auto("b", 2, 2, 2)
    cache.limpiar()
    assert len(cache) == 0


def test_listar_ordenado_por_reciente(ruta_cache):
    cache = CacheColores(ruta_cache)
    cache.guardar_auto("viejo", 1, 1, 1)
    cache.guardar_auto("nuevo", 2, 2, 2)
    listado = cache.listar()
    assert [e["cancion_id"] for e in listado] == ["nuevo", "viejo"]
    assert all("cancion_id" in e for e in listado)


def test_archivo_corrupto_no_rompe(ruta_cache):
    with open(ruta_cache, "w", encoding="utf-8") as f:
        f.write("{esto no es json valido")
    cache = CacheColores(ruta_cache)  # no debe lanzar
    assert len(cache) == 0
    cache.guardar_auto("s", 1, 2, 3)
    assert cache.obtener_color("s") == (1, 2, 3)


def test_entrada_incompleta_se_ignora(ruta_cache):
    with open(ruta_cache, "w", encoding="utf-8") as f:
        json.dump({"malo": {"r": 1}, "bueno": {"r": 1, "g": 2, "b": 3}}, f)
    cache = CacheColores(ruta_cache)
    assert cache.obtener("malo") is None
    assert cache.obtener_color("bueno") == (1, 2, 3)


def test_autosave_desactivado(ruta_cache):
    cache = CacheColores(ruta_cache, autosave=False)
    cache.guardar_auto("s", 1, 2, 3)
    # Sin autosave el archivo no existe todavía.
    import os
    assert not os.path.exists(ruta_cache)
    cache.guardar()
    assert os.path.exists(ruta_cache)


def test_cancion_id_vacio_es_seguro(ruta_cache):
    cache = CacheColores(ruta_cache)
    assert cache.obtener("") is None
    assert cache.guardar_auto("", 1, 2, 3) == (1, 2, 3)
    assert len(cache) == 0
