
from __future__ import annotations

import math


def check_multiple_choice(selected: str, answer: list[str]) -> bool:
    """Multiple choice: user selected one option string; compare against the
    single correct answer (case-insensitive, whitespace-trimmed)."""
    if not answer:
        return False
    correct = answer[0]
    return selected.strip().lower() == correct.strip().lower()


def check_word_bank(ordered_tokens: list[str], answer: list[str]) -> bool:
    """Word bank: user has arranged tokens in some order; compare the full
    ordered sequence (case-insensitive, whitespace-trimmed per token)."""
    if len(ordered_tokens) != len(answer):
        return False
    return all(
        a.strip().lower() == b.strip().lower()
        for a, b in zip(ordered_tokens, answer)
    )


def fuzzy_check(
    user_vector: list[float],
    reference_vector: list[float],
    threshold: float = 0.82,
) -> bool:
    """v2 fuzzy free-text scoring.

    Reference embeddings are precomputed offline (via the
    sentence-transformers pipeline in scripts/); here we just do a
    lightweight cosine-similarity comparison against a precomputed reference
    vector, given a threshold.
    """
    if len(user_vector) != len(reference_vector):
        raise ValueError("Vector dimension mismatch")

    dot = sum(a * b for a, b in zip(user_vector, reference_vector))
    norm_a = math.sqrt(sum(a * a for a in user_vector))
    norm_b = math.sqrt(sum(b * b for b in reference_vector))
    if norm_a == 0 or norm_b == 0:
        return False

    cosine_similarity = dot / (norm_a * norm_b)
    return cosine_similarity >= threshold
