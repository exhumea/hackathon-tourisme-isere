"""Classification d'un avis avec Jev (TypeSafe) via l'API Decisions d'OpenRouter.

Un seul appel POST /api/alpha/decisions par avis, toutes les questions groupées
(Jev y répond en parallèle). Règle « missing data » : chaque Choice a une option
`non_mentionne` ; si elle gagne (ou si Jev refuse la question), la colonne vaut NULL.
La note (Score 1-5) est toujours inférée.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

ENDPOINT = os.environ.get("JEV_ENDPOINT", "https://openrouter.ai/api/alpha/decisions")
MODEL = os.environ.get("JEV_MODEL", "typesafe/jev-1.13")
TIMEOUT_S = float(os.environ.get("JEV_TIMEOUT_S", "20"))
NON_MENTIONNE = "non_mentionne"

_NM = "La conversation n'aborde pas ce point, ou pas assez clairement pour trancher."

QUESTIONS: dict[str, dict[str, Any]] = {
    "profil": {
        "type": "choice",
        "instructions": "Quel est le profil de séjour de la personne interrogée ?",
        "criteria": {
            "touriste": "A passé au moins une nuit hors de son domicile pour ce séjour (hôtel, gîte, camping, location, famille…).",
            "excursionniste": "Venue à la journée, sans nuitée sur place, depuis un domicile éloigné.",
            "local": "Habite à proximité (commune voisine, agglomération proche) et pratique le site régulièrement.",
            NON_MENTIONNE: _NM,
        },
    },
    "origine": {
        "type": "choice",
        "instructions": "Où la personne interrogée réside-t-elle ?",
        "criteria": {
            "isere": "Réside en Isère (dont Grenoble et sa métropole).",
            "autre_france": "Réside en France, hors Isère.",
            "etranger": "Réside hors de France.",
            NON_MENTIONNE: _NM,
        },
    },
    "groupe": {
        "type": "choice",
        "instructions": "Avec qui la personne est-elle venue ?",
        "criteria": {
            "seul": "Seule.",
            "couple": "En couple, à deux.",
            "famille": "En famille, avec des enfants ou des proches.",
            "amis": "Entre amis.",
            "groupe_organise": "Groupe encadré : club, sortie guidée, association, scolaire.",
            NON_MENTIONNE: _NM,
        },
    },
    "mode_venue": {
        "type": "choice",
        "instructions": "Comment la personne est-elle venue jusqu'au départ de la randonnée ?",
        "criteria": {
            "voiture": "En voiture, moto ou covoiturage.",
            "transport_en_commun": "En bus, car, train ou navette.",
            "velo": "À vélo.",
            "a_pied": "À pied depuis son hébergement ou son domicile.",
            "autre": "Un autre moyen (taxi, stop, remontée mécanique…).",
            NON_MENTIONNE: _NM,
        },
    },
    "affluence": {
        "type": "choice",
        "instructions": "Comment la personne a-t-elle ressenti la fréquentation du site (nombre de personnes, parking, sentier) ?",
        "criteria": {
            "faible": "Peu de monde, site calme.",
            "normale": "Fréquentation jugée normale ou acceptable.",
            "saturee": "Trop de monde, saturation, parking plein, foule, file d'attente.",
            NON_MENTIONNE: _NM,
        },
    },
    "revenir": {
        "type": "choice",
        "instructions": "La personne exprime-t-elle l'intention de revenir ?",
        "criteria": {
            "oui": "Elle compte revenir ou recommanderait le site.",
            "non": "Elle ne compte pas revenir.",
            NON_MENTIONNE: _NM,
        },
    },
    "note": {
        "type": "score",
        "instructions": "Quelle est la satisfaction globale de la personne sur sa visite, déduite de l'ensemble de la conversation ?",
        "criteria": [
            "1 - Très insatisfaite",
            "2 - Plutôt insatisfaite",
            "3 - Mitigée",
            "4 - Plutôt satisfaite",
            "5 - Très satisfaite",
        ],
    },
}

CHOICE_COLUMNS = [k for k, q in QUESTIONS.items() if q["type"] == "choice"]
OPTIONS = {k: [o for o in QUESTIONS[k]["criteria"] if o != NON_MENTIONNE] for k in CHOICE_COLUMNS}


class JevError(RuntimeError):
    pass


def build_request(transcript: str, lieu: str, langue: str | None, model: str = MODEL) -> dict[str, Any]:
    return {
        "model": model,
        "state": {
            "contexte": "Enquête de satisfaction auprès de randonneurs en montagne (Isère). "
                        "Transcription automatique d'une conversation enregistrée au départ d'une randonnée ; "
                        "elle peut contenir des erreurs de transcription et la voix de l'enquêteur.",
            "lieu": lieu,
            "langue": langue or "inconnue",
            "transcription": transcript,
        },
        "questions": QUESTIONS,
    }


def parse_answers(answers: dict[str, Any]) -> dict[str, Any]:
    """Réponse Jev -> colonnes de la table `avis` (NULL si non mentionné / refus)."""
    out: dict[str, Any] = {}
    for col in CHOICE_COLUMNS:
        a = answers.get(col) or {}
        choice = a.get("choice") if a.get("type") == "choice" else None
        out[col] = choice if choice in OPTIONS[col] else None
    a = answers.get("note") or {}
    if a.get("type") == "score" and isinstance(a.get("score"), (int, float)):
        out["note"] = min(5.0, max(1.0, float(a["score"]) + 1.0))  # index 0..4 -> note 1..5
    else:
        out["note"] = None
    return out


def classify(transcript: str, lieu: str, langue: str | None, *, client: httpx.Client | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Retourne (colonnes, réponse brute). Lève JevError en cas d'échec."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise JevError("OPENROUTER_API_KEY non définie")
    body = build_request(transcript, lieu, langue)
    own = client is None
    client = client or httpx.Client(timeout=TIMEOUT_S)
    try:
        r = client.post(ENDPOINT, json=body, headers={"Authorization": f"Bearer {key}"})
    except httpx.HTTPError as e:
        raise JevError(f"réseau : {e}") from e
    finally:
        if own:
            client.close()
    if r.status_code != 200:
        raise JevError(f"HTTP {r.status_code} : {r.text[:300]}")
    try:
        raw = r.json()
        answers = raw["answers"]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise JevError(f"réponse inattendue : {r.text[:300]}") from e
    return parse_answers(answers), raw
