import pytest
from typing import Callable
from krillion_bot.utils import AnswerCategories, Emojis, KrillionCategory


@pytest.mark.parametrize(
    ("member", "value"),
    [
        (Emojis.K, "🌟"),
        (Emojis.D, "🏮"),
        (Emojis.R, "🦑"),
        (Emojis.S, "🐟"),
        (Emojis.C, "🤡"),
        (Emojis.P, "🫧"),
        (Emojis.E, "⬛"),
    ],
)
def test_emoji_members_have_expected_values(member: Emojis, value: str):
    assert member.value == value
    assert str(member) == value


@pytest.mark.parametrize("emoji", list(Emojis))
def test_emoji_unicode_conversion_round_trips(emoji: Emojis):
    assert Emojis.from_unicode(emoji.to_unicode()) is emoji


@pytest.mark.parametrize(
    ("member", "letter_code", "label", "score"),
    [
        (AnswerCategories.K, "O", "One in a Krillion", 100),
        (AnswerCategories.D, "D", "Deep Cut", 85),
        (AnswerCategories.R, "R", "Rare", 60),
        (AnswerCategories.S, "S", "Schooler", 30),
        (AnswerCategories.C, "T", "Too Clever", 15),
        (AnswerCategories.P, "P", "Plankton", 10),
        (AnswerCategories.E, "N", "No Response", 0),
    ],
)
def test_answer_categories_contain_expected_metadata(
    member: Emojis,
    letter_code: str,
    label: str,
    score: int,
):
    category = member.value

    assert isinstance(category, KrillionCategory)
    assert category.letter_code == letter_code
    assert category.category == label
    assert category.score == score
    assert category.as_emoji() is category.emoji
    assert category.unicode == category.emoji.to_unicode()
    assert repr(category) == f"KrillionCategory({label})"


@pytest.mark.parametrize("category", list(AnswerCategories))
def test_answer_category_lookups_round_trip(category: AnswerCategories):
    value = category.value

    assert AnswerCategories.from_unicode(value.unicode) is category
    assert AnswerCategories.from_char(value.letter_code) is category
    assert AnswerCategories.from_emoji(value.emoji) is category


@pytest.mark.parametrize(
    ("lookup", "value"),
    [
        (Emojis.from_unicode, r"\U0001f600"),
        (AnswerCategories.from_unicode, r"\U0001f600"),
        (AnswerCategories.from_char, "X"),
        (AnswerCategories.from_emoji, "😀"),
    ],
)
def test_unknown_utility_values_are_rejected(lookup: Callable, value: str):
    with pytest.raises(StopIteration):
        lookup(value)


def test_answer_category_from_char_rejects_non_string_values():
    with pytest.raises(
        ValueError,
        match="from_char must take a string of length 1 only",
    ):
        AnswerCategories.from_char(["O"]) # type: ignore (We want to pass a bad type here, do not flag as problematic)
    with pytest.raises(
            ValueError,
            match="from_char must take a string of length 1 only",
        ):
            AnswerCategories.from_char("OOSDSSS")