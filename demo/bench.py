"""Benchmark STT sur la machine de démo : `uv run python bench.py audio.wav [--models base small]`.

Mesure le coût d'une passe (détection de langue, transcription d'un chunk de 5 s) : c'est ce qui
fixe la latence du texte partiel (~ période du tick + durée d'un appel).
"""

import argparse
import time
from pathlib import Path

from faster_whisper import decode_audio

from worker import SR, TICK_S, Transcriber


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("audio")
    p.add_argument("--models", nargs="+", default=["base", "small"])
    p.add_argument("--threads", type=int, default=0)
    p.add_argument("--reps", type=int, default=3)
    a = p.parse_args()
    audio = decode_audio(a.audio, sampling_rate=SR)
    chunk = audio[: 5 * SR]
    for m in a.models:
        stt = Transcriber(m, "int8", a.threads, Path(__file__).resolve().parent / "models")
        lang = stt.detect(audio[: 30 * SR])
        stt.transcribe(chunk, lang, 1, None)  # échauffement
        times = []
        for _ in range(a.reps):
            t0 = time.monotonic()
            text = stt.transcribe(chunk, lang, 1, None)
            times.append(time.monotonic() - t0)
        t = sorted(times)[len(times) // 2]
        verdict = "OK" if t <= 1.5 else ("limite" if t <= 3 else "trop lent")
        print(f"\n== {m} : chunk 5 s en {t:.2f} s (médiane) → partiel ≈ {TICK_S + t:.1f} s après la parole [{verdict}]")
        print(f"   langue={lang} texte={text!r}")


if __name__ == "__main__":
    main()
