import random

import pytest

from bornes import APP_RADIUS_KM, BORNES, distance_km, position


def test_five_bornes_in_isere():
    assert len(BORNES) == 5
    for b in BORNES.values():
        assert 44.6 < b.lat < 45.9 and 4.7 < b.lon < 6.4  # emprise de l'Isère


def test_borne_exact():
    b = BORNES["col_porte"]
    assert position("col_porte", "borne") == (b.lat, b.lon)


def test_app_within_radius_and_spread():
    rng = random.Random(0)
    b = BORNES["moliere"]
    d = [distance_km(b.lat, b.lon, *position("moliere", "app", rng)) for _ in range(2000)]
    assert max(d) <= APP_RADIUS_KM + 1e-6
    # uniforme en surface : ~25 % des points dans le disque de rayon R/2
    inner = sum(x <= APP_RADIUS_KM / 2 for x in d) / len(d)
    assert 0.21 < inner < 0.29


def test_bad_source():
    with pytest.raises(ValueError):
        position("col_porte", "gps")
