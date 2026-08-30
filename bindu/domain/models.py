
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ExerciseType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    WORD_BANK = "word_bank"


@dataclass(frozen=True)
class Exercise:
    id: int
    lesson_id: int
    type: ExerciseType
    prompt: str
    answer: list[str]                       # correct option text OR correct token order
    options: list[str] = field(default_factory=list)   # multiple_choice
    tokens: list[str] = field(default_factory=list)    # word_bank shuffled tiles
    audio_url: str | None = None
    order_index: int = 0


@dataclass
class Lesson:
    id: int
    unit_id: int
    name: str
    order_index: int
    completed: bool = False
    stars: int = 0
    locked: bool = True


@dataclass
class LessonUnit:
    id: int
    name: str
    order_index: int
    color_theme: str | None = None
    lessons: list[Lesson] = field(default_factory=list)


@dataclass
class UserStats:
    user_id: str
    hearts: int
    xp: int
    streak: int
    last_active: str | None        
    hearts_last_refill: str      
