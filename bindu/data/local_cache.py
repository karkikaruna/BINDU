
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "bindu_local.db"

_SCHEMA = """
create table if not exists units (
    id integer primary key,
    name text not null,
    order_index integer not null,
    color_theme text
);

create table if not exists lessons (
    id integer primary key,
    unit_id integer not null,
    name text not null,
    order_index integer not null
);

create table if not exists exercises (
    id integer primary key,
    lesson_id integer not null,
    type text not null,
    prompt text not null,
    options_json text,
    tokens_json text,
    answer_json text not null,
    audio_url text,
    order_index integer not null
);

create table if not exists user_progress (
    user_id text not null,
    lesson_id integer not null,
    completed integer not null default 0,
    stars integer not null default 0,
    pending_sync integer not null default 0,
    primary key (user_id, lesson_id)
);

create table if not exists user_stats (
    user_id text primary key,
    hearts integer not null,
    xp integer not null,
    streak integer not null,
    last_active text,
    hearts_last_refill text not null,
    pending_sync integer not null default 0
);

create table if not exists users (
    username text primary key,
    password_hash text not null,
    salt text not null,
    display_name text,
    created_at text not null
);
"""


class LocalCache:
    """Thin wrapper around a SQLite connection. One instance per process is fine
    for a Streamlit app (each session reuses it via st.cache_resource)."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # -- curriculum ---------------------------------------------------------

    def replace_units(self, units: list[dict]) -> None:
        cur = self._conn.cursor()
        cur.execute("delete from units")
        cur.executemany(
            "insert into units (id, name, order_index, color_theme) values (?, ?, ?, ?)",
            [(u["id"], u["name"], u["order_index"], u.get("color_theme")) for u in units],
        )
        self._conn.commit()

    def replace_lessons(self, lessons: list[dict]) -> None:
        cur = self._conn.cursor()
        cur.execute("delete from lessons")
        cur.executemany(
            "insert into lessons (id, unit_id, name, order_index) values (?, ?, ?, ?)",
            [(l["id"], l["unit_id"], l["name"], l["order_index"]) for l in lessons],
        )
        self._conn.commit()

    def replace_exercises(self, exercises: list[dict]) -> None:
        cur = self._conn.cursor()
        cur.execute("delete from exercises")
        cur.executemany(
            """insert into exercises
               (id, lesson_id, type, prompt, options_json, tokens_json, answer_json, audio_url, order_index)
               values (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    e["id"], e["lesson_id"], e["type"], e["prompt"],
                    json.dumps(e.get("options")) if e.get("options") is not None else None,
                    json.dumps(e.get("tokens")) if e.get("tokens") is not None else None,
                    json.dumps(e["answer"]),
                    e.get("audio_url"), e["order_index"],
                )
                for e in exercises
            ],
        )
        self._conn.commit()

    def get_units(self) -> list[sqlite3.Row]:
        return self._conn.execute("select * from units order by order_index").fetchall()

    def get_lessons(self) -> list[sqlite3.Row]:
        return self._conn.execute("select * from lessons order by order_index").fetchall()

    def get_exercises_for_lesson(self, lesson_id: int) -> list[sqlite3.Row]:
        return self._conn.execute(
            "select * from exercises where lesson_id = ? order by order_index", (lesson_id,)
        ).fetchall()

    

    def get_stats(self, user_id: str) -> sqlite3.Row | None:
        return self._conn.execute(
            "select * from user_stats where user_id = ?", (user_id,)
        ).fetchone()

    def upsert_stats(
        self, user_id: str, hearts: int, xp: int, streak: int,
        last_active: str | None, hearts_last_refill: str, pending_sync: bool = False,
    ) -> None:
        self._conn.execute(
            """insert into user_stats (user_id, hearts, xp, streak, last_active, hearts_last_refill, pending_sync)
               values (?, ?, ?, ?, ?, ?, ?)
               on conflict(user_id) do update set
                 hearts=excluded.hearts, xp=excluded.xp, streak=excluded.streak,
                 last_active=excluded.last_active, hearts_last_refill=excluded.hearts_last_refill,
                 pending_sync=excluded.pending_sync""",
            (user_id, hearts, xp, streak, last_active, hearts_last_refill, int(pending_sync)),
        )
        self._conn.commit()

    def get_pending_stats(self) -> list[sqlite3.Row]:
        return self._conn.execute("select * from user_stats where pending_sync = 1").fetchall()

    def upsert_progress(
        self, user_id: str, lesson_id: int, completed: bool, stars: int, pending_sync: bool = False,
    ) -> None:
        self._conn.execute(
            """insert into user_progress (user_id, lesson_id, completed, stars, pending_sync)
               values (?, ?, ?, ?, ?)
               on conflict(user_id, lesson_id) do update set
                 completed=excluded.completed, stars=excluded.stars, pending_sync=excluded.pending_sync""",
            (user_id, lesson_id, int(completed), stars, int(pending_sync)),
        )
        self._conn.commit()

    def get_progress_for_user(self, user_id: str) -> list[sqlite3.Row]:
        return self._conn.execute(
            "select * from user_progress where user_id = ?", (user_id,)
        ).fetchall()

    def get_pending_progress(self) -> list[sqlite3.Row]:
        return self._conn.execute("select * from user_progress where pending_sync = 1").fetchall()

  

    def create_user(
        self, username: str, password_hash: str, salt: str,
        display_name: str, created_at: str,
    ) -> None:
        self._conn.execute(
            """insert into users (username, password_hash, salt, display_name, created_at)
               values (?, ?, ?, ?, ?)""",
            (username, password_hash, salt, display_name, created_at),
        )
        self._conn.commit()

    def get_user(self, username: str) -> sqlite3.Row | None:
        return self._conn.execute(
            "select * from users where username = ?", (username,)
        ).fetchone()
