"""Worker : micro -> VAD -> faster-whisper (live) -> SQLite -> Jev.

Pilote par la table `control` (commandes écrites par l'app Streamlit).
Lancement : `uv run python worker.py` (voir README pour les options).
"""

from __future__ import annotations

import argparse
import logging
import os
import queue
import re
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np

import bornes
import db
import jev
from periods import parse_ts

SR = 16_000
TICK_S = 2.0               # période de retranscription du chunk en cours (texte partiel)
MIN_SILENCE_MS = 700       # pause qui clôt un chunk
MAX_UNCOMMITTED_S = 20.0   # au-delà, on valide de force pour borner le coût des partiels
LANG_LOCK_MIN_S = 3.0      # durée minimale d'audio pour verrouiller la langue
# Détection auto restreinte aux langues plausibles ; une langue autre que la langue par défaut
# n'est retenue que si Whisper en est assez sûr (évite qu'un français mal détecté soit « traduit »).
CANDIDATE_LANGS = tuple(os.environ.get("DEMO_LANGS", "fr,en,de,it,nl,es").split(","))
DEFAULT_LANG = os.environ.get("DEMO_DEFAULT_LANG", "fr")
LANG_MIN_PROB = float(os.environ.get("DEMO_LANG_MIN_PROB", "0.5"))
HEARTBEAT_S = 1.0
TOKENS_PER_S = 8           # parole ≈ 3-5 tokens/s : marge x2

# Hallucinations classiques de Whisper sur du silence / bruit (surtout en français).
_HALLUCINATIONS = re.compile(
    r"sous-titr|amara\.org|merci d'avoir regard|abonnez-vous|thanks for watching|untertitel",
    re.IGNORECASE,
)

log = logging.getLogger("worker")


# --- sources audio ----------------------------------------------------------

class MicSource:
    """Micro du laptop via sounddevice (PortAudio)."""

    def __init__(self, device: str | int | None = None):
        import sounddevice as sd  # import tardif : PortAudio n'est requis qu'en mode micro

        self._sd = sd
        self.device = device
        self._q: queue.Queue[np.ndarray] = queue.Queue()
        self._stream = None

    def start(self) -> None:
        def cb(indata, frames, t, status):  # thread PortAudio
            if status:
                log.warning("audio: %s", status)
            self._q.put(indata[:, 0].copy())

        self._q = queue.Queue()
        self._stream = self._sd.InputStream(samplerate=SR, channels=1, dtype="float32",
                                            device=self.device, callback=cb, blocksize=1600)
        self._stream.start()

    def read(self) -> np.ndarray:
        parts = []
        while True:
            try:
                parts.append(self._q.get_nowait())
            except queue.Empty:
                break
        return np.concatenate(parts) if parts else np.zeros(0, np.float32)

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None


class FileSource:
    """Rejoue des fichiers audio en temps réel, un par enregistrement (répétition / tests sans micro)."""

    def __init__(self, paths: list[str], realtime: bool = True):
        from faster_whisper import decode_audio

        self._clips = [decode_audio(p, sampling_rate=SR) for p in paths]
        self._i = 0
        self.realtime = realtime
        self._clip = np.zeros(0, np.float32)
        self._pos = 0
        self._t0 = 0.0

    def start(self) -> None:
        self._clip = self._clips[self._i % len(self._clips)]
        self._i += 1
        self._pos = 0
        self._t0 = time.monotonic()

    @property
    def exhausted(self) -> bool:
        return self._pos >= len(self._clip)

    def read(self) -> np.ndarray:
        end = len(self._clip) if not self.realtime else min(len(self._clip), int((time.monotonic() - self._t0) * SR))
        out = self._clip[self._pos:end]
        self._pos = max(self._pos, end)
        return out

    def stop(self) -> None:
        pass


# --- transcription ----------------------------------------------------------

class Transcriber:
    def __init__(self, model_size: str, compute_type: str, cpu_threads: int, download_root: Path):
        from faster_whisper import WhisperModel

        t0 = time.monotonic()
        kw = dict(device="cpu", compute_type=compute_type, cpu_threads=cpu_threads, download_root=str(download_root))
        try:  # hors ligne d'abord : la salle peut ne pas avoir de réseau
            self.model = WhisperModel(model_size, local_files_only=True, **kw)
        except Exception:
            log.info("modèle %s absent localement : téléchargement dans %s", model_size, download_root)
            self.model = WhisperModel(model_size, **kw)
        log.info("modèle %s (%s) chargé en %.1f s", model_size, compute_type, time.monotonic() - t0)

    def detect(self, audio: np.ndarray) -> str:
        t0 = time.monotonic()
        _, _, probs = self.model.detect_language(audio)
        lang = choose_language(probs, CANDIDATE_LANGS, DEFAULT_LANG, LANG_MIN_PROB)
        top = ", ".join(f"{l}={p:.2f}" for l, p in probs[:3])
        log.info("langue : %s (top : %s) en %.2fs", lang, top, time.monotonic() - t0)
        return lang

    def transcribe(self, audio: np.ndarray, language: str, beam_size: int, prompt: str | None) -> str:
        t0 = time.monotonic()
        segments, _ = self.model.transcribe(
            audio, language=language, beam_size=beam_size, vad_filter=False,
            condition_on_previous_text=False, initial_prompt=prompt or None,
            # latence bornée en live : pas de ré-essais à température croissante, et un plafond de
            # tokens proportionnel à la durée (une boucle d'hallucination ne peut pas s'éterniser)
            temperature=0.0, max_new_tokens=min(440, int(len(audio) / SR * TOKENS_PER_S) + 16),
        )
        texts = [s.text.strip() for s in segments if not _HALLUCINATIONS.search(s.text)]
        dt = time.monotonic() - t0
        dur = len(audio) / SR
        log.info("stt %.1fs audio en %.2fs (RTF %.2f, beam %d, %s)", dur, dt, dt / max(dur, 1e-6), beam_size, language)
        return " ".join(t for t in texts if t)


def choose_language(probs: list[tuple[str, float]], candidates: tuple[str, ...], default: str, min_prob: float) -> str:
    """Meilleure langue parmi les candidates ; la langue par défaut sauf si une autre est assez probable."""
    cands = [(l, p) for l, p in probs if l in candidates]
    if not cands:
        return default
    best, p = max(cands, key=lambda lp: lp[1])
    return best if best == default or p >= min_prob else default


def speech_segments(audio: np.ndarray) -> list[dict]:
    from faster_whisper.vad import VadOptions, get_speech_timestamps

    if len(audio) < SR // 4:
        return []
    return get_speech_timestamps(audio, VadOptions(min_silence_duration_ms=MIN_SILENCE_MS, speech_pad_ms=200))


# --- enregistrement en cours ------------------------------------------------

@dataclass
class Recording:
    borne_id: str
    source: str
    event_ts: datetime | None
    is_init: bool
    audio: list[np.ndarray] = field(default_factory=list)
    n_samples: int = 0
    committed_pos: int = 0
    committed: list[str] = field(default_factory=list)
    language: str | None = None     # verrouillée une fois par enregistrement
    last_tick: float = 0.0
    partial_key: tuple[int, int] | None = None  # (committed_pos, n_samples) du dernier partiel
    _flat: np.ndarray | None = None

    def append(self, chunk: np.ndarray) -> None:
        if len(chunk):
            self.audio.append(chunk)
            self.n_samples += len(chunk)
            self._flat = None

    def flat(self) -> np.ndarray:
        if self._flat is None:
            self._flat = np.concatenate(self.audio) if self.audio else np.zeros(0, np.float32)
            self.audio = [self._flat]
        return self._flat

    @property
    def committed_text(self) -> str:
        return " ".join(t for t in self.committed if t)


class Worker:
    def __init__(self, conn: sqlite3.Connection, db_path: Path, source, stt: Transcriber, beam_size: int = 1):
        self.beam_size = beam_size
        self.conn = conn
        self.db_path = db_path
        self.source = source
        self.stt = stt
        self.rec: Recording | None = None
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="jev")
        self._last_hb = 0.0

    # -- boucle principale
    def run_forever(self) -> None:
        db.set_live(self.conn, status="idle", committed_text="", partial_text="", message="prêt")
        for row in self.conn.execute("SELECT id FROM avis WHERE classif_status = 'pending'").fetchall():
            self.pool.submit(self._classify_job, row["id"])  # reprise après un arrêt
        log.info("worker prêt (base : %s)", self.db_path)
        while True:
            self.step()
            time.sleep(0.05)

    def step(self) -> None:
        now = time.monotonic()
        if now - self._last_hb >= HEARTBEAT_S:
            db.heartbeat(self.conn)
            self._last_hb = now
        for cmd in db.pop_commands(self.conn):
            self._handle(cmd)
        if self.rec is not None:
            self.rec.append(self.source.read())
            if now - self.rec.last_tick >= TICK_S:
                self.rec.last_tick = now
                self._tick()

    def _handle(self, cmd: sqlite3.Row) -> None:
        kind = cmd["cmd"]
        if kind == "start":
            if self.rec is not None:
                log.warning("start ignoré : enregistrement déjà en cours")
                return
            if cmd["borne_id"] not in bornes.BORNES or cmd["source"] not in bornes.SOURCES:
                db.set_live(self.conn, message=f"borne/source invalide : {cmd['borne_id']}/{cmd['source']}")
                return
            try:
                self.source.start()
            except Exception as e:  # micro absent, permission refusée…
                log.exception("ouverture audio impossible")
                db.set_live(self.conn, status="idle", message=f"micro indisponible : {e}")
                return
            override = cmd["event_ts_override"]
            self.rec = Recording(cmd["borne_id"], cmd["source"], parse_ts(override) if override else None,
                                 bool(cmd["is_init"]), last_tick=time.monotonic())
            db.set_live(self.conn, status="recording", committed_text="", partial_text="", langue=None,
                        borne_id=cmd["borne_id"], source=cmd["source"], message="enregistrement…")
            log.info("start (%s, %s)", cmd["borne_id"], cmd["source"])
        elif kind == "stop":
            if self.rec is None:
                return
            self._finish()
        elif kind == "reclassify":
            if cmd["avis_id"] is not None and db.get_avis(self.conn, cmd["avis_id"]) is not None:
                db.set_pending(self.conn, cmd["avis_id"])
                self.pool.submit(self._classify_job, cmd["avis_id"])

    # -- live : valide les chunks clos par une pause, retranscrit le chunk en cours.
    # Chaque appel Whisper coûte une passe d'encodeur complète : au plus une par tick.
    def _tick(self) -> None:
        rec = self.rec
        if rec.language is None:
            if rec.n_samples < LANG_LOCK_MIN_S * SR or not speech_segments(rec.flat()):
                return
            rec.language = self.stt.detect(rec.flat()[: 30 * SR])
            db.set_live(self.conn, langue=rec.language)
            return
        buf = rec.flat()[rec.committed_pos:]
        if len(buf) < SR // 2:
            return
        segs = speech_segments(buf)
        if not segs:
            if len(buf) > 5 * SR:
                rec.committed_pos += len(buf)  # que du silence : on avance sans transcrire
                db.set_live(self.conn, partial_text="")
            return
        sil = int(MIN_SILENCE_MS / 1000 * SR)
        cut = None
        if len(buf) - segs[-1]["end"] >= sil:
            cut = segs[-1]["end"]
        elif len(segs) >= 2:
            cut = segs[-2]["end"]
        elif len(buf) > MAX_UNCOMMITTED_S * SR:
            cut = len(buf)
        if cut is not None:
            rec.committed.append(self._transcribe(buf[:cut]))
            rec.committed_pos += cut
            partial = ""  # le reste sera retranscrit au tick suivant
        else:
            key = (rec.committed_pos, rec.n_samples)
            if key == rec.partial_key:
                return  # pas de nouvel audio depuis le dernier partiel
            rec.partial_key = key
            partial = self._transcribe(buf)
        db.set_live(self.conn, committed_text=rec.committed_text, partial_text=partial)

    def _transcribe(self, audio: np.ndarray) -> str:
        rec = self.rec
        prompt = rec.committed_text[-200:] if rec.committed else None
        return self.stt.transcribe(audio, rec.language, self.beam_size, prompt)

    def _finish(self) -> None:
        rec = self.rec
        self.source.stop()
        rec.append(self.source.read())
        db.set_live(self.conn, status="transcribing", partial_text="", message="transcription finale…")
        rest = rec.flat()[rec.committed_pos:]
        if speech_segments(rest):
            if rec.language is None:  # enregistrement court : détection sur tout l'audio
                rec.language = self.stt.detect(rec.flat()[: 30 * SR])
            rec.committed.append(self._transcribe(rest))
        transcript = rec.committed_text.strip()
        duree = rec.n_samples / SR
        self.rec = None
        if not transcript:
            db.set_live(self.conn, status="idle", committed_text="", message="aucune parole détectée")
            log.info("stop : aucune parole détectée (%.1f s)", duree)
            return
        lat, lon = bornes.position(rec.borne_id, rec.source)
        avis_id = db.insert_avis(self.conn, transcript=transcript, langue=rec.language, duree_s=round(duree, 1),
                                 borne_id=rec.borne_id, source=rec.source, lat=lat, lon=lon,
                                 event_ts=rec.event_ts, is_init=rec.is_init)
        db.set_live(self.conn, status="classifying", committed_text=transcript, message=f"avis #{avis_id} → Jev…")
        log.info("avis #%d enregistré (%.1f s, %s)", avis_id, duree, rec.language)
        self.pool.submit(self._classify_job, avis_id)

    # -- classification (thread du pool, connexion dédiée)
    def _classify_job(self, avis_id: int) -> None:
        conn = db.connect(self.db_path)
        try:
            row = db.get_avis(conn, avis_id)
            lieu = bornes.BORNES[row["borne_id"]].nom
            try:
                cols, raw = jev.classify(row["transcript"], lieu, row["langue"])
                db.set_classification(conn, avis_id, cols, raw, raw.get("model") or jev.MODEL)
                log.info("avis #%d classifié : %s", avis_id, cols)
                msg = f"avis #{avis_id} classifié"
            except jev.JevError as e:
                db.set_classification_error(conn, avis_id, str(e))
                log.error("avis #%d : échec Jev : %s", avis_id, e)
                msg = f"avis #{avis_id} : échec Jev"
            conn.execute("UPDATE live_state SET status = 'idle', message = ? WHERE id = 1 AND status = 'classifying'", (msg,))
        except Exception:
            log.exception("classification #%d", avis_id)
            db.set_classification_error(conn, avis_id, "erreur interne (voir logs du worker)")
        finally:
            conn.close()


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", type=Path, default=db.DEFAULT_PATH)
    p.add_argument("--model", default="small", help="taille faster-whisper (tiny, base, small, medium…)")
    p.add_argument("--compute-type", default="int8")
    p.add_argument("--beam", type=int, default=1, help="beam search (1 = greedy, le plus rapide)")
    p.add_argument("--threads", type=int, default=0, help="threads CPU (0 = auto)")
    p.add_argument("--models-dir", type=Path, default=Path(__file__).resolve().parent / "models")
    p.add_argument("--device", default=None, help="périphérique d'entrée (index ou nom, cf. --list-devices)")
    p.add_argument("--list-devices", action="store_true")
    p.add_argument("--simulate", nargs="+", metavar="AUDIO",
                   help="rejoue ces fichiers (un par enregistrement) au lieu du micro")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

    if args.list_devices:
        import sounddevice as sd
        print(sd.query_devices())
        return
    device = int(args.device) if args.device and args.device.isdigit() else args.device
    source = FileSource(args.simulate) if args.simulate else MicSource(device)
    if not args.simulate:
        import sounddevice as sd
        log.info("micro : %s", sd.query_devices(device if device is not None else sd.default.device[0])["name"])
    if not os.environ.get("OPENROUTER_API_KEY"):
        log.warning("OPENROUTER_API_KEY absente : les avis seront enregistrés en 'error' (re-classifiables)")
    conn = db.connect(args.db)
    db.set_live(conn, status="loading", message=f"chargement du modèle {args.model}…")
    stt = Transcriber(args.model, args.compute_type, args.threads, args.models_dir)
    worker = Worker(conn, args.db, source, stt, beam_size=args.beam)
    try:
        worker.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        db.set_live(conn, status="offline", message="worker arrêté")
        source.stop()


if __name__ == "__main__":
    sys.exit(main())
