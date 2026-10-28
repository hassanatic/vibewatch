import pytest

from vibewatch import Zone, zone


@pytest.mark.parametrize(
    "value, expected",
    [(0.0, Zone.A), (1.39, Zone.A), (1.4, Zone.B), (2.79, Zone.B), (2.8, Zone.C), (4.49, Zone.C), (4.5, Zone.D)],
)
def test_group2_rigid_boundaries(value, expected):
    assert zone(value, group=2, mounting="rigid") is expected


def test_the_same_reading_is_milder_on_a_large_flexibly_mounted_machine():
    assert zone(5.0, group=2, mounting="rigid") is Zone.D
    assert zone(5.0, group=1, mounting="flexible") is Zone.B


def test_unknown_class_and_negative_values_are_rejected():
    with pytest.raises(ValueError):
        zone(1.0, group=3, mounting="rigid")
    with pytest.raises(ValueError):
        zone(-0.1)
