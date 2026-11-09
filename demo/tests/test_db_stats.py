from datetime import date

import db
import stats
from periods import local_from_naive


def add(conn, when=None, **cls):
    i = db.insert_avis(conn, transcript="x", langue="fr", duree_s=3, borne_id=cls.pop("borne", "col_porte"),
                       source=cls.pop("source", "borne"), lat=45.0, lon=5.7, event_ts=when)
    if cls:
        db.set_classification(conn, i, cls, {"answers": {}}, "m")
    return i


def test_insert_and_window(conn):
    a = add(conn, local_from_naive(date(2026, 11, 8), 9), note=4.0)
    b = add(conn, local_from_naive(date(2026, 11, 8), 15), note=2.0)
    assert [r["id"] for r in db.avis_in_window(conn, "2026-11-08_matin")] == [a]
    assert [r["id"] for r in db.avis_in_window(conn, "2026-11-08_apres_midi")] == [b]
    assert len(db.avis_in_window(conn, None)) == 2
    assert db.get_avis(conn, a)["classif_status"] == "ok"


def test_error_and_pending(conn):
    i = add(conn)
    db.set_classification_error(conn, i, "boom")
    assert db.get_avis(conn, i)["classif_status"] == "error"
    db.set_pending(conn, i)
    assert db.get_avis(conn, i)["classif_error"] is None


def test_commands_consumed_once(conn):
    db.push_command(conn, "start", borne_id="col_porte", source="app")
    db.push_command(conn, "stop")
    assert [r["cmd"] for r in db.pop_commands(conn)] == ["start", "stop"]
    assert db.pop_commands(conn) == []


def test_live_state(conn):
    db.set_live(conn, status="recording", partial_text="bon")
    assert db.get_live(conn)["status"] == "recording"


def test_stats(conn):
    add(conn, note=4.6, profil="touriste", affluence="saturee", mode_venue="voiture")
    add(conn, note=2.5, profil="excursionniste", affluence="faible", borne="moliere", source="app")
    add(conn, note=3.0, profil=None, affluence=None)
    add(conn)  # pending : ignoré par les critères classifiés
    df = stats.to_df(db.avis_in_window(conn, None))
    hist, mean, n = stats.notes(df)
    assert n == 3 and abs(mean - (4.6 + 2.5 + 3.0) / 3) < 1e-9
    assert dict(zip(hist["note"], hist["avis"])) == {1: 0, 2: 0, 3: 2, 4: 0, 5: 1}  # 2.5 -> 3
    prof, nm = stats.categorical(df, "profil")
    assert nm == 1 and dict(zip(prof["valeur"], prof["avis"])) == {"Touriste": 1, "Excursionniste": 1, "Local": 0}
    assert abs(prof["part"].sum() - 1) < 1e-9
    sat = dict(zip(*stats.saturation(df).values.T))
    assert sat == {"Saturée": 1, "Non saturée": 1, "Non mentionné": 1}
    vol = stats.volume(df)
    assert vol["avis"].sum() == 4
    assert int(vol[(vol.borne == "La Molière") & (vol.source == "app")]["avis"].iloc[0]) == 1
    aff = stats.affluence_par_borne(df).set_index("borne")
    assert aff.loc["Col de Porte", "affluence"] == 3.0 and aff.loc["La Molière", "affluence"] == 1.0


def test_stats_empty(conn):
    df = stats.to_df([])
    assert stats.notes(df)[1] is None
    assert stats.categorical(df, "profil")[0]["part"].sum() == 0
