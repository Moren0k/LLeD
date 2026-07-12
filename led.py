import asyncio
import math
from typing import Optional

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice

# --- Constantes del protocolo BLE ---
UUID_SERVICIO = "0000fff0-0000-1000-8000-00805f9b34fb"
UUID_CARACTERISTICA = "0000fff3-0000-1000-8000-00805f9b34fb"

INICIO = 0x7E
FINAL = 0xEF

# Corrección de gamma para la salida de color del LED. El ojo percibe la luz de
# forma no lineal; sin corrección los fundidos "saltan" en la zona oscura y los
# tonos medios se ven más claros de lo esperado. Se aplica solo al color enviado
# a la tira (la interfaz sigue mostrando el color sRGB pedido). Ajustable.
GAMMA = 2.2
_GAMMA_LUT = tuple(round(((i / 255.0) ** GAMMA) * 255) for i in range(256))


def _gamma(v: int) -> int:
    return _GAMMA_LUT[max(0, min(255, int(v)))]


def _comando_color(rojo: int, verde: int, azul: int, byte2: int = 0x00, relleno: int = 0x00) -> bytes:
    """Construye el payload de 9 bytes para cambiar el color RGB.

    Formato: [0x7E, byte2, 0x05, 0x03, R, G, B, relleno, 0xEF]
    """
    return bytes([
        INICIO,
        byte2,
        0x05,
        0x03,
        rojo & 0xFF,
        verde & 0xFF,
        azul & 0xFF,
        relleno,
        FINAL,
    ])


def _comando_encender(encendido: bool) -> bytes:
    """Construye el payload para encender o apagar la tira LED."""
    if encendido:
        return bytes([0x7E, 0x04, 0x04, 0xF0, 0x00, 0x01, 0xFF, 0x00, 0xEF])
    return bytes([0x7E, 0x04, 0x04, 0x00, 0x00, 0x00, 0xFF, 0x00, 0xEF])


def _comando_brillo(valor: int, modo: int = 0xFF) -> bytes:
    """Construye el payload para cambiar el brillo (0-255)."""
    return bytes([
        INICIO,
        0x00,
        0x01,
        valor & 0xFF,
        modo & 0xFF,
        0x00,
        0x00,
        0x00,
        FINAL,
    ])


def _comando_temperatura(calido: int, frio: int) -> bytes:
    """Construye el payload para temperatura de color (cálido + frío deben sumar 100)."""
    return bytes([
        INICIO,
        0x00,
        0x05,
        0x02,
        calido & 0xFF,
        frio & 0xFF,
        0x00,
        0x00,
        FINAL,
    ])


def _hsv_a_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    """Convierte un color HSV (0-1) a RGB (0-255)."""
    i = int(h * 6)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    r, g, b = [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)][i % 6]
    return int(r * 255), int(g * 255), int(b * 255)


class TiraLED:
    """Controlador para tiras LED compatibles con ELK-BLEDOM / Lotus Lantern.

    Se comunica vía Bluetooth Low Energy (BLE) usando la librería Bleak.
    """

    def __init__(self, direccion_mac: Optional[str] = None) -> None:
        self.direccion_mac = direccion_mac
        self._cliente: Optional[BleakClient] = None

    @staticmethod
    async def escanear(tiempo_limite: int = 10) -> list[BLEDevice]:
        """Escanea dispositivos BLE cercanos y devuelve los que tengan 'ELK' en el nombre."""
        dispositivos = await BleakScanner.discover(timeout=tiempo_limite)
        return [d for d in dispositivos if d.name and "ELK" in d.name.upper()]

    @staticmethod
    async def escanear_todos(tiempo_limite: int = 8) -> list[dict]:
        """Escanea TODOS los dispositivos BLE cercanos con nombre.

        Devuelve una lista de dicts {nombre, direccion, probable_led} ordenada
        poniendo primero los que parecen tiras LED compatibles.
        """
        patrones_led = ("ELK", "LED", "BLEDOM", "LOTUS", "MELK", "LEDBLE", "QHM", "ISP")
        dispositivos = await BleakScanner.discover(timeout=tiempo_limite)
        resultado = []
        for d in dispositivos:
            if not d.name:
                continue
            nombre_up = d.name.upper()
            probable = any(p in nombre_up for p in patrones_led)
            resultado.append({
                "nombre": d.name,
                "direccion": d.address,
                "probable_led": probable,
            })
        resultado.sort(key=lambda x: (not x["probable_led"], x["nombre"].lower()))
        return resultado

    async def conectar(self) -> None:
        """Establece conexión BLE con la tira LED."""
        if self._cliente and self._cliente.is_connected:
            return
        if not self.direccion_mac:
            raise ValueError("No hay dirección MAC configurada")
        self._cliente = BleakClient(self.direccion_mac)
        await self._cliente.connect()
        print(f"Conectado a {self.direccion_mac}")

    async def desconectar(self) -> None:
        """Cierra la conexión BLE."""
        if self._cliente and self._cliente.is_connected:
            await self._cliente.disconnect()

    async def enviar(self, datos: bytes) -> None:
        """Envía un payload de bytes a la característica FFF3 de la tira."""
        if not self._cliente or not self._cliente.is_connected:
            raise ConnectionError("No hay conexión activa. Ejecuta conectar() primero")
        await self._cliente.write_gatt_char(UUID_CARACTERISTICA, datos, response=False)

    async def encender(self) -> None:
        """Enciende la tira LED."""
        await self.enviar(_comando_encender(True))
        print("LED encendido")

    async def apagar(self) -> None:
        """Apaga la tira LED."""
        await self.enviar(_comando_encender(False))
        print("LED apagado")

    async def color(self, rojo: int, verde: int, azul: int) -> None:
        """Cambia el color de la tira a un RGB específico (0-255 cada canal).

        Aplica corrección de gamma para que los fundidos y los tonos se vean
        perceptualmente correctos en la tira.
        """
        await self.enviar(_comando_color(_gamma(rojo), _gamma(verde), _gamma(azul)))
        print(f"Color: RGB({rojo}, {verde}, {azul})")

    async def brillo(self, valor: int) -> None:
        """Ajusta el brillo de 0 a 255."""
        valor = max(0, min(255, valor))
        await self.enviar(_comando_brillo(valor))
        print(f"Brillo: {valor}")

    async def temperatura(self, calido: int = 50, frio: int = 50) -> None:
        """Ajusta temperatura de color. Cálido + Frío deben sumar 100."""
        calido = max(0, min(100, calido))
        frio = max(0, min(100, frio))
        await self.enviar(_comando_temperatura(calido, frio))
        print(f"Temperatura: cálido={calido}, frío={frio}")

    async def arcoiris(self, pasos: int = 12, demora: float = 0.8) -> None:
        """Recorre el espectro HSV mostrando N colores con una pausa entre cada uno."""
        for i in range(pasos):
            matiz = i / pasos
            r, g, b = _hsv_a_rgb(matiz, 1.0, 1.0)
            await self.color(r, g, b)
            await asyncio.sleep(demora)

    async def probar_colores(self) -> None:
        """Prueba una paleta de colores predefinidos para verificar el funcionamiento."""
        paleta = [
            ("ROJO", 255, 0, 0),
            ("VERDE", 0, 255, 0),
            ("AZUL", 0, 0, 255),
            ("AMARILLO", 255, 255, 0),
            ("CYAN", 0, 255, 255),
            ("MAGENTA", 255, 0, 255),
            ("BLANCO", 255, 255, 255),
            ("NARANJA", 255, 128, 0),
            ("PURPURA", 128, 0, 255),
            ("ROSA", 255, 64, 128),
        ]
        for nombre, r, g, b in paleta:
            await self.color(r, g, b)
            await asyncio.sleep(1.5)

    async def probar_variantes(self, rojo: int, verde: int, azul: int) -> None:
        """Envía el mismo color con 4 combinaciones de byte2/relleno para depuración."""
        variantes = [
            ("byte2=0x00 relleno=0x00", 0x00, 0x00),
            ("byte2=0x07 relleno=0x00", 0x07, 0x00),
            ("byte2=0x00 relleno=0x10", 0x00, 0x10),
            ("byte2=0x07 relleno=0x10", 0x07, 0x10),
        ]
        for etiqueta, b2, relleno in variantes:
            comando = _comando_color(rojo, verde, azul, byte2=b2, relleno=relleno)
            print(f"  [{etiqueta}] -> {comando.hex()}")
            await self.enviar(comando)
            await asyncio.sleep(2)
