"""Turn raw acceleration samples into the numbers condition monitoring works with."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# ISO 10816-3 measures broadband velocity between 10 and 1000 Hz for machines running above 600 rpm.
ISO_BAND_HZ = (10.0, 1000.0)


@dataclass(frozen=True)
class Features:
    velocity_rms_mm_s: float
    acceleration_rms_m_s2: float
    peak_frequency_hz: float


def velocity_rms(accel_m_s2, fs_hz: float, band_hz: tuple[float, float] = ISO_BAND_HZ) -> float:
    """Velocity RMS in mm/s, integrating acceleration in the frequency domain.

    Integration is a division by j*2*pi*f per FFT bin. Bins outside the band are dropped, which
    also removes DC and slow drift that would otherwise dominate a time-domain integral.
    """
    a = np.asarray(accel_m_s2, dtype=float)
    if a.ndim != 1 or a.size < 2:
        raise ValueError("need a 1-D signal with at least two samples")
    if fs_hz <= 0:
        raise ValueError("sample rate must be positive")
    lo, hi = band_hz
    if not 0 < lo < hi:
        raise ValueError("band must satisfy 0 < low < high")

    n = a.size
    spectrum = np.fft.rfft(a - a.mean())
    freqs = np.fft.rfftfreq(n, d=1.0 / fs_hz)
    keep = (freqs >= lo) & (freqs <= hi)

    velocity_spectrum = np.zeros_like(spectrum)
    velocity_spectrum[keep] = spectrum[keep] / (2j * np.pi * freqs[keep])
    velocity = np.fft.irfft(velocity_spectrum, n=n)
    return float(np.sqrt(np.mean(velocity**2)) * 1000.0)


def features(accel_m_s2, fs_hz: float, band_hz: tuple[float, float] = ISO_BAND_HZ) -> Features:
    a = np.asarray(accel_m_s2, dtype=float)
    centred = a - a.mean()
    spectrum = np.abs(np.fft.rfft(centred))
    freqs = np.fft.rfftfreq(a.size, d=1.0 / fs_hz)
    spectrum[0] = 0.0
    return Features(
        velocity_rms_mm_s=velocity_rms(a, fs_hz, band_hz),
        acceleration_rms_m_s2=float(np.sqrt(np.mean(centred**2))),
        peak_frequency_hz=float(freqs[int(np.argmax(spectrum))]),
    )
