"""Demi-journées (Europe/Paris).

Plages nominales : matin 6h-13h, après-midi 13h-20h. Un horodatage hors plage est
rattaché à la plage du même jour la plus proche (0h-6h -> matin, 20h-24h ->
après-midi), donc en pratique : heure locale < 13h -> matin, sinon après-midi.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Paris")
MATIN = "matin"
APRES_MIDI = "apres_midi"
_SLOTS = (MATIN, APRES_MIDI)
_LABELS = {MATIN: "Matin (6h-13h)", APRES_MIDI: "Après-midi (13h-20h)"}
_JOURS = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]


@dataclass(frozen=True)
class HalfDay:
    day: date
    slot: str  # MATIN | APRES_MIDI

    @property
    def index(self) -> int:
        """Rang chronologique (sert à l'ordre et au décalage)."""
        return self.day.toordinal() * 2 + _SLOTS.index(self.slot)

    def __lt__(self, other: "HalfDay") -> bool:
        return self.index < other.index

    def __le__(self, other: "HalfDay") -> bool:
        return self.index <= other.index

    def __gt__(self, other: "HalfDay") -> bool:
        return self.index > other.index

    def __ge__(self, other: "HalfDay") -> bool:
        return self.index >= other.index

    @property
    def key(self) -> str:
        return f"{self.day.isoformat()}_{self.slot}"

    @classmethod
    def from_key(cls, key: str) -> "HalfDay":
        day_s, slot = key.split("_", 1)
        if slot not in _SLOTS:
            raise ValueError(f"demi-journée invalide : {key!r}")
        return cls(date.fromisoformat(day_s), slot)

    def shift(self, n: int) -> "HalfDay":
        idx = self.index + n
        return HalfDay(date.fromordinal(idx // 2), _SLOTS[idx % 2])

    @property
    def label(self) -> str:
        return f"{_JOURS[self.day.weekday()]} {self.day.strftime('%d/%m')} · {_LABELS[self.slot]}"


def half_day_of(ts: datetime) -> HalfDay:
    """Demi-journée d'un horodatage *aware* (converti en heure de Paris)."""
    if ts.tzinfo is None:
        raise ValueError("horodatage naïf refusé : fournir un datetime avec fuseau")
    local = ts.astimezone(TZ)
    return HalfDay(local.date(), MATIN if local.hour < 13 else APRES_MIDI)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def current_half_day(now: datetime | None = None) -> HalfDay:
    return half_day_of(now or now_utc())


def parse_ts(s: str) -> datetime:
    ts = datetime.fromisoformat(s)
    if ts.tzinfo is None:
        raise ValueError(f"horodatage sans fuseau : {s!r}")
    return ts


def local_from_naive(d: date, hour: int, minute: int = 0) -> datetime:
    """Construit un horodatage aware en heure de Paris (pour la « date simulée »)."""
    return datetime(d.year, d.month, d.day, hour, minute, tzinfo=TZ)


__all__ = [
    "TZ", "MATIN", "APRES_MIDI", "HalfDay", "half_day_of", "current_half_day",
    "now_utc", "parse_ts", "local_from_naive",
]
