from datetime import date, datetime, timezone

import pytest

from periods import TZ, HalfDay, half_day_of, local_from_naive


@pytest.mark.parametrize("h,slot", [(0, "matin"), (5, "matin"), (6, "matin"), (12, "matin"),
                                    (13, "apres_midi"), (19, "apres_midi"), (20, "apres_midi"), (23, "apres_midi")])
def test_slots_local_time(h, slot):
    assert half_day_of(local_from_naive(date(2026, 11, 9), h, 30)) == HalfDay(date(2026, 11, 9), slot)


def test_utc_converted_to_paris():
    # 12:30 UTC en novembre = 13:30 à Paris -> après-midi
    assert half_day_of(datetime(2026, 11, 9, 12, 30, tzinfo=timezone.utc)).slot == "apres_midi"
    # 11:30 UTC en juillet (UTC+2) = 13:30 -> après-midi ; 10:59 UTC = 12:59 -> matin
    assert half_day_of(datetime(2026, 7, 1, 11, 30, tzinfo=timezone.utc)).slot == "apres_midi"
    assert half_day_of(datetime(2026, 7, 1, 10, 59, tzinfo=timezone.utc)).slot == "matin"
    # 23:30 UTC le 9 = 00:30 le 10 à Paris -> matin du 10
    assert half_day_of(datetime(2026, 11, 9, 23, 30, tzinfo=timezone.utc)) == HalfDay(date(2026, 11, 10), "matin")


def test_naive_rejected():
    with pytest.raises(ValueError):
        half_day_of(datetime(2026, 11, 9, 10))


def test_shift_and_keys():
    h = HalfDay(date(2026, 11, 9), "matin")
    assert h.shift(-1) == HalfDay(date(2026, 11, 8), "apres_midi")
    assert h.shift(1) == HalfDay(date(2026, 11, 9), "apres_midi")
    assert h.shift(2) == HalfDay(date(2026, 11, 10), "matin")
    assert h.shift(-3).shift(3) == h
    assert HalfDay.from_key(h.key) == h
    assert h.key == "2026-11-09_matin"
    assert h < h.shift(1)
    assert HalfDay(date(2026, 3, 1), "matin").shift(-1) == HalfDay(date(2026, 2, 28), "apres_midi")


def test_bad_key():
    with pytest.raises(ValueError):
        HalfDay.from_key("2026-11-09_soir")


def test_local_from_naive_dst():
    assert local_from_naive(date(2026, 7, 1), 10).utcoffset().total_seconds() == 7200
    assert local_from_naive(date(2026, 11, 9), 10).tzinfo is TZ
