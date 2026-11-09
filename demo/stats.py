"""Agrégats des critères affichés dans la vue « Frontend » (fonctions pures sur DataFrame)."""

from __future__ import annotations

import pandas as pd

from bornes import BORNES
from jev import OPTIONS

NM_LABEL = "Non mentionné"

LABELS = {
    "profil": {"touriste": "Touriste", "excursionniste": "Excursionniste", "local": "Local"},
    "mode_venue": {"voiture": "Voiture", "transport_en_commun": "Transport en commun", "velo": "Vélo",
                   "a_pied": "À pied", "autre": "Autre"},
    "affluence": {"faible": "Faible", "normale": "Normale", "saturee": "Saturée"},
}
AFFLUENCE_LEVEL = {"faible": 1, "normale": 2, "saturee": 3}

CRITERES = {
    "notes": "Distribution des notes",
    "profil": "Touriste / excursionniste / local",
    "volume": "Volume d'avis",
    "venue": "Mode de venue & affluence",
    "saturation": "Mention de saturation",
}


def to_df(rows) -> pd.DataFrame:
    cols = ["id", "event_ts", "demi_journee", "borne_id", "source", "lat", "lon", "profil", "origine",
            "groupe", "mode_venue", "affluence", "revenir", "note", "classif_status", "transcript"]
    df = pd.DataFrame([dict(r) for r in rows], columns=cols)
    df["note"] = pd.to_numeric(df["note"], errors="coerce")
    return df


def classified(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["classif_status"] == "ok"]


def notes(df: pd.DataFrame) -> tuple[pd.DataFrame, float | None, int]:
    """Histogramme de round(note) sur 1..5 (zéros inclus), moyenne sur la valeur continue, n."""
    n = df["note"].dropna()
    # arrondi « commercial » (2.5 -> 3), pas l'arrondi bancaire de pandas
    rounded = (n + 0.5).apply(int).clip(1, 5)
    counts = rounded.value_counts().reindex(range(1, 6), fill_value=0)
    hist = pd.DataFrame({"note": counts.index.astype(int), "avis": counts.values.astype(int)})
    return hist, (float(n.mean()) if len(n) else None), int(len(n))


def categorical(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    """Parts parmi les non-NULL (avis classifiés), et nombre de « non mentionné »."""
    c = classified(df)
    known = c[col].dropna()
    counts = known.value_counts().reindex(OPTIONS[col], fill_value=0)
    total = int(counts.sum())
    out = pd.DataFrame({
        "valeur": [LABELS.get(col, {}).get(k, k) for k in counts.index],
        "avis": counts.values.astype(int),
        "part": (counts.values / total) if total else [0.0] * len(counts),
    })
    return out, int(c[col].isna().sum())


def volume(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for bid, b in BORNES.items():
        for src in ("borne", "app"):
            rows.append({"borne": b.court, "source": src,
                         "avis": int(((df["borne_id"] == bid) & (df["source"] == src)).sum())})
    return pd.DataFrame(rows)


def affluence_par_borne(df: pd.DataFrame) -> pd.DataFrame:
    c = classified(df)
    rows = []
    for bid, b in BORNES.items():
        lv = c.loc[c["borne_id"] == bid, "affluence"].dropna().map(AFFLUENCE_LEVEL)
        rows.append({"borne": b.court,
                     "affluence": float(lv.mean()) if len(lv) else None, "avis": int(len(lv))})
    return pd.DataFrame(rows)


def saturation(df: pd.DataFrame) -> pd.DataFrame:
    """Saturée / non saturée (faible ou normale) / non mentionné, sur les avis classifiés."""
    a = classified(df)["affluence"]
    vals = {
        "Saturée": int((a == "saturee").sum()),
        "Non saturée": int(a.isin(["faible", "normale"]).sum()),
        NM_LABEL: int(a.isna().sum()),
    }
    return pd.DataFrame({"mention": list(vals), "avis": list(vals.values())})
