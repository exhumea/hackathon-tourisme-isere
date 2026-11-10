import mapping

ANSWERS = {
    "satisfaction": {"type": "score", "score": 3.0, "confidence": 0.9},
    "affluence": {"type": "score", "score": 1.0, "confidence": 0.8},
    "provenance": {"type": "choice", "choice": "hors_departement", "confidence": 0.95},
    "transport": {"type": "choice", "choice": "voiture", "confidence": 0.3},
    "profil": {"type": "refusal"},
}


def test_une_question_par_colonne():
    qs = mapping.questions("Isère")
    assert set(qs) == set(mapping.COLUMNS)
    for col, opts in mapping.CHOICE_OPTIONS.items():
        assert tuple(qs[col]["criteria"]) == opts
    assert "Isère" in qs["provenance"]["instructions"]


def test_parse():
    out = mapping.parse(ANSWERS, "Isère", seuil=0.6)
    assert out == {
        "satisfaction": 75.0,  # index 3 sur 5 niveaux
        "affluence": 25.0,
        "provenance": "hors_departement",
        "transport": None,  # confiance trop faible : no guess
        "profil": None,  # refus
    }


def test_seuil_sur_les_scores_aussi():
    out = mapping.parse({"satisfaction": {"type": "score", "score": 4, "confidence": 0.5}}, "Isère", seuil=0.6)
    assert out["satisfaction"] is None


def test_sans_confiance_la_valeur_est_gardee():
    out = mapping.parse({"profil": {"type": "choice", "choice": "famille"}}, "Isère", seuil=0.6)
    assert out["profil"] == "famille"


def test_valeurs_hors_options_ou_absentes():
    out = mapping.parse({"transport": {"type": "choice", "choice": "avion", "confidence": 1}}, "Isère")
    assert out == dict.fromkeys(mapping.COLUMNS)


def test_score_borne():
    out = mapping.parse({"affluence": {"type": "score", "score": 7, "confidence": 1}}, "Isère")
    assert out["affluence"] == 100.0
