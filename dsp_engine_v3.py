"""
Motor DSP V3 - DINÁMICO CON CONTROL DE ENERGÍA
Detecta energía de la música en tiempo real y mapea a brillo/intensidad.
"""

import numpy as np
from collections import deque
from typing import Tuple, Optional, Dict


class EnergyAnalyzer:
    """Analiza energía de la música en tiempo real (NUEVO)."""

    def __init__(self, sr=48000, smoothing=0.7):
        self.sr = sr
        self.smoothing = smoothing  # 0-1, qué tan suave es la transición
        self.energy_history = deque(maxlen=100)
        self.current_energy = 0.0
        self.baseline_energy = 0.1
        self.peak_energy = 1.0

    def analyze(self, magnitude: np.ndarray) -> dict:
        """
        Analiza energía y retorna:
        - current_energy: energía normalizada (0-1)
        - relative_energy: cuánta energía relativa al baseline
        - intensity: qué tan "fuerte" se siente (para brillo)
        """
        # RMS energy
        energy = np.sqrt(np.mean(magnitude ** 2))
        self.energy_history.append(energy)

        # Baseline: promedio de últimas 2 segundos
        if len(self.energy_history) > 50:
            self.baseline_energy = np.mean(list(self.energy_history)[-50:])
        else:
            self.baseline_energy = np.mean(list(self.energy_history))

        # Peak: máximo de últimas 5 segundos
        if len(self.energy_history) > 100:
            self.peak_energy = np.max(list(self.energy_history)[-100:])
        else:
            self.peak_energy = np.max(list(self.energy_history)) if self.energy_history else 1.0

        # Normaliza a 0-1
        if self.peak_energy > self.baseline_energy:
            normalized = (energy - self.baseline_energy) / (self.peak_energy - self.baseline_energy + 1e-6)
        else:
            normalized = 0.0

        normalized = np.clip(normalized, 0, 1)

        # Suaviza transiciones
        self.current_energy = (self.smoothing * self.current_energy +
                              (1 - self.smoothing) * normalized)

        # Intensity: de 0-1, qué tan intenso debería ser el flash
        # Baja = tenue, Alta = brillante
        intensity = self.current_energy ** 0.7  # Exponencial para mejor control

        return {
            "energy": energy,
            "current_energy": self.current_energy,
            "baseline_energy": self.baseline_energy,
            "peak_energy": self.peak_energy,
            "intensity": intensity,  # Para brillo
            "is_quiet": self.current_energy < 0.2,  # Muy bajo
            "is_loud": self.current_energy > 0.7,   # Muy alto
        }


class AggressiveSilenceDetector:
    """Detecta SILENCIO instantáneamente."""

    def __init__(self, sr=48000, threshold_db=-40):
        self.sr = sr
        self.threshold_db = threshold_db
        self.energy_history = deque(maxlen=50)
        self.silence_frames = 0
        self.is_silent = False

    def detect(self, magnitude: np.ndarray) -> bool:
        """Detecta si hay SILENCIO."""
        energy = np.sqrt(np.mean(magnitude ** 2))
        energy_db = 20 * np.log10(energy + 1e-10)

        self.energy_history.append(energy_db)

        if len(self.energy_history) >= 10:
            recent_energy = np.mean(list(self.energy_history)[-10:])

            if recent_energy < self.threshold_db:
                self.silence_frames += 1
                if self.silence_frames > 5:
                    self.is_silent = True
                    return True
            else:
                self.silence_frames = 0
                self.is_silent = False

        return False


class SpectralFluxDetector:
    """FASE 1: Detección real de onsets."""

    def __init__(self, sr=48000, n_fft=2048):
        self.sr = sr
        self.n_fft = n_fft
        self.prev_magnitude = None
        self.flux_history = deque(maxlen=100)

    def compute_flux(self, magnitude_spectrum: np.ndarray) -> float:
        if self.prev_magnitude is None:
            self.prev_magnitude = magnitude_spectrum.copy()
            return 0.0
        diff = magnitude_spectrum - self.prev_magnitude
        flux = np.sqrt(np.sum(diff**2))
        self.flux_history.append(flux)
        self.prev_magnitude = magnitude_spectrum.copy()
        return float(flux)

    def normalize_flux(self, flux: float) -> float:
        if not self.flux_history:
            return 0.0
        mean_flux = np.mean(self.flux_history)
        std_flux = np.std(self.flux_history)
        if std_flux < 1e-6:
            return 0.5
        normalized = (flux - mean_flux) / (std_flux + 1e-6)
        return float(np.clip(1.0 / (1.0 + np.exp(-normalized)), 0, 1))


class AdaptiveEnergyThreshold:
    """FASE 1: Umbral inteligente."""

    def __init__(self, lookback_frames=200):
        self.energy_history = deque(maxlen=lookback_frames)
        self.silence_counter = 0

    def compute_threshold(self, current_onset_strength: float, snr_db: float, estimated_bpm: float) -> Tuple[float, dict]:
        base = 0.65

        if snr_db > 20:
            snr_mult = 0.90
        elif snr_db > 10:
            snr_mult = 0.95
        elif snr_db > 0:
            snr_mult = 1.0
        else:
            snr_mult = 1.15

        if len(self.energy_history) > 10:
            energy_mean = np.mean(list(self.energy_history))
            energy_std = np.std(list(self.energy_history))

            if current_onset_strength < energy_std * 0.3:
                self.silence_counter += 1
            else:
                self.silence_counter = 0

            if self.silence_counter > 30:
                silence_mult = 2.0
            elif self.silence_counter > 10:
                silence_mult = 1.5
            else:
                silence_mult = 1.0
        else:
            silence_mult = 1.0

        tempo_mult = 1.05 if estimated_bpm > 140 else 1.0
        adaptive_threshold = base * snr_mult * silence_mult * tempo_mult

        return np.clip(adaptive_threshold, 0.5, 0.95), {"final": adaptive_threshold}

    def update_history(self, energy: float):
        self.energy_history.append(energy)


class BeatTracker:
    """FASE 1: Tracking de BPM."""

    def __init__(self):
        self.bpm_hypothesis = [80, 100, 120, 140, 160]
        self.bpm_weights = [0.2] * 5
        self.last_beat_times = deque(maxlen=20)

    def update(self, beat_time: float) -> dict:
        self.last_beat_times.append(beat_time)
        if len(self.last_beat_times) > 2:
            intervals = np.diff(list(self.last_beat_times)[-8:])
            measured_bpms = 60.0 / np.clip(intervals, 0.2, 2.0)
            for i, hyp in enumerate(self.bpm_hypothesis):
                likelihood = np.exp(-0.5 * ((measured_bpms - hyp) / 15) ** 2).mean()
                self.bpm_weights[i] *= (likelihood + 0.1)
            total = sum(self.bpm_weights)
            self.bpm_weights = [w / total for w in self.bpm_weights]
        estimated_bpm = sum(h * w for h, w in zip(self.bpm_hypothesis, self.bpm_weights))
        return {"estimated_bpm": estimated_bpm, "confidence": max(self.bpm_weights)}


class KickBassClassifier:
    """FASE 2: ML Classifier para kick vs bass."""

    def __init__(self):
        self.model = None
        self.scaler = None
        self.features_cache = deque(maxlen=10)
        self._cache_len = None
        self._bandas = None

    def _obtener_bandas(self, n: int, sr: int):
        if self._cache_len != n:
            n_fft = (n - 1) * 2
            freqs = np.fft.rfftfreq(n_fft, 1 / sr)
            self._bandas = (
                (freqs >= 40) & (freqs <= 120),
                (freqs >= 80) & (freqs <= 250),
                (freqs >= 20) & (freqs <= 100),
                (freqs >= 500) & (freqs <= 8000),
            )
            self._cache_len = n
        return self._bandas

    def extract_features(self, magnitude: np.ndarray, sr: int = 48000) -> np.ndarray:
        """Extrae características para clasificación."""
        kick_band, bass_band, sub_band, high_band = self._obtener_bandas(len(magnitude), sr)

        features = np.array([
            np.sum(magnitude[kick_band] ** 2),
            np.sum(magnitude[bass_band] ** 2),
            np.sum(magnitude[sub_band] ** 2),
            np.sum(magnitude[high_band] ** 2),
            np.sum(magnitude[kick_band] ** 2) / (np.sum(magnitude[bass_band] ** 2) + 1e-6),
            np.std(magnitude[kick_band]),
            np.std(magnitude[bass_band]),
            np.max(magnitude[kick_band]),
            np.max(magnitude[bass_band]),
            np.percentile(magnitude[kick_band], 75),
            np.percentile(magnitude[bass_band], 75),
            np.mean(magnitude[kick_band]),
            np.mean(magnitude[bass_band]),
            np.sum(magnitude ** 2),
            np.argmax(magnitude),
        ])
        return np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)

    def classify(self, magnitude: np.ndarray, sr: int = 48000) -> Tuple[str, float]:
        """Clasifica como kick o bass."""
        features = self.extract_features(magnitude, sr)

        kick_energy_ratio = features[4]
        sub_dominance = features[2] / (features[2] + features[1] + 1e-6)
        high_content = features[3] / (features[13] + 1e-6)

        kick_score = (
            (kick_energy_ratio if kick_energy_ratio > 1 else 0.3) * 0.4 +
            sub_dominance * 0.3 +
            (1.0 - high_content) * 0.3
        )

        if kick_score > 0.6:
            return "kick", min(kick_score, 1.0)
        else:
            return "bass", min(1.0 - kick_score, 1.0)


class LatencyCompensator:
    """FASE 3: Compensación automática de latencia."""

    def __init__(self):
        self.latency_history = deque(maxlen=100)
        self.measured_latency = 0.0

    def measure_latency(self, click_time: float, detection_time: float):
        """Registra latencia medida."""
        latency = detection_time - click_time
        self.latency_history.append(latency)
        self.measured_latency = np.median(self.latency_history) if self.latency_history else 0.0

    def compensate(self, beat_detection_time: float) -> float:
        """Retorna tiempo de envío compensado."""
        if self.measured_latency > 0:
            return beat_detection_time - self.measured_latency
        return beat_detection_time


class SourceSeparation:
    """FASE 3: Aislamiento de componentes."""

    def __init__(self, sr: int = 48000):
        self.sr = sr
        self.kick_buffer = deque(maxlen=200)
        self.bass_buffer = deque(maxlen=200)
        self._cache_len = None
        self._filtros = None

    def _obtener_filtros(self, n: int):
        """Filtros gaussianos cacheados (no recalcular por frame)."""
        if self._cache_len != n:
            n_fft = (n - 1) * 2
            freqs = np.fft.rfftfreq(n_fft, 1 / self.sr)
            self._filtros = (
                np.exp(-((freqs - 80) ** 2) / (2 * 30 ** 2)),
                np.exp(-((freqs - 150) ** 2) / (2 * 50 ** 2)),
                np.exp(-((freqs - 400) ** 2) / (2 * 150 ** 2)),
            )
            self._cache_len = n
        return self._filtros

    def separate(self, spectrum: np.ndarray) -> Dict[str, np.ndarray]:
        """Separa componentes por frecuencia."""
        kick_filter, bass_filter, mid_filter = self._obtener_filtros(len(spectrum))

        kick = spectrum * kick_filter
        bass = spectrum * bass_filter
        mid = spectrum * mid_filter

        self.kick_buffer.append(np.sum(kick ** 2))
        self.bass_buffer.append(np.sum(bass ** 2))

        return {
            "kick": kick,
            "bass": bass,
            "mid": mid,
            "kick_energy": float(np.mean(self.kick_buffer)) if self.kick_buffer else 0,
            "bass_energy": float(np.mean(self.bass_buffer)) if self.bass_buffer else 0,
        }


_SNR_MASK_CACHE: dict = {}


def compute_snr(magnitude_spectrum: np.ndarray, sr: int = 48000) -> float:
    """SNR en dB."""
    clave = (len(magnitude_spectrum), sr)
    bandas = _SNR_MASK_CACHE.get(clave)
    if bandas is None:
        n_fft = (len(magnitude_spectrum) - 1) * 2
        freqs = np.fft.rfftfreq(n_fft, 1 / sr)
        bandas = ((freqs >= 20) & (freqs <= 1000), (freqs >= 8000) & (freqs <= sr / 2))
        _SNR_MASK_CACHE[clave] = bandas
    signal_band, noise_band = bandas
    signal_energy = np.sum(magnitude_spectrum[signal_band] ** 2)
    noise_energy = np.sum(magnitude_spectrum[noise_band] ** 2)
    snr_linear = signal_energy / (noise_energy + 1e-6)
    return float(10 * np.log10(snr_linear + 1e-6))


class CompleteDSPEngine:
    """Motor DSP V3 - Con control dinámico de energía."""

    def __init__(self, sr: int = 48000):
        self.sr = sr
        self.energy_analyzer = EnergyAnalyzer(sr=sr)  # NUEVO
        self.silence_detector = AggressiveSilenceDetector(sr=sr)
        self.flux_detector = SpectralFluxDetector(sr=sr)
        self.adaptive_threshold = AdaptiveEnergyThreshold()
        self.beat_tracker = BeatTracker()
        self.classifier = KickBassClassifier()
        self.latency_compensator = LatencyCompensator()
        self.source_separation = SourceSeparation(sr=sr)

    def process_frame(self, magnitude: np.ndarray) -> dict:
        """Procesa frame con análisis dinámico de energía."""

        # PRIMERO: Analiza energía global
        energy_info = self.energy_analyzer.analyze(magnitude)

        # SEGUNDO: Detecta SILENCIO
        is_silent = self.silence_detector.detect(magnitude)

        if is_silent:
            return {
                "is_beat": False,
                "is_silent": True,
                "beat_type": "none",
                "confidence": 0.0,
                "onset_strength": 0.0,
                "threshold": 1.0,
                "snr_db": -50.0,
                "estimated_bpm": 120.0,
                "separation": {"kick_energy": 0, "bass_energy": 0},
                "kick_energy": 0,
                "bass_energy": 0,
                "energy_intensity": 0.0,  # NUEVO
            }

        # TERCERO: Procesa beats normalmente
        flux = self.flux_detector.compute_flux(magnitude)
        onset_normalized = self.flux_detector.normalize_flux(flux)

        snr_db = compute_snr(magnitude, self.sr)

        bpm_info = self.beat_tracker.update(0)
        estimated_bpm = bpm_info["estimated_bpm"]

        threshold, _ = self.adaptive_threshold.compute_threshold(onset_normalized, snr_db, estimated_bpm)
        self.adaptive_threshold.update_history(onset_normalized)

        is_beat = onset_normalized > threshold

        beat_type = "none"
        beat_confidence = 0.0
        if is_beat:
            beat_type, beat_confidence = self.classifier.classify(magnitude, self.sr)

        separation = self.source_separation.separate(magnitude)

        return {
            "is_beat": is_beat,
            "is_silent": False,
            "beat_type": beat_type,
            "confidence": beat_confidence,
            "onset_strength": onset_normalized,
            "threshold": threshold,
            "snr_db": snr_db,
            "estimated_bpm": estimated_bpm,
            "separation": separation,
            "kick_energy": separation["kick_energy"],
            "bass_energy": separation["bass_energy"],
            "energy_intensity": energy_info["intensity"],  # NUEVO: 0-1 para brillo
            "is_quiet": energy_info["is_quiet"],
            "is_loud": energy_info["is_loud"],
        }


class DetectorImpacto:
    """Detecta sonidos FUERTES REPENTINOS (golpes, crujidos, explosiones, portazos).

    Pensado para inmersión en películas (Cine Mode), NO para música. Reacciona a
    una SUBIDA brusca de volumen sobre una línea base lenta, y rechaza diálogos
    exigiendo o bien contenido fuera de la banda de voz (graves/agudos) o bien un
    salto muy grande. Es independiente del detector de beats (no lo afecta).
    """

    def __init__(self, sr: int = 48000):
        self.sr = sr
        self.baseline_db = -60.0
        self.hist_db = deque(maxlen=180)  # ~pocos segundos de historia
        self.umbral_db = 9.0              # ajustable por sensibilidad
        self._init = False
        self._cache_len = None
        self._masks = None

    def set_sensibilidad(self, s: float) -> None:
        """s en 0..1: 0 = poco sensible (salto grande), 1 = muy sensible."""
        s = max(0.0, min(1.0, float(s)))
        self.umbral_db = 14.0 - 9.0 * s   # 14 dB (poco) .. 5 dB (mucho)

    def _obtener_masks(self, n: int, sr: int):
        if self._cache_len != n:
            n_fft = (n - 1) * 2
            freqs = np.fft.rfftfreq(n_fft, 1 / sr)
            self._masks = (
                (freqs >= 20) & (freqs <= 250),
                (freqs > 250) & (freqs <= 4000),
                (freqs > 4000) & (freqs <= 16000),
            )
            self._cache_len = n
        return self._masks

    def analyze(self, magnitude: np.ndarray, sr: int = None) -> dict:
        sr = sr or self.sr

        energy = float(np.sqrt(np.mean(magnitude ** 2)))
        db = 20.0 * np.log10(energy + 1e-9)
        if not self._init:
            self.baseline_db = db
            self._init = True
        self.hist_db.append(db)

        sub, voz, agudo = self._obtener_masks(len(magnitude), sr)
        e_sub = float(np.sum(magnitude[sub] ** 2))
        e_voz = float(np.sum(magnitude[voz] ** 2))
        e_agudo = float(np.sum(magnitude[agudo] ** 2))
        total = e_sub + e_voz + e_agudo + 1e-9
        no_habla = (e_sub + e_agudo) / total

        subida = db - self.baseline_db
        lo = min(self.hist_db)
        hi = max(self.hist_db)
        nivel = 0.0 if (hi - lo) < 1e-6 else float(np.clip((db - lo) / (hi - lo), 0.0, 1.0))

        # Línea base lenta (~1-2 s).
        self.baseline_db += 0.02 * (db - self.baseline_db)

        fuerte = (subida >= self.umbral_db) and (db > lo + 8.0)
        # Salto moderado exige contenido no-voz; salto enorme dispara igual.
        es_impacto = fuerte and (no_habla >= 0.30 or subida >= self.umbral_db * 1.6)
        fuerza = float(np.clip((subida - self.umbral_db) / 12.0, 0.0, 1.0)) if es_impacto else 0.0

        return {
            "nivel": nivel,
            "subida_db": float(subida),
            "no_habla": float(no_habla),
            "es_impacto": bool(es_impacto),
            "fuerza": fuerza,
            "silencio": nivel < 0.05,
        }
