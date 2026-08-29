import pytest

from bindu.domain import exercise_validator as ev


def test_multiple_choice_correct_answer_is_case_insensitive():
    assert ev.check_multiple_choice("Namaste", ["namaste"]) is True


def test_multiple_choice_wrong_answer_fails():
    assert ev.check_multiple_choice("Dhanyabad", ["Namaste"]) is False


def test_word_bank_correct_order_passes():
    answer = ["timro", "naam", "ke", "ho"]
    assert ev.check_word_bank(["timro", "naam", "ke", "ho"], answer) is True


def test_word_bank_wrong_order_fails():
    answer = ["timro", "naam", "ke", "ho"]
    assert ev.check_word_bank(["naam", "timro", "ke", "ho"], answer) is False


def test_word_bank_mismatched_length_fails():
    answer = ["timro", "naam", "ke", "ho"]
    assert ev.check_word_bank(["timro", "naam"], answer) is False


def test_fuzzy_check_passes_above_threshold():
    a = [1.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    assert ev.fuzzy_check(a, b, threshold=0.9) is True


def test_fuzzy_check_fails_below_threshold():
    a = [1.0, 0.0, 0.0]
    b = [0.0, 1.0, 0.0]
    assert ev.fuzzy_check(a, b, threshold=0.5) is False


def test_fuzzy_check_raises_on_dimension_mismatch():
    with pytest.raises(ValueError):
        ev.fuzzy_check([1.0, 0.0], [1.0, 0.0, 0.0])
