from datetime import datetime, timedelta

import pytest

from vibewatch import Reading, Zone, assess

START = datetime(2026, 9, 1)


def daily(values):
    return [Reading(START + timedelta(days=i), v) for i, v in enumerate(values)]


def test_steady_machine_is_ok():
    s = assess("pump-1", daily([1.0, 1.05, 0.98, 1.02, 1.0, 1.01, 0.99]))
    assert s.status == "ok"
    assert s.zone is Zone.A
    assert s.reasons == ()


def test_rising_machine_is_flagged_before_it_leaves_zone_b():
    # 1.0 mm/s for five days, then climbing 0.1 mm/s per day; still zone B at the end
    s = assess("fan-2", daily([1.0] * 5 + [1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7]))
    assert s.zone is Zone.B
    assert s.ratio_to_baseline == pytest.approx(1.7)
    assert s.status == "watch"
    assert s.slope_mm_s_per_day > 0
    assert s.days_to_next_limit is not None and s.days_to_next_limit < 30


def test_recent_climb_is_not_averaged_away_by_a_long_quiet_history():
    # flat at 1.2 for 20 days, then +0.055 mm/s per day for 10 days: ends at 1.75, under 1.5x baseline
    values = [1.2] * 20 + [1.2 + 0.055 * d for d in range(1, 11)]
    s = assess("crusher-fan", daily(values))
    assert s.ratio_to_baseline < 1.5
    # the 14-day window still holds four flat days, so the fit sits a little under 0.055
    assert 0.03 < s.slope_mm_s_per_day < 0.055
    assert s.status == "watch"
    assert any("next limit" in r for r in s.reasons)


def test_large_jump_against_own_history_alerts_even_in_a_good_zone():
    s = assess("motor-3", daily([0.3, 0.3, 0.3, 0.3, 0.3, 0.9]))
    assert s.zone is Zone.A
    assert s.status == "alert"


def test_zone_d_is_an_alarm():
    s = assess("gearbox-4", daily([3.0, 3.2, 3.5, 4.0, 4.6]))
    assert s.zone is Zone.D
    assert s.status == "alarm"


def test_readings_are_sorted_before_use():
    readings = daily([1.0, 1.0, 1.0, 1.0, 1.0, 2.0])
    s = assess("pump-5", list(reversed(readings)))
    assert s.latest_mm_s == 2.0


def test_no_readings_is_an_error():
    with pytest.raises(ValueError):
        assess("empty", [])
