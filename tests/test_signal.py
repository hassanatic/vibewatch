import math

import numpy as np
import pytest

from vibewatch import features, velocity_rms

FS = 5120.0
T = np.arange(int(FS)) / FS  # one second, so every test tone has a whole number of cycles


def tone_velocity_rms_mm_s(accel_amplitude: float, freq: float) -> float:
    return accel_amplitude / (2 * math.pi * freq) / math.sqrt(2) * 1000


def test_single_tone_matches_closed_form():
    a = 10.0 * np.sin(2 * np.pi * 50 * T)
    assert velocity_rms(a, FS) == pytest.approx(tone_velocity_rms_mm_s(10.0, 50), rel=1e-3)


def test_two_tones_add_as_root_sum_square():
    a = 10.0 * np.sin(2 * np.pi * 50 * T) + 20.0 * np.sin(2 * np.pi * 120 * T)
    expected = math.hypot(tone_velocity_rms_mm_s(10.0, 50), tone_velocity_rms_mm_s(20.0, 120))
    assert velocity_rms(a, FS) == pytest.approx(expected, rel=1e-3)


def test_tone_below_band_is_ignored():
    a = 10.0 * np.sin(2 * np.pi * 5 * T)
    assert velocity_rms(a, FS) == pytest.approx(0.0, abs=1e-9)


def test_dc_offset_and_gravity_do_not_count():
    a = 9.81 + 10.0 * np.sin(2 * np.pi * 50 * T)
    assert velocity_rms(a, FS) == pytest.approx(tone_velocity_rms_mm_s(10.0, 50), rel=1e-3)


def test_features_report_peak_frequency_and_acceleration_rms():
    a = 10.0 * np.sin(2 * np.pi * 50 * T) + 20.0 * np.sin(2 * np.pi * 120 * T)
    f = features(a, FS)
    assert f.peak_frequency_hz == pytest.approx(120.0)
    assert f.acceleration_rms_m_s2 == pytest.approx(math.hypot(10, 20) / math.sqrt(2), rel=1e-6)


@pytest.mark.parametrize(
    "signal, fs, band",
    [([1.0], FS, (10.0, 1000.0)), ([1.0, 2.0], 0.0, (10.0, 1000.0)), ([1.0, 2.0], FS, (100.0, 10.0))],
)
def test_bad_input_is_rejected(signal, fs, band):
    with pytest.raises(ValueError):
        velocity_rms(signal, fs, band)
