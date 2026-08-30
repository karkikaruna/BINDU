from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
CONTENT_PATH = ROOT / "content" / "units.final.yaml"
DB_PATH = ROOT / "bindu_local.db"


def load_rows():
    """Flattens units.final.yaml into (units, lessons, exercises) row lists,
    assigning our own sequential ids so foreign keys line up."""
    with open(CONTENT_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    units, lessons, exercises = [], [], []
    unit_id = lesson_id = exercise_id = 0

    for unit in data["units"]:
        unit_id += 1
        units.append({
            "id": unit_id,
            "name": unit["name"],
            "order_index": unit["order_index"],
            "color_theme": unit.get("color_theme"),
        })
        for lesson in unit["lessons"]:
            lesson_id += 1
            lessons.append({
                "id": lesson_id,
                "unit_id": unit_id,
                "name": lesson["name"],
                "order_index": lesson["order_index"],
            })
            for exercise in lesson["exercises"]:
                exercise_id += 1
                options = exercise.get("nepali_options") or exercise.get("nepali_options_draft")
                tokens = exercise.get("nepali_tokens") or exercise.get("nepali_tokens_draft")
                answer = exercise.get("nepali_answer") or exercise.get("nepali_answer_draft")
                exercises.append({
                    "id": exercise_id,
                    "lesson_id": lesson_id,
                    "type": exercise["type"],
                    "prompt": exercise["english_prompt"],  # <- the fix
                    "options": options,
                    "tokens": tokens,
                    "answer": answer,
                    "audio_url": exercise.get("audio_url"),
                    "order_index": exercise["order_index"],
                })

    return units, lessons, exercises


def rebuild_local(units, lessons, exercises) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        create table if not exists units (
            id integer primary key, name text not null,
            order_index integer not null, color_theme text
        );
        create table if not exists lessons (
            id integer primary key, unit_id integer not null,
            name text not null, order_index integer not null
        );
        create table if not exists exercises (
            id integer primary key, lesson_id integer not null,
            type text not null, prompt text not null,
            options_json text, tokens_json text, answer_json text not null,
            audio_url text, order_index integer not null
        );
        """
    )
    cur = conn.cursor()
    cur.execute("delete from units")
    cur.execute("delete from lessons")
    cur.execute("delete from exercises")
    cur.executemany(
        "insert into units (id, name, order_index, color_theme) values (?, ?, ?, ?)",
        [(u["id"], u["name"], u["order_index"], u["color_theme"]) for u in units],
    )
    cur.executemany(
        "insert into lessons (id, unit_id, name, order_index) values (?, ?, ?, ?)",
        [(l["id"], l["unit_id"], l["name"], l["order_index"]) for l in lessons],
    )
    cur.executemany(
        """insert into exercises
           (id, lesson_id, type, prompt, options_json, tokens_json, answer_json, audio_url, order_index)
           values (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                e["id"], e["lesson_id"], e["type"], e["prompt"],
                json.dumps(e["options"]) if e["options"] is not None else None,
                json.dumps(e["tokens"]) if e["tokens"] is not None else None,
                json.dumps(e["answer"]),
                e["audio_url"], e["order_index"],
            )
            for e in exercises
        ],
    )
    conn.commit()
    conn.close()
    print(f"Local cache rebuilt: {len(units)} units, {len(lessons)} lessons, {len(exercises)} exercises.")


def rebuild_supabase(units, lessons, exercises) -> None:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("SUPABASE_SERVICE_ROLE_KEY not set — skipping Supabase update "
              "(local cache is already fixed).")
        return

    from supabase import create_client
    supabase = create_client(url, key)

    # Clear old (possibly Nepali-only-prompt) rows before re-inserting so we
    # don't end up with duplicates.
    supabase.table("exercises").delete().neq("id", 0).execute()
    supabase.table("lessons").delete().neq("id", 0).execute()
    supabase.table("units").delete().neq("id", 0).execute()

    unit_id_map, lesson_id_map = {}, {}

    for unit in units:
        row = supabase.table("units").insert({
            "name": unit["name"], "order_index": unit["order_index"],
            "color_theme": unit["color_theme"],
        }).execute().data[0]
        unit_id_map[unit["id"]] = row["id"]

    for lesson in lessons:
        row = supabase.table("lessons").insert({
            "unit_id": unit_id_map[lesson["unit_id"]],
            "name": lesson["name"], "order_index": lesson["order_index"],
        }).execute().data[0]
        lesson_id_map[lesson["id"]] = row["id"]

    for exercise in exercises:
        supabase.table("exercises").insert({
            "lesson_id": lesson_id_map[exercise["lesson_id"]],
            "type": exercise["type"],
            "prompt": exercise["prompt"],
            "options": exercise["options"],
            "tokens": exercise["tokens"],
            "answer": exercise["answer"],
            "audio_url": exercise["audio_url"],
            "order_index": exercise["order_index"],
        }).execute()

    print("Supabase re-seeded with corrected English prompts.")


def main():
    units, lessons, exercises = load_rows()
    rebuild_local(units, lessons, exercises)
    try:
        rebuild_supabase(units, lessons, exercises)
    except Exception as exc:
        print(f"Supabase update skipped/failed ({exc}); local cache is still fixed.")


if __name__ == "__main__":
    main()
