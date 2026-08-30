
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

CONTENT_PATH = Path(__file__).resolve().parent / "units.final.yaml"


def wipe_existing(supabase) -> None:
    """Deletes every row from the curriculum tables before reseeding.

    Previously this script only ever inserted, so every rerun (e.g. after
    fixing a bad translation) left the old, wrong rows in place alongside
    the new ones — the app would keep showing whichever copy it happened
    to read first. Deleting child tables before parents avoids foreign-key
    errors (exercises -> lessons -> units).

    Note: this does not touch user_progress. If any users have already
    completed lessons against the old lesson ids, those progress rows will
    point at ids that no longer exist after this wipe. Fine for
    pre-launch/content-authoring use; worth revisiting before real users
    have progress to preserve.
    """
    supabase.table("exercises").delete().neq("id", 0).execute()
    supabase.table("lessons").delete().neq("id", 0).execute()
    supabase.table("units").delete().neq("id", 0).execute()
    print("Cleared existing units/lessons/exercises.\n")


def main():
    with open(CONTENT_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    wipe_existing(supabase)

    for unit in data["units"]:
        unit_row = supabase.table("units").insert({
            "name": unit["name"],
            "order_index": unit["order_index"],
            "color_theme": unit.get("color_theme"),
        }).execute().data[0]
        unit_id = unit_row["id"]
        print(f"Inserted unit: {unit['name']} (id={unit_id})")

        for lesson in unit["lessons"]:
            lesson_row = supabase.table("lessons").insert({
                "unit_id": unit_id,
                "name": lesson["name"],
                "order_index": lesson["order_index"],
            }).execute().data[0]
            lesson_id = lesson_row["id"]
            print(f"  Inserted lesson: {lesson['name']} (id={lesson_id})")

            for exercise in lesson["exercises"]:
                options = exercise.get("nepali_options") or exercise.get("nepali_options_draft")
                tokens = exercise.get("nepali_tokens") or exercise.get("nepali_tokens_draft")
                answer = exercise.get("nepali_answer") or exercise.get("nepali_answer_draft")
                # The prompt shown to the learner is the English question
                # ("How do you say 'Hello' in Nepali?") — the Nepali fields
                # above are the answer choices, not the prompt. Using the
                # (non-existent) "prompt" key here previously fell through
                # to Nepali-only content because the KeyError was masked.
                prompt = exercise["english_prompt"]

                supabase.table("exercises").insert({
                    "lesson_id": lesson_id,
                    "type": exercise["type"],
                    "prompt": prompt,
                    "options": options,
                    "tokens": tokens,
                    "answer": answer,
                    "audio_url": exercise.get("audio_url"),
                    "order_index": exercise["order_index"],
                }).execute()
                print(f"    Inserted exercise #{exercise['order_index']}")

    print("\nSeeding complete.")


if __name__ == "__main__":
    main()
