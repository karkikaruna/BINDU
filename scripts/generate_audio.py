
import os, uuid
from io import BytesIO
from pathlib import Path
import yaml
from dotenv import load_dotenv
from gtts import gTTS
from supabase import create_client

load_dotenv()
LANG = "ne"
BUCKET_NAME = "audio"
CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
INPUT_PATH = CONTENT_DIR / "units.reviewed.yaml"
OUTPUT_PATH = CONTENT_DIR / "units.final.yaml"
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

def synthesize(text):
    buf = BytesIO()
    gTTS(text=text, lang=LANG).write_to_fp(buf)
    buf.seek(0)
    return buf.read()

def upload_audio(supabase, audio_bytes):
    filename = f"{uuid.uuid4().hex}.mp3"
    supabase.storage.from_(BUCKET_NAME).upload(filename, audio_bytes, {"content-type": "audio/mpeg"})
    return supabase.storage.from_(BUCKET_NAME).get_public_url(filename)

def main():
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    for unit in data["units"]:
        for lesson in unit["lessons"]:
            for exercise in lesson["exercises"]:
                text = exercise.get("nepali_prompt") or exercise.get("nepali_prompt_draft")
                if not text:
                    continue
                url = upload_audio(supabase, synthesize(text))
                exercise["audio_url"] = url
                print(f"Uploaded audio for: {text} -> {url}")
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    print(f"\nDone. {OUTPUT_PATH} is ready for content/seed_supabase.py")

if __name__ == "__main__":
    main()

