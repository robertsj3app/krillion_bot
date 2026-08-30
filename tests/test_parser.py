import pytest

from krillion_bot.services.parser import KrillionCategory, KrillionResult


def make_result(score: int, answers: str, game_number: int = 46) -> KrillionResult:
    return KrillionResult.from_result_string(
        f"""
Krillion #{game_number} 🦐
{score}

{answers}
        """
    )


def test_parse_game_number():
    result = make_result(
        375,
        "🌟🌟⬛🦑🏮⬛🐟",
    )

    assert result.game_number == 46


@pytest.mark.parametrize(
    ("score", "answers"),
    [
        (375, "🌟🌟⬛🦑🏮⬛🐟"),
        (275, "🌟⬛⬛🦑🏮⬛🐟"),
        (155, "🐟🤡🐟🐟🫧🫧🐟"),
        (200, "🫧⬛🐟🦑🐟🫧🦑"),
        (190, "⬛🫧⬛🦑🐟🐟🦑"),
        (230, "🐟🦑🐟🫧🦑🫧🐟"),
        (180, "🫧🦑🫧🐟🐟🫧🐟"),
    ],
)
def test_parse_score(score, answers):
    result = make_result(score, answers)

    assert result.score == score


def test_parse_answers():
    result = make_result(
        375,
        "🌟🌟⬛🦑🏮⬛🐟",
    )

    assert result.as_emoji() == "🌟🌟⬛🦑🏮⬛🐟"


def test_result_is_valid_when_score_matches_answers():
    result = make_result(
        375,
        "🌟🌟⬛🦑🏮⬛🐟",
    )

    assert result.valid is True


def test_result_is_invalid_when_score_does_not_match_answers():
    result = KrillionResult(
        game_number=46,
        score=1,
        answers=[
            KrillionResult.CATEGORY_LOOKUP_UNICODE[r"\U0001f31f"],
            KrillionResult.CATEGORY_LOOKUP_UNICODE[r"\U0001f31f"],
            KrillionResult.CATEGORY_LOOKUP_UNICODE[r"\u2b1b"],
            KrillionResult.CATEGORY_LOOKUP_UNICODE[r"\U0001f991"],
            KrillionResult.CATEGORY_LOOKUP_UNICODE[r"\U0001f3ee"],
            KrillionResult.CATEGORY_LOOKUP_UNICODE[r"\u2b1b"],
            KrillionResult.CATEGORY_LOOKUP_UNICODE[r"\U0001f41f"],
        ],
    )

    assert result.valid is False


def test_category_counts_are_calculated():
    result = make_result(
        375,
        "🌟🌟⬛🦑🏮⬛🐟",
    )

    assert result.krillions == 2
    assert result.deep_cuts == 1
    assert result.rares == 1
    assert result.schoolers == 1
    assert result.clevers == 0
    assert result.planktons == 0
    assert result.empties == 2


def test_category_counts_for_all_categories():
    result = make_result(
        300,
        "🌟🦑🏮🐟🤡🫧⬛",
    )

    assert result.krillions == 1
    assert result.deep_cuts == 1
    assert result.rares == 1
    assert result.schoolers == 1
    assert result.clevers == 1
    assert result.planktons == 1
    assert result.empties == 1


@pytest.mark.parametrize(
    ("unicode", "expected_category", "expected_score"),
    [
        (r"\U0001f31f", "One in a Krillion", 100),
        (r"\U0001f991", "Deep Cut", 85),
        (r"\U0001f3ee", "Rare", 60),
        (r"\U0001f41f", "Schooler", 30),
        (r"\U0001f921", "Too Clever", 15),
        (r"\U0001fae7", "Plankton", 10),
        (r"\u2b1b", "No Response", 0),
    ],
)
def test_category_lookup(unicode, expected_category, expected_score):
    category = KrillionResult.CATEGORY_LOOKUP_UNICODE[unicode]

    assert isinstance(category, KrillionCategory)
    assert category.category == expected_category
    assert category.score == expected_score


def test_as_emoji_round_trips_original_answers():
    answers = "🌟🌟⬛🦑🏮⬛🐟"

    result = make_result(375, answers)

    assert result.as_emoji() == answers


def test_parse_invalid_result_raises_value_error():
    with pytest.raises(ValueError, match="invalid string"):
        KrillionResult.from_result_string(
            """
            This is not a Krillion result.
            """
        )


def test_parse_result_with_unknown_category_raises_value_error():
    # The parser's format accepts escaped Unicode strings, but the
    # lookup should reject values that aren't known Krillion categories.
    with pytest.raises(ValueError, match="KrillionResult from invalid string"):
        KrillionResult.from_result_string(
            r"""
            Krillion #46 🦐
            375

            \U0001f31f\U0001f31f\U0001f600\U0001f991\U0001f3ee\u2b1b\U0001f41f
            """
        )


def test_from_database_row_reconstructs_result():
    result = make_result(
        375,
        "🌟🌟⬛🦑🏮⬛🐟",
    )

    # The database row layout is:
    # id, guild_id, author_id, author_name, game_number, score,
    # krillions, deep_cuts, rares, schoolers, clevers, planktons,
    # blanks, result_order, created_at
    row = (
        1,
        123,
        4652,
        "FireBjorne",
        result.game_number,
        result.score,
        result.krillions,
        result.deep_cuts,
        result.rares,
        result.schoolers,
        result.clevers,
        result.planktons,
        result.empties,
        "OONDRNS",
        "2026-08-30 12:00:00",
    )

    reconstructed = KrillionResult.from_database_row(row)

    assert reconstructed.game_number == result.game_number
    assert reconstructed.score == result.score
    assert reconstructed.as_emoji() == result.as_emoji()
    assert reconstructed.krillions == result.krillions
    assert reconstructed.deep_cuts == result.deep_cuts
    assert reconstructed.rares == result.rares
    assert reconstructed.schoolers == result.schoolers
    assert reconstructed.clevers == result.clevers
    assert reconstructed.planktons == result.planktons
    assert reconstructed.empties == result.empties


@pytest.mark.parametrize(
    ("answers", "score"),
    [
        ("🌟🌟⬛🦑🏮⬛🐟", 375),
        ("🌟⬛⬛🦑🏮⬛🐟", 275),
        ("🫧⬛🐟🦑🐟🫧🦑", 250),
        ("⬛🫧⬛🦑🐟🐟🦑", 240),
        ("🐟🦑🐟🫧🦑🫧🐟", 280),
    ],
)
def test_valid_results_from_example_results(answers, score):
    result = make_result(score, answers)

    assert result.valid is True
    assert sum(category.score for category in result.answers) == score