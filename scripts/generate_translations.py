import json
import time
from pathlib import Path

import yaml
from deep_translator import GoogleTranslator

SRC_LANG = "en"  
TGT_LANG = "ne" 

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
INPUT_PATH = CONTENT_DIR / "units.yaml"
OUTPUT_PATH = CONTENT_DIR / "units.translated.yaml"
CACHE_PATH = CONTENT_DIR / ".translation_cache.json"

translator = GoogleTranslator(source=SRC_LANG, target=TGT_LANG)

_cache: dict[str, str] = {}
if CACHE_PATH.exists():
    try:
        _cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        print(f"Loaded {len(_cache)} cached translations from {CACHE_PATH.name}")
    except (json.JSONDecodeError, OSError):
        _cache = {}


def _save_cache():
    CACHE_PATH.write_text(json.dumps(_cache, ensure_ascii=False, indent=2), encoding="utf-8")


def collect_all_strings(data) -> list[str]:
    """Walk the whole yaml tree once and gather every unique string to translate."""
    seen = []
    seen_set = set()
    for unit in data["units"]:
        for lesson in unit["lessons"]:
            for exercise in lesson["exercises"]:
                candidates = []
                if "english_prompt" in exercise:
                    candidates.append(exercise["english_prompt"])
                candidates += exercise.get("english_options", [])
                candidates += exercise.get("english_tokens", [])
                candidates += exercise.get("english_answer", [])
                for text in candidates:
                    if text and text != "___" and text not in seen_set and text not in _cache:
                        seen_set.add(text)
                        seen.append(text)
    return seen


MAX_RETRIES = 4        
RETRY_BACKOFF = 2.0      
REQUEST_DELAY = 0.4      

_failed: list[str] = []


def _translate_with_retries(text: str) -> tuple[str, bool]:

    delay = RETRY_BACKOFF
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            translated = translator.translate(text)
            if translated:
                return translated, True
            last_exc = ValueError("empty translation returned")
        except Exception as exc:
            last_exc = exc
        if attempt < MAX_RETRIES:
            print(f"    retry {attempt}/{MAX_RETRIES - 1} after error: {last_exc}")
            time.sleep(delay)
            delay *= 2
    print(f"  ! giving up after {MAX_RETRIES} attempts ({last_exc}); falling back to source text")
    return text, False


def translate_missing(strings: list[str]):
    """Translate everything not already cached, one string at a time, saving as it goes."""
    total = len(strings)
    for i, text in enumerate(strings, start=1):
        print(f"Translating {i}/{total}: {text!r}")
        translated, ok = _translate_with_retries(text)
        if ok:
            _cache[text] = translated
            _save_cache()
        else:

            _failed.append(text)
        time.sleep(REQUEST_DELAY)


def translate(text: str) -> str:
    if not text or text == "___":
        return text
    return _cache.get(text, text)


def translate_list(items):
    return [translate(item) for item in items]


def main():
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    to_translate = collect_all_strings(data)
    print(f"{len(to_translate)} new strings to translate ({len(_cache)} already cached).\n")
    translate_missing(to_translate)

    for unit in data["units"]:
        for lesson in unit["lessons"]:
            for exercise in lesson["exercises"]:
                if "english_prompt" in exercise:
                    exercise["nepali_prompt_draft"] = translate(exercise["english_prompt"])
                if "english_options" in exercise:
                    exercise["nepali_options_draft"] = translate_list(exercise["english_options"])
                if "english_tokens" in exercise:
                    exercise["nepali_tokens_draft"] = translate_list(exercise["english_tokens"])
                if "english_answer" in exercise:
                    exercise["nepali_answer_draft"] = translate_list(exercise["english_answer"])

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

    print(f"\nDone. Review every *_draft field in {OUTPUT_PATH} before seeding.")
    print(f"({len(_cache)} strings cached in {CACHE_PATH.name} -- rerunning reuses them instantly.)")

    if _failed:
        print(
            f"\n{len(_failed)} string(s) could not be translated after {MAX_RETRIES} attempts "
            f"each and were left in English in the output (not cached, so rerunning will "
            f"retry them):"
        )
        for text in _failed:
            print(f"  - {text!r}")


if __name__ == "__main__":
    main()
