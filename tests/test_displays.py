import pytest

from krillion_bot.services.displays import (
    DailyScoreboard,
    Scoreboard,
    ScoreboardRow,
)
from krillion_bot.services.parser import KrillionResult
from krillion_bot.utils import current_game_number


def make_result(
    score: int,
    answers: str,
    game_number: int = 46,
) -> KrillionResult:
    return KrillionResult.from_result_string(
        f"""
Krillion #{game_number} 🦐
{score}

{answers}
        """
    )


def make_scoreboard_rows() -> list[ScoreboardRow]:
    return [
        ScoreboardRow(
            "The Owl Baron",
            make_result(155, "🐟🤡🐟🐟🫧🫧🐟", current_game_number()),
        ),
        ScoreboardRow(
            "The Raven Knight",
            make_result(200, "🫧⬛🐟🦑🐟🫧🦑", current_game_number()),
        ),
        ScoreboardRow(
            "Obscur",
            make_result(190, "⬛🫧⬛🦑🐟🐟🦑", current_game_number()),
        ),
        ScoreboardRow(
            "FireBjorne",
            make_result(230, "🐟🦑🐟🫧🦑🫧🐟", current_game_number()),
        ),
        ScoreboardRow(
            "The Bookkeeper of Domino",
            make_result(180, "🫧🦑🫧🐟🐟🫧🐟", current_game_number()),
        ),
    ]


def test_scoreboard_sorts_entries_by_score_descending():
    scoreboard = Scoreboard(make_scoreboard_rows())

    assert [entry.user for entry in scoreboard.entries] == [
        "FireBjorne",
        "The Raven Knight",
        "Obscur",
        "The Bookkeeper of Domino",
        "The Owl Baron",
    ]


def test_scoreboard_winner_is_highest_scoring_player():
    scoreboard = Scoreboard(make_scoreboard_rows())

    assert scoreboard.winner == "FireBjorne"


def test_scoreboard_does_not_mutate_original_entries():
    rows = make_scoreboard_rows()
    original_order = [row.user for row in rows]

    Scoreboard(rows)

    assert [row.user for row in rows] == original_order


def test_scoreboard_as_message_contains_expected_rankings():
    scoreboard = Scoreboard(make_scoreboard_rows())

    message = scoreboard.as_message()

    assert "🥇 FireBjorne - 230" in message
    assert "🥈 The Raven Knight - 200" in message
    assert "🥉 Obscur - 190" in message
    assert "4. The Bookkeeper of Domino - 180" in message
    assert "5. The Owl Baron - 155" in message


def test_scoreboard_as_message_contains_each_result_as_emoji():
    scoreboard = Scoreboard(make_scoreboard_rows())

    message = scoreboard.as_message()

    for row in scoreboard.entries:
        assert row.result.as_emoji() in message


def test_scoreboard_as_message_respects_top_n():
    scoreboard = Scoreboard(make_scoreboard_rows())

    message = scoreboard.as_message(2)

    assert "🥇 FireBjorne - 230" in message
    assert "🥈 The Raven Knight - 200" in message

    assert "Obscur" not in message
    assert "The Bookkeeper of Domino" not in message
    assert "The Owl Baron" not in message


def test_scoreboard_as_message_with_no_top_n_includes_everyone():
    scoreboard = Scoreboard(make_scoreboard_rows())

    message = scoreboard.as_message()

    for row in scoreboard.entries:
        assert row.user in message


def test_daily_scoreboard_sets_game_number():
    scoreboard = DailyScoreboard(make_scoreboard_rows())

    assert scoreboard.game_number == current_game_number()


def test_daily_scoreboard_winner_is_highest_scoring_player():
    scoreboard = DailyScoreboard(make_scoreboard_rows())

    assert scoreboard.winner == "FireBjorne"


def test_daily_scoreboard_rejects_results_from_different_games():
    rows = make_scoreboard_rows()

    rows.append(
        ScoreboardRow(
            "Different Game",
            make_result(
                250,
                "🌟🌟⬛🦑🏮⬛🐟",
                game_number=32,
            ),
        )
    )

    with pytest.raises(
        ValueError,
        match="Cannot create daily scoreboard for entries from different games",
    ):
        DailyScoreboard(rows)


def test_daily_scoreboard_message_contains_header():
    scoreboard = DailyScoreboard(make_scoreboard_rows())

    message = scoreboard.as_message()

    assert f"🏆 **SCOREBOARD FOR GAME #{current_game_number()}** 🏆" in message


def test_daily_scoreboard_message_contains_winner():
    scoreboard = DailyScoreboard(make_scoreboard_rows())

    message = scoreboard.as_message()

    assert "🎉 **Today's Winner: FireBjorne!** 🎉" in message
    assert "🏆 **Score:** 230" in message


def test_daily_scoreboard_message_contains_scoreboard():
    scoreboard = DailyScoreboard(make_scoreboard_rows())

    message = scoreboard.as_message()

    assert "🥇 FireBjorne - 230" in message
    assert "🥈 The Raven Knight - 200" in message
    assert "🥉 Obscur - 190" in message
    assert "4. The Bookkeeper of Domino - 180" in message
    assert "5. The Owl Baron - 155" in message


def test_daily_scoreboard_message_respects_top_n():
    scoreboard = DailyScoreboard(make_scoreboard_rows())

    message = scoreboard.as_message(2)

    assert "🥇 FireBjorne - 230" in message
    assert "🥈 The Raven Knight - 200" in message
    assert "Obscur" not in message
    assert "The Bookkeeper of Domino" not in message
    assert "The Owl Baron" not in message

@pytest.mark.parametrize(
    ("score", "answers"),
    [
        (155, "🐟🤡🐟🐟🫧🫧🐟"),
        (200, "🫧⬛🐟🦑🐟🫧🦑"),
        (190, "⬛🫧⬛🦑🐟🐟🦑"),
        (230, "🐟🦑🐟🫧🦑🫧🐟"),
        (180, "🫧🦑🫧🐟🐟🫧🐟"),
    ],
)
def test_scoreboard_row_preserves_result(score, answers):
    result = make_result(score, answers)
    row = ScoreboardRow("Player", result)

    assert row.user == "Player"
    assert row.result is result
    assert row.result.score == score
    assert row.result.as_emoji() == answers