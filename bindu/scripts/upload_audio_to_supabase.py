"""Upload the pre-generated Nepali clips to the public Supabase Storage bucket, so they no longer have to live in the app / git.

    python scripts/upload_audio_to_supabase.py --dry-run          # show what would happen, no network writes
    python scripts/upload_audio_to_supabase.py                    # upload + verify every clip
    python scripts/upload_audio_to_supabase.py --delete-local     # upload + verify, THEN delete the local copies that are confirmed online

Reads SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY from the environment, falling back to backend/.env.
Optional: SUPABASE_AUDIO_BUCKET (default "audio"). The service-role key is only used here, on your computer; it never goes into the app.

Where files go
  local   mobile/assets/audio/ne/<hash>.mp3   (the old location)  and  scripts/audio_out/ne/<hash>.mp3  (where generate_nepali_audio.py now writes)
  remote  <bucket>/ne/<hash>.mp3              -> https://<ref>.supabase.co/storage/v1/object/public/<bucket>/ne/<hash>.mp3
The "ne/" folder keeps these apart from the older lesson clips that sit in the bucket root.
Clip names are content hashes, so they never change meaning: re-running is safe, and the files are cached for a year.

Safety: --delete-local only removes a local file after a HEAD request to its public URL answered 200 with the same byte size.
Anything that failed to upload or verify is kept, and the script exits non-zero.

Needs: httpx.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
SOURCES = [ROOT / "mobile" / "assets" / "audio" / "ne", ROOT / "scripts" / "audio_out" / "ne"]
MANIFEST = Path(__file__).resolve().parent / "audio_manifest.json"
PREFIX = "ne"
WORKERS = 8


def load_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip("'\"")
    return out


def ensure_public_bucket(http: httpx.Client, sb: str, bucket: str, auth: dict) -> None:
    r = http.get(f"{sb}/storage/v1/bucket/{bucket}", headers=auth)
    if r.status_code == 200:
        if not r.json().get("public"):
            u = http.put(f"{sb}/storage/v1/bucket/{bucket}", headers=auth, json={"public": True})
            if u.status_code >= 300:
                sys.exit(f"Bucket {bucket!r} is private and could not be made public: {u.status_code} {u.text[:200]}")
            print(f"made bucket {bucket!r} public")
        return
    c = http.post(f"{sb}/storage/v1/bucket", headers=auth, json={"id": bucket, "name": bucket, "public": True})
    if c.status_code >= 300:
        sys.exit(f"Could not create bucket {bucket!r}: {c.status_code} {c.text[:200]}")
    print(f"created public bucket {bucket!r}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="list what would be uploaded; change nothing")
    ap.add_argument("--delete-local", action="store_true", help="after upload, delete local clips that are verified online")
    ap.add_argument("--src", action="append", type=Path, help="folder of .mp3 clips (repeatable). Default: the two folders listed above")
    a = ap.parse_args()

    env = {**load_env_file(ROOT / "backend" / ".env"), **{k: v for k, v in os.environ.items() if k.startswith("SUPABASE_")}}
    sb = env.get("SUPABASE_URL", "").rstrip("/")
    key = env.get("SUPABASE_SERVICE_ROLE_KEY", "")
    bucket = env.get("SUPABASE_AUDIO_BUCKET", "audio")

    local: dict[str, Path] = {}
    for d in (a.src or SOURCES):
        if d.is_dir():
            for f in sorted(d.glob("*.mp3")):
                if f.stat().st_size > 0:
                    local.setdefault(f.name, f)
    wanted = {v["file"] for v in json.loads(MANIFEST.read_text(encoding="utf-8")).values()} if MANIFEST.exists() else set()

    print(f"{len(local)} local clips found; {len(wanted)} listed in audio_manifest.json")
    if a.dry_run:
        for n in sorted(local):
            print(f"  would upload  {bucket}/{PREFIX}/{n}  ({local[n].stat().st_size} bytes)")
        print(f"  {len(wanted - set(local))} manifest clips have no local file (they must already be online; they will be checked)" if wanted else "")
        return 0
    if not (sb and key):
        sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or put them in backend/.env).")

    auth = {"Authorization": f"Bearer {key}", "apikey": key}
    public = lambda n: f"{sb}/storage/v1/object/public/{bucket}/{PREFIX}/{n}"  # noqa: E731

    with httpx.Client(timeout=60) as http:
        ensure_public_bucket(http, sb, bucket, auth)

        def upload(name: str) -> tuple[str, str]:
            try:
                r = http.post(f"{sb}/storage/v1/object/{bucket}/{PREFIX}/{name}", content=local[name].read_bytes(),
                              headers={**auth, "Content-Type": "audio/mpeg", "x-upsert": "true", "cache-control": "max-age=31536000"})
                return name, "" if r.status_code < 300 else f"HTTP {r.status_code}: {r.text[:120]}"
            except httpx.HTTPError as e:
                return name, f"{type(e).__name__}: {e}"

        failed: dict[str, str] = {}
        with ThreadPoolExecutor(WORKERS) as pool:
            for i, (name, err) in enumerate(pool.map(upload, sorted(local)), 1):
                if err:
                    failed[name] = err
                    print(f"[{i}/{len(local)}] FAILED {name}: {err}")
                elif i % 25 == 0 or i == len(local):
                    print(f"[{i}/{len(local)}] uploaded")

        # Verify everything the app will ask for (all local clips + everything in the manifest) by asking the PUBLIC url, like the app does.
        def verify(name: str) -> tuple[str, bool, str]:
            try:
                r = http.head(public(name))
            except httpx.HTTPError as e:
                return name, False, f"{type(e).__name__}: {e}"
            if r.status_code != 200:
                return name, False, f"HTTP {r.status_code}" + (" (is the bucket public?)" if r.status_code in (400, 404) else "")
            want = local[name].stat().st_size if name in local else None
            got = int(r.headers.get("content-length", -1))
            if want is not None and got != want:
                return name, False, f"size mismatch (local {want}, online {got})"
            return name, True, ""

        names = sorted(set(local) | wanted)
        ok: set[str] = set()
        problems: list[str] = []
        with ThreadPoolExecutor(WORKERS) as pool:
            for name, good, why in pool.map(verify, names):
                if good:
                    ok.add(name)
                else:
                    problems.append(f"{name}: {why}")

    print(f"\nverified online: {len(ok)}/{len(names)}")
    for p in problems:
        print("  PROBLEM", p)

    if a.delete_local:
        removed = 0
        for name, path in local.items():
            if name in ok and name not in failed:
                path.unlink()
                removed += 1
        for d in (a.src or SOURCES):
            if d.is_dir() and not any(d.iterdir()):
                d.rmdir()
        print(f"deleted {removed} local clips (kept {len(local) - removed} that were not verified)")

    if failed or problems:
        print("\nSome clips are not online yet. Fix the problem above and run this script again; it is safe to repeat.")
        return 1
    print(f"\nAll clips are online at {public('<hash>.mp3')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
