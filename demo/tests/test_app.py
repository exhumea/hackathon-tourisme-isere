from datetime import date

from streamlit.testing.v1 import AppTest

import db
from periods import local_from_naive


def test_app_renders_all_criteria(tmp_path, monkeypatch):
    path = tmp_path / "app.db"
    monkeypatch.setenv("DEMO_DB", str(path))
    monkeypatch.setattr(db, "DEFAULT_PATH", path)
    c = db.connect(path)
    for i, (h, note, prof) in enumerate([(9, 4.4, "touriste"), (15, 2.1, None)]):
        a = db.insert_avis(c, transcript=f"avis {i}", langue="fr", duree_s=3, borne_id="col_porte",
                           source="app", lat=45.29, lon=5.77, event_ts=local_from_naive(date.today(), h))
        db.set_classification(c, a, {"note": note, "profil": prof, "affluence": "saturee"}, {"answers": {}}, "m")
    at = AppTest.from_file("../app.py", default_timeout=30).run()
    assert not at.exception, at.exception
    for crit in ["notes", "profil", "volume", "venue", "saturation"]:
        at.selectbox(key="crit").set_value(crit).run()
        assert not at.exception, (crit, at.exception)
    at.toggle(key="all_past").set_value(True).run()
    assert not at.exception
    at.toggle(key="all_past").set_value(False).run()
    at.button(key="prev").click().run()
    assert not at.exception and at.session_state.win is not None
    at.button(key="live").click().run()
    assert at.session_state.win is None
    # worker absent -> bouton Enregistrer désactivé
    assert at.button(key="btn_start").disabled
