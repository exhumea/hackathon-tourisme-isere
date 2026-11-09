import httpx
import pytest

import jev


def answers(**over):
    base = {
        "profil": {"type": "choice", "choice": "touriste", "confidence": 0.8, "probabilities": {}},
        "origine": {"type": "choice", "choice": "non_mentionne", "confidence": 0.9, "probabilities": {}},
        "groupe": {"type": "choice", "choice": "famille", "confidence": 0.7, "probabilities": {}},
        "mode_venue": {"type": "refusal"},
        "affluence": {"type": "choice", "choice": "saturee", "confidence": 0.6, "probabilities": {}},
        "revenir": {"type": "choice", "choice": "oui", "confidence": 0.9, "probabilities": {}},
        "note": {"type": "score", "score": 3.2, "confidence": 0.8, "probabilities": {}, "legend": {}},
    }
    base.update(over)
    return base


def test_parse_maps_null_and_score():
    cols = jev.parse_answers(answers())
    assert cols == {"profil": "touriste", "origine": None, "groupe": "famille", "mode_venue": None,
                    "affluence": "saturee", "revenir": "oui", "note": pytest.approx(4.2)}


def test_parse_clamps_and_rejects_unknown_option():
    cols = jev.parse_answers(answers(note={"type": "score", "score": 4.0},
                                     profil={"type": "choice", "choice": "martien"}))
    assert cols["note"] == 5.0 and cols["profil"] is None
    assert jev.parse_answers(answers(note={"type": "score", "score": -0.5}))["note"] == 1.0
    assert jev.parse_answers({})["note"] is None


def test_request_shape():
    body = jev.build_request("bonjour", "Col de Porte", "fr")
    assert body["model"] == jev.MODEL
    assert body["state"]["transcription"] == "bonjour"
    for k, q in body["questions"].items():
        assert q["type"] in ("choice", "score")
        if q["type"] == "choice":
            assert jev.NON_MENTIONNE in q["criteria"] and all(isinstance(v, str) for v in q["criteria"].values())
        else:
            assert isinstance(q["criteria"], list) and len(q["criteria"]) == 5


def test_classify_http(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    seen = {}

    def handler(req):
        seen["auth"] = req.headers["authorization"]
        return httpx.Response(200, json={"model": "typesafe/jev-1.13-x", "answers": answers(), "usage": {}})

    cols, raw = jev.classify("t", "lieu", "fr", client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert seen["auth"] == "Bearer k" and cols["profil"] == "touriste" and raw["model"] == "typesafe/jev-1.13-x"


def test_classify_errors(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(jev.JevError):
        jev.classify("t", "l", "fr")
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    c = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(402, json={"error": {"code": 402}})))
    with pytest.raises(jev.JevError, match="402"):
        jev.classify("t", "l", "fr", client=c)
