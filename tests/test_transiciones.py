"""Pruebas del motor de transiciones de color."""

from __future__ import annotations

import asyncio

import pytest

from transiciones import MotorTransiciones


async def test_aplicar_es_instantaneo(tira_fake):
    motor = MotorTransiciones(tira_fake, fps=30)
    await motor.aplicar(255, 100, 50)
    assert tira_fake.enviados == [(255, 100, 50)]
    assert motor.color_actual == (255, 100, 50)


async def test_crossfade_termina_en_destino(tira_fake):
    motor = MotorTransiciones(tira_fake, fps=30, r=0, g=0, b=0)
    await motor.crossfade(255, 0, 0, duracion=0.2)
    assert tira_fake.ultimo == (255, 0, 0)
    assert motor.color_actual == (255, 0, 0)
    # Debe haber pasos intermedios (no salta directo).
    assert len(tira_fake.enviados) > 1


async def test_crossfade_es_monotono(tira_fake):
    motor = MotorTransiciones(tira_fake, fps=30, r=0, g=0, b=0)
    await motor.crossfade(200, 0, 0, duracion=0.2)
    rojos = [c[0] for c in tira_fake.enviados]
    assert rojos == sorted(rojos)  # el canal R sube monótonamente
    assert rojos[-1] == 200


async def test_crossfade_duracion_cero_es_directo(tira_fake):
    motor = MotorTransiciones(tira_fake, fps=30)
    await motor.crossfade(10, 20, 30, duracion=0)
    assert tira_fake.enviados == [(10, 20, 30)]


async def test_crossfade_mismo_color_no_duplica(tira_fake):
    motor = MotorTransiciones(tira_fake, fps=30, r=50, g=50, b=50)
    await motor.crossfade(50, 50, 50, duracion=0.3)
    assert tira_fake.enviados == [(50, 50, 50)]


async def test_fade_a_negro(tira_fake):
    motor = MotorTransiciones(tira_fake, fps=30, r=255, g=255, b=255)
    await motor.fade_a_negro(duracion=0.15)
    assert tira_fake.ultimo == (0, 0, 0)
    assert motor.color_actual == (0, 0, 0)


async def test_fade_desde_negro(tira_fake):
    motor = MotorTransiciones(tira_fake, fps=30, r=120, g=0, b=0)
    await motor.fade_desde_negro(0, 0, 255, duracion=0.15)
    # Debe empezar oscuro y terminar en el color objetivo.
    assert tira_fake.enviados[0] != (0, 0, 255)
    assert tira_fake.ultimo == (0, 0, 255)


async def test_respeta_limite_de_fps(tira_fake):
    # 10 fps durante 1s => como máximo ~10 envíos aunque se pidan 1000 pasos.
    motor = MotorTransiciones(tira_fake, fps=10)
    await motor.crossfade(255, 255, 255, duracion=1.0, pasos=1000)
    assert len(tira_fake.enviados) <= 10


async def test_crossfade_cancelable_deja_estado_consistente(tira_fake):
    motor = MotorTransiciones(tira_fake, fps=30, r=0, g=0, b=0)
    tarea = asyncio.create_task(motor.crossfade(255, 255, 255, duracion=2.0))
    await asyncio.sleep(0.1)
    tarea.cancel()
    with pytest.raises(asyncio.CancelledError):
        await tarea
    # El estado interno coincide con el último color enviado.
    assert motor.color_actual == tira_fake.ultimo
    # No llegó hasta el final.
    assert tira_fake.ultimo != (255, 255, 255)


async def test_set_actual_no_envia(tira_fake):
    motor = MotorTransiciones(tira_fake, fps=30)
    motor.set_actual(10, 20, 30)
    assert tira_fake.enviados == []
    assert motor.color_actual == (10, 20, 30)


async def test_set_fps_actualiza_intervalo(tira_fake):
    motor = MotorTransiciones(tira_fake, fps=30)
    motor.set_fps(10)
    assert motor.fps == 10
    await motor.crossfade(255, 255, 255, duracion=1.0, pasos=1000)
    assert len(tira_fake.enviados) <= 10
