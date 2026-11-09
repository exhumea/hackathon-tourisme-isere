import time
import wave

import numpy as np
import pytest

import db
import jev
import worker
from worker import SR, choose_language


def test_choose_language():
    c, d = ("fr", "en", "de"), "fr"
    assert choose_language([("en", 0.27), ("la", 0.2)], c, d, 0.5) == "fr"   # anglais peu sûr -> défaut
    assert choose_language([("en", 0.88), ("fr", 0.05)], c, d, 0.5) == "en"
    assert choose_language([("fr", 0.3), ("en", 0.25)], c, d, 0.5) == "fr"
    assert choose_language([("ja", 0.9)], c, d, 0.5) == "fr"                 # hors candidates
    assert choose_language([("ja", 0.9), ("de", 0.6)], c, d, 0.5) == "de"


def _wav(path, pattern):
    """pattern : liste de (durée_s, parole?) ; la « parole » est une sinusoïde."""
    parts = []
    for dur, speech in pattern:
        t = np.arange(int(dur * SR)) / SR
        parts.append(0.3 * np.sin(2 * np.pi * 220 * t) if speech else np.zeros_like(t))
    pcm = (np.concatenate(parts) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


def _energy_segments(audio):
    """VAD factice : segments où le signal est non nul (pas de modèle à charger)."""
    on = np.abs(audio) > 1e-3
    segs, start = [], None
    for i in range(0, len(audio), 160):
        v = on[i:i + 160].any()
        if v and start is None:
            start = i
        if not v and start is not None:
            segs.append({"start": start, "end": i}); start = None
    if start is not None:
        segs.append({"start": start, "end": len(audio)})
    merged = []
    for s in segs:  # fusion des pauses < MIN_SILENCE_MS, comme silero
        if merged and s["start"] - merged[-1]["end"] < worker.MIN_SILENCE_MS / 1000 * SR:
            merged[-1]["end"] = s["end"]
        else:
            merged.append(s)
    return merged


class FakeSTT:
    def __init__(self):
        self.calls = []

    def detect(self, audio):
        return "fr"

    def transcribe(self, audio, language, beam_size, prompt):
        self.calls.append(round(len(audio) / SR, 1))
        return f"phrase{len(self.calls)}"


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, "TICK_S", 0.0)
    monkeypatch.setattr(worker, "speech_segments", _energy_segments)
    calls = []

    def fake_classify(transcript, lieu, langue):
        calls.append((transcript, lieu, langue))
        return {"profil": "touriste", "note": 4.0}, {"model": "typesafe/jev-test", "answers": {}}

    monkeypatch.setattr(jev, "classify", fake_classify)
    path = tmp_path / "w.db"
    return path, calls


def _drain(w):
    w.pool.shutdown(wait=True)


def test_full_recording(tmp_path, setup):
    path, calls = setup
    wav = tmp_path / "a.wav"
    _wav(wav, [(4, True), (1.5, False), (3, True), (1, False)])
    conn = db.connect(path)
    stt = FakeSTT()
    w = worker.Worker(conn, path, worker.FileSource([str(wav)], realtime=False), stt)
    db.push_command(conn, "start", borne_id="sept_laux", source="app")
    w.step()                       # start + lecture complète du fichier
    assert db.get_live(conn)["status"] == "recording"
    w.step()                       # 1er tick : détection de langue (aucune transcription)
    assert w.rec.language == "fr" and stt.calls == []
    w.step()                       # 2e tick : tout l'audio est là -> une seule passe jusqu'à la dernière pause
    assert db.get_live(conn)["committed_text"] == "phrase1" and len(stt.calls) == 1
    w.step()                       # 3e tick : ne reste que du silence -> aucune passe
    assert len(stt.calls) == 1
    db.push_command(conn, "stop")
    w.step()
    _drain(w)
    (row,) = db.latest_avis(conn)
    assert row["transcript"] == "phrase1" and row["langue"] == "fr"
    assert row["classif_status"] == "ok" and row["profil"] == "touriste" and row["note"] == 4.0
    assert row["source"] == "app" and row["duree_s"] == 9.5
    assert calls == [("phrase1", "Les 7 Laux (Prapoutel)", "fr")]
    assert db.get_live(conn)["status"] == "idle"
    assert len(stt.calls) == 1  # aucune retranscription au stop


def test_silence_only_creates_nothing(tmp_path, setup):
    path, calls = setup
    wav = tmp_path / "s.wav"
    _wav(wav, [(6, False)])
    conn = db.connect(path)
    w = worker.Worker(conn, path, worker.FileSource([str(wav)], realtime=False), FakeSTT())
    db.push_command(conn, "start", borne_id="col_porte", source="borne")
    w.step(); w.step()
    db.push_command(conn, "stop")
    w.step(); _drain(w)
    assert db.latest_avis(conn) == [] and calls == []
    assert db.get_live(conn)["message"] == "aucune parole détectée"


def test_short_recording_detects_on_stop(tmp_path, setup):
    path, _ = setup
    wav = tmp_path / "c.wav"
    _wav(wav, [(1.5, True)])
    conn = db.connect(path)
    w = worker.Worker(conn, path, worker.FileSource([str(wav)], realtime=False), FakeSTT())
    db.push_command(conn, "start", borne_id="col_porte", source="borne", event_ts_override="2026-11-01T10:00:00+01:00", is_init=1)
    w.step()
    db.push_command(conn, "stop")
    w.step(); _drain(w)
    (row,) = db.latest_avis(conn)
    assert row["langue"] == "fr" and row["demi_journee"] == "2026-11-01_matin" and row["is_init"] == 1


def test_jev_error_then_reclassify(tmp_path, setup, monkeypatch):
    path, _ = setup
    wav = tmp_path / "c.wav"
    _wav(wav, [(1.5, True)])
    conn = db.connect(path)

    def boom(*a):
        raise jev.JevError("HTTP 503")

    monkeypatch.setattr(jev, "classify", boom)
    w = worker.Worker(conn, path, worker.FileSource([str(wav)], realtime=False), FakeSTT())
    db.push_command(conn, "start", borne_id="col_porte", source="borne")
    w.step(); db.push_command(conn, "stop"); w.step()
    for _ in range(50):
        if db.latest_avis(conn)[0]["classif_status"] != "pending":
            break
        time.sleep(0.05)
    row = db.latest_avis(conn)[0]
    assert row["classif_status"] == "error" and "503" in row["classif_error"]
    monkeypatch.setattr(jev, "classify", lambda *a: ({"note": 2.0}, {"answers": {}}))
    db.push_command(conn, "reclassify", avis_id=row["id"])
    w.step(); _drain(w)
    row = db.get_avis(conn, row["id"])
    assert row["classif_status"] == "ok" and row["note"] == 2.0 and row["jev_model"] == jev.MODEL


def test_invalid_start_and_double_start(tmp_path, setup):
    path, _ = setup
    wav = tmp_path / "c.wav"
    _wav(wav, [(1.5, True)])
    conn = db.connect(path)
    w = worker.Worker(conn, path, worker.FileSource([str(wav)], realtime=False), FakeSTT())
    db.push_command(conn, "start", borne_id="nulle_part", source="borne")
    w.step()
    assert w.rec is None
    db.push_command(conn, "start", borne_id="col_porte", source="borne")
    db.push_command(conn, "start", borne_id="moliere", source="app")
    w.step()
    assert w.rec.borne_id == "col_porte"


class StepSource:
    """Source qui livre l'audio par tranches, pour simuler l'arrivée progressive en live."""

    def __init__(self, audio, step_s):
        self.audio, self.n, self.pos = audio, int(step_s * SR), 0

    def start(self):
        self.pos = 0

    def read(self):
        out = self.audio[self.pos:self.pos + self.n]
        self.pos += self.n
        return out

    def stop(self):
        pass


def test_live_chunks_and_partials(tmp_path, setup):
    path, _ = setup
    wav = tmp_path / "a.wav"
    _wav(wav, [(4, True), (1.5, False), (3, True)])
    from faster_whisper import decode_audio
    conn = db.connect(path)
    stt = FakeSTT()
    w = worker.Worker(conn, path, StepSource(decode_audio(str(wav), sampling_rate=SR), 1.0), stt)
    db.push_command(conn, "start", borne_id="col_porte", source="borne")
    live = []
    for _ in range(9):
        w.step()
        l = db.get_live(conn)
        live.append((l["committed_text"], l["partial_text"]))
    # pendant la 1re phrase : partiels ; après la pause : 1re phrase validée ; puis partiels de la 2e
    assert any(p and not c for c, p in live), live
    assert any(c and p for c, p in live), live
    db.push_command(conn, "stop")
    w.step(); _drain(w)
    row = db.latest_avis(conn)[0]
    first, *rest = row["transcript"].split()
    assert len(rest) == 1  # 1re phrase validée une fois + fin transcrite au stop
