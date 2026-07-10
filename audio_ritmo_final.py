"""
Detector de Ritmo FINAL - PRODUCCIÓN
Incluye todas las mejoras (FASES 1, 2, 3) integradas.
Reemplaza audio_ritmo.py completamente.
"""

import logging
import threading
import time
from collections import deque
from typing import Optional

import numpy as np

try:
    import pyaudiowpatch as pa_rt
    _PA_DISPONIBLE = True
except ImportError:
    pa_rt = None
    _PA_DISPONIBLE = False

from dsp_engine_v3 import CompleteDSPEngine

logger = logging.getLogger(__name__)

# Configuración optimizada
TAMANO_BLOQUE = 512
FFT_SIZE = 2048
HOP_SIZE = 256

BANDAS = {
    "kick": (40, 120),
    "bass": (80, 250),
    "full": (40, 250),
}


class DetectorRitmo:
    """Detector profesional de ritmo - Todas las fases integradas."""

    def __init__(self, modo_deteccion: str = "kick"):
        self._stream = None
        self._corriendo = False
        self._dispositivo: Optional[dict] = None
        self._tasa: int = 48000
        self._beat_flag = False
        self._ultimo_beat: float = 0.0
        self._beat_info: dict = {}
        self._lock = threading.Lock()
        self._callback_thread: Optional[threading.Thread] = None
        self._modo: str = modo_deteccion if modo_deteccion in BANDAS else "kick"

        # Motor DSP profesional (FASES 1, 2, 3)
        self._dsp_engine = CompleteDSPEngine(sr=self._tasa)
        self._audio_buffer = np.zeros(FFT_SIZE)
        self._last_beat_times = deque(maxlen=20)

        self._encontrar_loopback()

    @property
    def modo(self) -> str:
        return self._modo

    @modo.setter
    def modo(self, valor: str):
        if valor in BANDAS:
            self._modo = valor

    def _encontrar_loopback(self):
        if not _PA_DISPONIBLE:
            logger.warning("pyaudiowpatch no disponible")
            return
        try:
            py_audio = pa_rt.PyAudio()
            self._dispositivo = py_audio.get_default_wasapi_loopback()
            self._tasa = int(self._dispositivo["defaultSampleRate"])
            py_audio.terminate()
            logger.info(
                "✅ Loopback WASAPI encontrado: %s (48kHz)",
                self._dispositivo["name"],
            )
        except Exception as e:
            logger.warning("No WASAPI loopback: %s", e)

    def _callback_lectura(self):
        """Lee audio y procesa con motor DSP."""
        try:
            while self._corriendo and self._stream.is_active():
                try:
                    disponibles = self._stream.get_read_available()
                    if disponibles < TAMANO_BLOQUE:
                        time.sleep(0.002)
                        continue
                    datos = self._stream.read(TAMANO_BLOQUE, exception_on_overflow=False)
                    datos_mono = np.frombuffer(datos, dtype=np.int16).reshape(-1, 2)
                    self._procesar_bloque(datos_mono[:, 0])
                except Exception:
                    break
        except Exception:
            pass

    def _procesar_bloque(self, datos: np.ndarray):
        """Procesa con motor DSP completo."""
        if len(datos) < 2:
            return

        # Buffer superpuesto (50% overlap)
        self._audio_buffer = np.roll(self._audio_buffer, -HOP_SIZE)
        self._audio_buffer[-HOP_SIZE:] = datos[:HOP_SIZE]

        # FFT
        window = np.hanning(FFT_SIZE)
        audio_windowed = self._audio_buffer * window
        spectrum = np.fft.rfft(audio_windowed, n=FFT_SIZE * 2)
        magnitude = np.abs(spectrum)

        # Motor DSP (FASES 1, 2, 3)
        result = self._dsp_engine.process_frame(magnitude)

        # Decisión de beat
        if result["is_beat"]:
            ahora = time.time()
            bpm = result["estimated_bpm"]
            min_interval = (60.0 / max(bpm, 60)) * 0.2  # 20% del intervalo de beat

            with self._lock:
                if ahora - self._ultimo_beat > min_interval:
                    self._beat_flag = True
                    self._beat_info = result
                    self._ultimo_beat = ahora
                    self._last_beat_times.append(ahora)

    @property
    def disponible(self) -> bool:
        return self._dispositivo is not None

    @property
    def hubo_beat(self) -> bool:
        with self._lock:
            if self._beat_flag:
                self._beat_flag = False
                return True
            return False

    def get_beat_info(self) -> dict:
        """Retorna información detallada del último beat."""
        with self._lock:
            return self._beat_info.copy() if self._beat_info else {}

    def iniciar(self) -> bool:
        if not _PA_DISPONIBLE:
            logger.error("pyaudiowpatch no instalado")
            return False
        if not self._dispositivo:
            logger.error("No hay loopback WASAPI")
            return False
        if self._corriendo:
            return True

        self._corriendo = True
        try:
            py_audio = pa_rt.PyAudio()
            self._stream = py_audio.open(
                format=pa_rt.paInt16,
                channels=2,
                rate=self._tasa,
                input=True,
                input_device_index=self._dispositivo["index"],
                frames_per_buffer=TAMANO_BLOQUE,
            )
            self._callback_thread = threading.Thread(
                target=self._callback_lectura, daemon=True
            )
            self._callback_thread.start()
            logger.info("✅ Detector FINAL iniciado - Todas las fases activas")
            return True
        except Exception as e:
            logger.error("Error captura audio: %s", e)
            self._corriendo = False
            return False

    def detener(self):
        self._corriendo = False
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        if self._callback_thread and self._callback_thread.is_alive():
            self._callback_thread.join(timeout=2)
            self._callback_thread = None
        logger.info("Detector detenido")
