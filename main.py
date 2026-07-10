"""CLI para controlar tiras LED ELK-BLEDOM / Lotus Lantern vía Bluetooth LE.

Uso:
    python main.py scan                     Buscar dispositivos y guardar MAC
    python main.py on                       Encender tira LED
    python main.py off                      Apagar tira LED
    python main.py color <R> <G> <B>        Color RGB (0-255)
    python main.py brillo <0-255>           Ajustar brillo
    python main.py temperatura <cal> <frio> Temperatura de color (0-100 c/u)
    python main.py arcoiris [pasos] [delay] Recorrido de colores
    python main.py probar                   Probar paleta de colores
    python main.py variante <R> <G> <B>     Probar variantes del comando
"""

import asyncio
import json
import os
import sys


from led import TiraLED
from rutas import ruta_datos

RUTA_CONFIG = ruta_datos("config.json")


def cargar_config() -> dict:
    """Lee la configuración desde config.json."""
    if os.path.exists(RUTA_CONFIG):
        with open(RUTA_CONFIG, encoding="utf-8") as f:
            return json.load(f)
    return {"direccion_mac": None}


def guardar_config(config: dict) -> None:
    """Guarda la configuración en config.json."""
    with open(RUTA_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


async def cmd_escanear(_led: TiraLED, _args: list[str]) -> None:
    """Busca dispositivos BLE ELK-BLEDOM y guarda la MAC seleccionada."""
    print("Escaneando dispositivos BLE ...")
    dispositivos = await TiraLED.escanear(tiempo_limite=15)

    if not dispositivos:
        print("  No se encontraron dispositivos ELK-BLEDOM")
        return

    for i, d in enumerate(dispositivos):
        print(f"  [{i}] {d.name} - {d.address}")

    if len(dispositivos) == 1:
        config = cargar_config()
        config["direccion_mac"] = dispositivos[0].address
        guardar_config(config)
        print(f"\n  MAC guardada: {dispositivos[0].address}")
    else:
        try:
            indice = int(input("\nSelecciona el número: "))
            config = cargar_config()
            config["direccion_mac"] = dispositivos[indice].address
            guardar_config(config)
            print(f"  MAC guardada: {dispositivos[indice].address}")
        except (IndexError, ValueError):
            print("  Selección inválida")


async def cmd_encender(tira: TiraLED, _args: list[str]) -> None:
    """Enciende la tira LED."""
    await tira.encender()


async def cmd_apagar(tira: TiraLED, _args: list[str]) -> None:
    """Apaga la tira LED."""
    await tira.apagar()


async def cmd_color(tira: TiraLED, args: list[str]) -> None:
    """Cambia el color RGB."""
    if len(args) < 3:
        print("Uso: python main.py color <R> <G> <B>")
        return
    try:
        r, g, b = int(args[0]), int(args[1]), int(args[2])
        await tira.color(r, g, b)
    except ValueError:
        print("Los valores deben ser números enteros (0-255)")


async def cmd_brillo(tira: TiraLED, args: list[str]) -> None:
    """Ajusta el brillo."""
    if not args:
        print("Uso: python main.py brillo <0-255>")
        return
    try:
        valor = int(args[0])
        await tira.brillo(valor)
    except ValueError:
        print("El valor debe ser un número entero (0-255)")


async def cmd_temperatura(tira: TiraLED, args: list[str]) -> None:
    """Ajusta temperatura de color."""
    try:
        calido = int(args[0]) if len(args) > 0 else 50
        frio = int(args[1]) if len(args) > 1 else 50
        await tira.temperatura(calido, frio)
    except ValueError:
        print("Los valores deben ser números enteros (0-100)")


async def cmd_arcoiris(tira: TiraLED, args: list[str]) -> None:
    """Recorre colores del arcoíris."""
    try:
        pasos = int(args[0]) if args else 12
        demora = float(args[1]) if len(args) > 1 else 0.8
        print(f"Arcoíris ({pasos} pasos, demora={demora}s)")
        await tira.arcoiris(pasos, demora)
        print("Arcoíris terminado")
    except ValueError:
        print("Argumentos inválidos. Uso: python main.py arcoiris [pasos] [demora]")


async def cmd_probar(tira: TiraLED, _args: list[str]) -> None:
    """Prueba paleta de colores predefinida."""
    print("Probando colores básicos ...")
    await tira.probar_colores()
    print("Prueba terminada")


async def cmd_variante(tira: TiraLED, args: list[str]) -> None:
    """Prueba variaciones del comando de color."""
    if len(args) < 3:
        print("Uso: python main.py variante <R> <G> <B>")
        return
    try:
        r, g, b = int(args[0]), int(args[1]), int(args[2])
        print(f"Probando variantes para RGB({r},{g},{b})...")
        await tira.probar_variantes(r, g, b)
    except ValueError:
        print("Los valores deben ser números enteros (0-255)")


async def main() -> None:
    """Punto de entrada: interpreta el primer argumento como comando."""
    config = cargar_config()
    direccion_mac = config.get("direccion_mac")

    if len(sys.argv) < 2:
        print(__doc__)
        return

    comando = sys.argv[1]
    args = sys.argv[2:]

    # Diccionario que asocia comandos con funciones
    comandos: dict[str, object] = {
        "scan": cmd_escanear,
        "on": cmd_encender,
        "off": cmd_apagar,
        "color": cmd_color,
        "brillo": cmd_brillo,
        "temperatura": cmd_temperatura,
        "arcoiris": cmd_arcoiris,
        "probar": cmd_probar,
        "variante": cmd_variante,
    }

    if comando in ("scan",):
        await cmd_escanear(TiraLED(), [])
        return

    if not direccion_mac:
        print("No hay MAC configurada. Ejecuta: python main.py scan")
        return

    tira = TiraLED(direccion_mac)
    try:
        await tira.conectar()
        if comando in comandos:
            funcion = comandos[comando]
            await funcion(tira, args)
        else:
            print(f"Comando desconocido: {comando}")
            print("Comandos disponibles: scan, on, off, color, brillo, temperatura, arcoiris, probar, variante")
    finally:
        await tira.desconectar()


if __name__ == "__main__":
    asyncio.run(main())
