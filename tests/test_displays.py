import pytest
from dataclasses import replace

from krillion_bot.services.displays import (
    DailyScoreboard,
    OverallScoreboard,
    Scoreboard,
    ScoreboardRow,
    UserStats,
)
from krillion_bot.services.database import KrillionResultRecord
from krillion_bot.services.parser import KrillionResult
from krillion_bot.utils import AnswerCategories, current_game_number


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


def make_record(
    score: int,
    answers: str,
    game_number: int = 46,
    author_name: str = "Player",
) -> KrillionResultRecord:
    result = make_result(score, answers, game_number)
    return KrillionResultRecord(
        1,
        123,
        456,
        author_name,
        result.game_number,
        result.score,
        result.krillions,
        result.deep_cuts,
        result.rares,
        result.schoolers,
        result.clevers,
        result.planktons,
        result.empties,
        "".join(answer.letter_code for answer in result.answers),
        "",
    )


def record_as_emoji(record: KrillionResultRecord) -> str:
    return "".join(
        AnswerCategories.from_char(char).value.as_emoji()
        for char in record.result_order
    )


def make_scoreboard_rows() -> list[ScoreboardRow]:
    return [
        ScoreboardRow(
            "The Owl Baron",
            make_record(155, "🐟🤡🐟🐟🫧🫧🐟", current_game_number()),
        ),
        ScoreboardRow(
            "The Raven Knight",
            make_record(200, "🫧⬛🐟🦑🐟🫧🦑", current_game_number()),
        ),
        ScoreboardRow(
            "Obscur",
            make_record(190, "⬛🫧⬛🦑🐟🐟🦑", current_game_number()),
        ),
        ScoreboardRow(
            "FireBjorne",
            make_record(230, "🐟🦑🐟🫧🦑🫧🐟", current_game_number()),
        ),
        ScoreboardRow(
            "The Bookkeeper of Domino",
            make_record(180, "🫧🦑🫧🐟🐟🫧🐟", current_game_number()),
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


def test_scoreboard_from_database_result_maps_author_names():
    records = [make_record(230, "🐟🦑🐟🫧🦑🫧🐟", author_name="FireBjorne")]

    scoreboard = Scoreboard.from_database_result(records)

    assert len(scoreboard.entries) == 1
    assert scoreboard.entries[0].user == "FireBjorne"
    assert scoreboard.entries[0].result is records[0]


def test_empty_scoreboard_has_no_winner_or_message():
    scoreboard = Scoreboard([])

    assert scoreboard.winner == ""
    assert scoreboard.as_message() == ""


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
        assert record_as_emoji(row.result) in message


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


def test_empty_daily_scoreboard_uses_current_game_and_no_results_message():
    scoreboard = DailyScoreboard([])

    assert scoreboard.game_number == current_game_number()
    assert "😢 **No results yet today!**" in scoreboard.as_message()


def test_daily_scoreboard_message_can_show_current_leader_before_final_results():
    scoreboard = DailyScoreboard(make_scoreboard_rows())

    message = scoreboard.as_message(final_result=False)

    assert "Leaderboard is not set in stone yet!" in message
    assert "Current Leader: FireBjorne!" in message
    assert "Scores close at" in message


def test_daily_scoreboard_rejects_results_from_different_games():
    rows = make_scoreboard_rows()

    rows.append(
        ScoreboardRow(
            "Different Game",
            make_record(
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


def test_overall_scoreboard_uses_krelo_instead_of_total_score():
    frequent_player = replace(
        make_record(800, "🌟🌟⬛🦑🏮⬛🐟", author_name="Frequent Player"),
        games_played=8,
        confidence_adjusted_average=145.0,
    )
    strong_player = replace(
        make_record(200, "🌟⬛⬛🦑🏮⬛🐟", author_name="Strong Player"),
        confidence_adjusted_average=180.0,
    )

    message = OverallScoreboard(
        [ScoreboardRow("Frequent Player", frequent_player), ScoreboardRow("Strong Player", strong_player)]
    ).as_message()

    assert "Overall KrELO Leader: Strong Player" in message
    assert "Strong Player - 180.0" in message
    assert "Frequent Player - 145.0" in message
    assert "Overall Points" not in message


def test_empty_overall_scoreboard_reports_no_results():
    message = OverallScoreboard([]).as_message()

    assert "😢 **No results ever logged!**" in message


def test_user_stats_from_database_result_builds_summary():
    aggregate = make_record(650, "🌟🌟⬛🦑🏮⬛🐟", author_name="FireBjorne")
    aggregate = replace(
        aggregate,
        games_played=2,
        confidence_adjusted_average=175.0,
    )
    best = make_record(375, "🌟🌟⬛🦑🏮⬛🐟", game_number=47, author_name="FireBjorne")
    latest = make_record(275, "🌟⬛⬛🦑🏮⬛🐟", game_number=48, author_name="FireBjorne")

    stats = UserStats.from_database_result(aggregate, best, latest)

    assert stats.user_name == "FireBjorne"
    assert stats.total_score == 650
    assert stats.krelo == 175.0
    assert stats.best_game.game_number == 47
    assert stats.latest_game.game_number == 48
    assert stats.EMOJI_MAPPING


def test_user_stats_rejects_results_for_different_users():
    aggregate = make_record(375, "🌟🌟⬛🦑🏮⬛🐟", author_name="FireBjorne")
    best = make_record(375, "🌟🌟⬛🦑🏮⬛🐟", author_name="Paradigm")
    latest = make_record(375, "🌟🌟⬛🦑🏮⬛🐟", author_name="FireBjorne")

    with pytest.raises(
        ValueError,
        match="Cannot build user stats from results for different users",
    ):
        UserStats.from_database_result(aggregate, best, latest)


def test_user_stats_message_contains_lifetime_and_category_totals():
    stats = UserStats(
        "FireBjorne",
        650,
        4,
        2,
        1,
        1,
        0,
        0,
        2,
        175.0,
        make_result(375, "🌟🌟⬛🦑🏮⬛🐟", game_number=47),
        make_result(275, "🌟⬛⬛🦑🏮⬛🐟", game_number=48),
    )

    message = stats.as_message()

    assert "**STATS FOR USER FireBjorne**" in message
    assert "**KrELO:** 175.0" in message
    assert "**Latest Game:** #48" in message
    assert "**Best Game:** #47" in message
    assert "**Lifetime Score:** 650" in message
    assert "🌟: 4" in message
    assert "⬛: 2" in message


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
    result = make_record(score, answers)
    row = ScoreboardRow("Player", result)

    assert row.user == "Player"
    assert row.result is result
    assert row.result.score == score
    assert record_as_emoji(row.result) == answers