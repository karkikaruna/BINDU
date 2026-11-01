"""Regenerate every lesson's pronunciation audio with Swar (Nepali TTS) instead of the old hosted MP3s.

    SWAR_BASE_URL=https://xxxx.trycloudflare.com SWAR_API_KEY=... SWAR_VOICE_ID=maya \\
    SUPABASE_URL=https://<ref>.supabase.co SUPABASE_SERVICE_ROLE_KEY=... [SUPABASE_AUDIO_BUCKET=audio] \\
    python scripts/generate_swar_audio.py            # synth + upload + rewrite audio_url in the YAML

    python scripts/generate_swar_audio.py --local-only   # synth to scripts/audio_out/ only; touches nothing else
    python scripts/generate_swar_audio.py --limit 3      # try a few first

Then run `python scripts/build_lessons_json.py` to rebuild backend + mobile lessons.json.

Needs: pyyaml, httpx, and ffmpeg on PATH (WAV -> MP3 so the files stay small).
The spoken text is the exercise's Nepali answer (word-bank answers are joined with spaces), which is what the learner
is being taught to say. Files are named by a hash of voice+text, so re-running skips what already exists and a changed
voice/text gets a new URL (no stale CDN cache). Only the audio_url values are changed in the YAML; formatting is kept.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "content" / "units.final.yaml"
OUT = Path(__file__).resolve().parent / "audio_out"
BUCKET = os.environ.get("SUPABASE_AUDIO_BUCKET", "audio")  # public bucket the app plays from


def spoken_text(ex: dict) -> str:
    ans = ex.get("nepali_answer") or ex.get("nepali_answer_draft") or []
    return " ".join(ans).strip()


def to_mp3(wav: bytes) -> bytes:
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", "pipe:0", "-ac", "1", "-codec:a", "libmp3lame", "-q:a", "4", "-f", "mp3", "pipe:1"],
                       input=wav, capture_output=True)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError("ffmpeg failed: " + r.stderr.decode(errors="ignore")[-300:])
    return r.stdout


def ensure_bucket(http: httpx.Client, sb_url: str, sb_key: str) -> None:
    """Create the public audio bucket if it does not exist yet (public = anyone can play, only the service key can write)."""
    h = {"Authorization": f"Bearer {sb_key}", "apikey": sb_key}
    if http.get(f"{sb_url}/storage/v1/bucket/{BUCKET}", headers=h).status_code == 200:
        return
    r = http.post(f"{sb_url}/storage/v1/bucket", headers=h, json={"id": BUCKET, "name": BUCKET, "public": True})
    if r.status_code >= 300:
        sys.exit(f"Could not create bucket {BUCKET!r}: {r.status_code} {r.text[:200]}")
    print(f"created public bucket {BUCKET!r}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--local-only", action="store_true", help="save MP3s under scripts/audio_out/, no upload, YAML untouched")
    ap.add_argument("--limit", type=int, default=0, help="only the first N exercises")
    ap.add_argument("--quality", choices=["fast", "best"], default=os.environ.get("SWAR_QUALITY", "fast"))
    a = ap.parse_args()

    base = os.environ.get("SWAR_BASE_URL", "").rstrip("/")
    if not base:
        sys.exit("Set SWAR_BASE_URL (the trycloudflare URL printed by voice.ipynb) and SWAR_API_KEY.")
    swar_h = {"X-API-Key": os.environ["SWAR_API_KEY"]} if os.environ.get("SWAR_API_KEY") else {}
    sb_url, sb_key = os.environ.get("SUPABASE_URL", "").rstrip("/"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not a.local_only and not (sb_url and sb_key):
        sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to upload, or pass --local-only.")

    text = SRC.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    exercises = [e for u in data["units"] for l in u["lessons"] for e in l["exercises"]]
    if a.limit:
        exercises = exercises[: a.limit]

    with httpx.Client(timeout=900) as http:
        voice = os.environ.get("SWAR_VOICE_ID") or http.get(f"{base}/voices", headers=swar_h).raise_for_status().json()["presets"][0]
        print(f"voice={voice} quality={a.quality} exercises={len(exercises)}")
        OUT.mkdir(exist_ok=True)
        if not a.local_only:
            ensure_bucket(http, sb_url, sb_key)
        replace: dict[str, str] = {}
        for i, ex in enumerate(exercises, 1):
            t = spoken_text(ex)
            if not t:
                print(f"[{i}] skip: no Nepali answer"); continue
            name = hashlib.sha1(f"{voice}|{a.quality}|{t}".encode()).hexdigest()[:32] + ".mp3"
            path = OUT / name
            if not path.exists():
                r = http.post(f"{base}/tts", headers=swar_h, json={"voice_id": voice, "text": t, "quality": a.quality})
                if r.status_code != 200 or not r.content.startswith(b"RIFF"):
                    print(f"[{i}] FAILED {r.status_code} for {t!r}: {r.text[:150]}"); continue
                path.write_bytes(to_mp3(r.content))
            if not a.local_only:
                up = http.post(f"{sb_url}/storage/v1/object/{BUCKET}/{name}", content=path.read_bytes(),
                               headers={"Authorization": f"Bearer {sb_key}", "apikey": sb_key, "Content-Type": "audio/mpeg", "x-upsert": "true"})
                if up.status_code >= 300:
                    print(f"[{i}] UPLOAD FAILED {up.status_code}: {up.text[:150]}"); continue
                new = f"{sb_url}/storage/v1/object/public/{BUCKET}/{name}"
                if ex.get("audio_url"):
                    replace[ex["audio_url"]] = new
            print(f"[{i}/{len(exercises)}] {t}  ->  {name}")
            time.sleep(0.2)

    if a.local_only:
        print(f"\nMP3s are in {OUT}. YAML not changed.")
        return 0
    for old, new in replace.items():
        text = text.replace(old, new)
    SRC.write_text(text, encoding="utf-8")
    print(f"\nUpdated {len(replace)} audio_url values in {SRC.name}. Now run: python scripts/build_lessons_json.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
