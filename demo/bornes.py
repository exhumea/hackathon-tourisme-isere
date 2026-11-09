"""Les 5 bornes fictives (départs de randonnée connus en Isère).

Coordonnées vérifiées sur OpenStreetMap (Nominatim) le 2026-11-09.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

APP_RADIUS_KM = 2.0
_KM_PER_DEG_LAT = 111.32


@dataclass(frozen=True)
class Borne:
    id: str
    nom: str
    court: str
    massif: str
    lat: float
    lon: float


BORNES: dict[str, Borne] = {
    b.id: b
    for b in (
        Borne("chamrousse", "Chamrousse 1750 (Roche Béranger) → Lac Blanc", "Chamrousse", "Belledonne", 45.1124, 5.8767),
        Borne("col_porte", "Col de Porte", "Col de Porte", "Chartreuse", 45.2899, 5.7670),
        Borne("moliere", "Plateau de la Molière", "La Molière", "Vercors", 45.1980, 5.5909),
        Borne("sept_laux", "Les 7 Laux (Prapoutel)", "7 Laux", "Belledonne", 45.2568, 5.9954),
        Borne("bourg_arud", "Bourg-d'Arud → Lac de la Muzelle", "Bourg-d'Arud", "Oisans", 44.9870, 6.1210),
    )
}

SOURCES = ("borne", "app")


def position(borne_id: str, source: str, rng: random.Random | None = None) -> tuple[float, float]:
    """Coordonnées d'un avis : exactes pour une borne, aléatoires (disque de 2 km) pour l'app."""
    b = BORNES[borne_id]
    if source == "borne":
        return b.lat, b.lon
    if source != "app":
        raise ValueError(f"source inconnue : {source!r}")
    rng = rng or random.Random()
    r_km = APP_RADIUS_KM * math.sqrt(rng.random())  # uniforme en surface
    theta = rng.uniform(0, 2 * math.pi)
    dlat = r_km * math.cos(theta) / _KM_PER_DEG_LAT
    dlon = r_km * math.sin(theta) / (_KM_PER_DEG_LAT * math.cos(math.radians(b.lat)))
    return b.lat + dlat, b.lon + dlon


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance haversine (pour les tests)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))
