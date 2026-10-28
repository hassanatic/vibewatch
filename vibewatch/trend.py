"""Per-asset trend: is this machine getting worse, and how soon does it cross the next limit?

A fixed zone tells you where a machine is. Most failures show up first as a change against that
machine's own history, so the status also compares the latest reading with its baseline.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import median

import numpy as np

from .severity import Zone, limits, zone

BASELINE_READINGS = 5
WATCH_RATIO = 1.5
ALERT_RATIO = 2.5
WATCH_HORIZON_DAYS = 30.0
# The slope is fitted over recent readings only: a machine that was flat for weeks and started
# climbing last week must not have that climb averaged away by its quiet history.
TREND_WINDOW_DAYS = 14.0


@dataclass(frozen=True)
class Reading:
    at: datetime
    velocity_rms_mm_s: float


@dataclass(frozen=True)
class AssetStatus:
    asset_id: str
    readings: int
    latest_mm_s: float
    zone: Zone
    baseline_mm_s: float
    ratio_to_baseline: float
    slope_mm_s_per_day: float
    days_to_next_limit: float | None
    status: str
    reasons: tuple[str, ...]


def _slope_per_day(readings: list[Reading]) -> float:
    cutoff = readings[-1].at.timestamp() - TREND_WINDOW_DAYS * 86400.0
    readings = [r for r in readings if r.at.timestamp() >= cutoff]
    if len(readings) < 3:
        return 0.0
    t0 = readings[0].at
    days = np.array([(r.at - t0).total_seconds() / 86400.0 for r in readings])
    values = np.array([r.velocity_rms_mm_s for r in readings])
    if np.ptp(days) == 0:
        return 0.0
    slope, _ = np.polyfit(days, values, 1)
    return float(slope)


def assess(asset_id: str, readings: list[Reading], group: int = 2, mounting: str = "rigid") -> AssetStatus:
    if not readings:
        raise ValueError(f"{asset_id}: no readings")
    ordered = sorted(readings, key=lambda r: r.at)
    latest = ordered[-1].velocity_rms_mm_s
    baseline = median(r.velocity_rms_mm_s for r in ordered[:BASELINE_READINGS])
    ratio = latest / baseline if baseline > 0 else float("inf")
    slope = _slope_per_day(ordered)
    current = zone(latest, group, mounting)

    next_limit = next((lim for lim in limits(group, mounting) if lim > latest), None)
    days_to_next = (next_limit - latest) / slope if next_limit is not None and slope > 0 else None

    reasons: list[str] = []
    if current is Zone.D:
        reasons.append("zone D")
    elif current is Zone.C:
        reasons.append("zone C")
    if ratio >= WATCH_RATIO:
        reasons.append(f"{ratio:.1f}x baseline")
    if days_to_next is not None and days_to_next <= WATCH_HORIZON_DAYS:
        reasons.append(f"next limit in {days_to_next:.0f} days")

    if current is Zone.D:
        status = "alarm"
    elif current is Zone.C or ratio >= ALERT_RATIO:
        status = "alert"
    elif reasons:
        status = "watch"
    else:
        status = "ok"

    return AssetStatus(
        asset_id=asset_id,
        readings=len(ordered),
        latest_mm_s=round(latest, 3),
        zone=current,
        baseline_mm_s=round(baseline, 3),
        ratio_to_baseline=round(ratio, 2),
        slope_mm_s_per_day=round(slope, 4),
        days_to_next_limit=None if days_to_next is None else round(days_to_next, 1),
        status=status,
        reasons=tuple(reasons),
    )
