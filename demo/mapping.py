"""Pur : questions Jev ↔ colonnes de `inference_avis`, réponse Jev → valeurs, seuil de confiance.

Règle « missing data » (§4), sur toutes les colonnes : refus, valeur absente ou confiance
< `SEUIL_CONFIANCE` → NULL. Si Jev ne renvoie pas de confiance pour une question, la
valeur est gardée telle quelle (go/no-go §10).
"""

from __future__ import annotations

import os
from typing import Any

SEUIL_CONFIANCE = float(os.environ.get("SEUIL_CONFIANCE", "0.6"))  # à fixer au jour 1 sur des avis réels

SCORE_COLUMNS = ("satisfaction", "affluence")
CHOICE_OPTIONS: dict[str, tuple[str, ...]] = {
    "provenance": ("departement", "hors_departement"),
    "transport": ("voiture", "transport_en_commun", "velo"),
    "profil": ("groupe_amis", "famille", "seul", "couple"),
}
COLUMNS = (*SCORE_COLUMNS, *CHOICE_OPTIONS)

_EXPLICITE = " Réponds uniquement si la conversation le dit explicitement ; ne déduis rien."


def questions(departement: str) -> dict[str, dict[str, Any]]:
    """Les 5 questions, envoyées en un seul appel (objet indexé par nom de colonne)."""
    return {
        "satisfaction": {
            "type": "score",
            "instructions": "Quelle satisfaction globale le visiteur exprime-t-il dans la conversation ?",
            "criteria": [
                "0 - Très insatisfait",
                "25 - Plutôt insatisfait",
                "50 - Mitigé ou neutre",
                "75 - Plutôt satisfait",
                "100 - Très satisfait",
            ],
        },
        "affluence": {
            "type": "score",
            "instructions": "Quelle affluence le visiteur a-t-il ressentie sur le site (monde, parking, sentier) ?",
            "criteria": [
                "0 - Personne, site désert",
                "25 - Peu de monde, calme",
                "50 - Fréquentation normale",
                "75 - Beaucoup de monde",
                "100 - Beaucoup trop de monde, saturation",
            ],
        },
        "provenance": {
            "type": "choice",
            "instructions": f"Le visiteur habite-t-il dans le département ({departement}) ou en dehors ?",
            "criteria": {
                "departement": f"Habite dans le département ({departement}).",
                "hors_departement": f"Habite hors du département ({departement}), en France ou à l'étranger.",
            },
        },
        "transport": {
            "type": "choice",
            "instructions": "Quel moyen de transport le visiteur a-t-il utilisé pour venir ?" + _EXPLICITE,
            "criteria": {
                "voiture": "Voiture, moto ou covoiturage. Exemple : « le parking est plein ».",
                "transport_en_commun": "Bus, car, train ou navette. "
                "Exemple : « les horaires des bus ne sont pas pratiques ».",
                "velo": "Vélo. Exemple : « pas pratique pour les vélos ».",
            },
        },
        "profil": {
            "type": "choice",
            "instructions": "Avec qui le visiteur est-il venu ?" + _EXPLICITE,
            "criteria": {
                "groupe_amis": "Entre amis, en groupe.",
                "famille": "En famille, avec des enfants ou des proches.",
                "seul": "Seul.",
                "couple": "En couple, à deux.",
            },
        },
    }


def _confiant(answer: dict[str, Any], seuil: float) -> bool:
    conf = answer.get("confidence")
    return conf is None or float(conf) >= seuil


def _score(answer: dict[str, Any], n_levels: int) -> float | None:
    """`score` est un index pondéré à partir de 0 sur `n_levels` niveaux → 0..100."""
    s = answer.get("score")
    if not isinstance(s, int | float):
        return None
    return min(100.0, max(0.0, float(s) / (n_levels - 1) * 100.0))


def parse(answers: dict[str, Any], departement: str, seuil: float = SEUIL_CONFIANCE) -> dict[str, Any]:
    """Réponse Jev (`answers`) → {colonne: valeur ou None}."""
    qs = questions(departement)
    out: dict[str, Any] = dict.fromkeys(COLUMNS)
    for col in SCORE_COLUMNS:
        a = answers.get(col) or {}
        if a.get("type") == "score" and _confiant(a, seuil):
            out[col] = _score(a, len(qs[col]["criteria"]))
    for col, options in CHOICE_OPTIONS.items():
        a = answers.get(col) or {}
        if a.get("type") == "choice" and a.get("choice") in options and _confiant(a, seuil):
            out[col] = a["choice"]
    return out
