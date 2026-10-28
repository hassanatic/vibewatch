"""ISO 10816-3 evaluation zones for broadband velocity RMS (mm/s, 10-1000 Hz).

Zone A: typical of newly commissioned machines.
Zone B: acceptable for unrestricted long-term operation.
Zone C: unsatisfactory for long-term operation; run only for a limited period.
Zone D: severe enough to cause damage.
"""
from __future__ import annotations

from enum import Enum

# (A/B, B/C, C/D) boundaries in mm/s.
#   group 1: large machines, 300 kW to 50 MW
#   group 2: medium machines, 15 kW to 300 kW
LIMITS: dict[tuple[int, str], tuple[float, float, float]] = {
    (1, "rigid"): (2.3, 4.5, 7.1),
    (1, "flexible"): (3.5, 7.1, 11.0),
    (2, "rigid"): (1.4, 2.8, 4.5),
    (2, "flexible"): (2.3, 4.5, 7.1),
}


class Zone(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


def limits(group: int, mounting: str) -> tuple[float, float, float]:
    try:
        return LIMITS[(group, mounting)]
    except KeyError:
        raise ValueError(f"unknown machine class: group {group}, {mounting} mounting") from None


def zone(velocity_rms_mm_s: float, group: int = 2, mounting: str = "rigid") -> Zone:
    if velocity_rms_mm_s < 0:
        raise ValueError("velocity RMS cannot be negative")
    ab, bc, cd = limits(group, mounting)
    if velocity_rms_mm_s < ab:
        return Zone.A
    if velocity_rms_mm_s < bc:
        return Zone.B
    if velocity_rms_mm_s < cd:
        return Zone.C
    return Zone.D
