import pytest

from krillion_bot.services.database import DatabaseHandler
from krillion_bot.services.parser import KrillionResult
from krillion_bot.utils import current_game_number
import aiosqlite


@pytest.fixture
def db(tmp_path):
    """Create an isolated database for each test."""
    db_path = tmp_path / "test.db"

    DatabaseHandler.initial_setup(str(db_path))

    return DatabaseHandler(123)


def make_result(score: int, answers: str, game_number: int = 46) -> KrillionResult:
    return KrillionResult.from_result_string(
        f"""
Krillion #{game_number} 🦐
{score}

{answers}
        """
    )


@pytest.mark.asyncio
async def test_user_has_not_submitted_today(db: DatabaseHandler):
    assert await db.check_user_submitted_today(4652) is False


@pytest.mark.asyncio
async def test_logging_result_marks_user_as_submitted_today(db: DatabaseHandler):
    result = make_result(
        375,
        "🌟🌟⬛🦑🏮⬛🐟",
        current_game_number()
    )

    await db.log_result(4652, "FireBjorne", result)

    assert await db.check_user_submitted_today(4652) is True


@pytest.mark.asyncio
async def test_logging_result_for_one_user_does_not_affect_another_user(db: DatabaseHandler):
    result = make_result(
        375,
        "🌟🌟⬛🦑🏮⬛🐟",
        current_game_number()
    )

    await db.log_result(4652, "FireBjorne", result)

    assert await db.check_user_submitted_today(4652) is True
    assert await db.check_user_submitted_today(4651) is False


@pytest.mark.asyncio
async def test_user_cannot_submit_twice_on_the_same_day(db: DatabaseHandler):
    first_result = make_result(
        375,
        "🌟🌟⬛🦑🏮⬛🐟",
        current_game_number()
    )

    second_result = make_result(
        275,
        "🌟⬛⬛🦑🏮⬛🐟",
        current_game_number()
    )

    await db.log_result(4652, "FireBjorne", first_result)

    with pytest.raises(
        Exception,
        match="Cannot submit a second Krillion result for user FireBjorne",
    ):
        await db.log_result(4652, "FireBjorne", second_result)


@pytest.mark.asyncio
async def test_different_users_can_submit_results(db: DatabaseHandler):
    firebjorne = make_result(
        375,
        "🌟🌟⬛🦑🏮⬛🐟",
        current_game_number()
    )
    paradigm = make_result(
        275,
        "🌟⬛⬛🦑🏮⬛🐟",
        current_game_number()
    )

    await db.log_result(4652, "FireBjorne", firebjorne)
    await db.log_result(4651, "Paradigm", paradigm)

    assert await db.check_user_submitted_today(4652) is True
    assert await db.check_user_submitted_today(4651) is True


@pytest.mark.asyncio
async def test_scoreboard_returns_results_ordered_by_score(db: DatabaseHandler):
    firebjorne = make_result(
        375,
        "🌟🌟⬛🦑🏮⬛🐟",
    )
    paradigm = make_result(
        275,
        "🌟⬛⬛🦑🏮⬛🐟",
    )

    await db.log_result(4652, "FireBjorne", firebjorne, force=True)
    await db.log_result(4651, "Paradigm", paradigm, force=True)

    scoreboard = list(await db.scoreboard())

    assert len(scoreboard) == 2

    assert scoreboard[0][3] == "FireBjorne"
    assert scoreboard[0][5] == 375

    assert scoreboard[1][3] == "Paradigm"
    assert scoreboard[1][5] == 275


@pytest.mark.asyncio
async def test_scoreboard_orders_equal_scores_by_krillions(db: DatabaseHandler):
    # Both results have the same score, but the first has more Krillions.
    result_with_krillion = make_result(
        100,
        "🌟⬛⬛⬛⬛⬛⬛",
    )
    result_without_krillion = make_result(
        100,
        "⬛⬛⬛⬛⬛⬛⬛",
    )

    await db.log_result(4651, "Paradigm", result_without_krillion, force=True)
    await db.log_result(4652, "FireBjorne", result_with_krillion, force=True)

    scoreboard = list(await db.scoreboard())

    assert len(scoreboard) == 2

    assert scoreboard[0][3] == "FireBjorne"
    assert scoreboard[0][5] == 100
    assert scoreboard[0][6] == 1

    assert scoreboard[1][3] == "Paradigm"
    assert scoreboard[1][5] == 100
    assert scoreboard[1][6] == 0


@pytest.mark.asyncio
async def test_scoreboard_count_limits_number_of_results(db: DatabaseHandler):
    results = [
        (
            4651,
            "Paradigm",
            make_result(100, "🌟⬛⬛⬛⬛⬛⬛"),
        ),
        (
            4652,
            "FireBjorne",
            make_result(90, "🦑⬛⬛⬛⬛⬛⬛"),
        ),
        (
            4653,
            "Obscur",
            make_result(80, "🫧⬛⬛⬛⬛⬛⬛"),
        ),
    ]

    for user_id, name, result in results:
        await db.log_result(user_id, name, result, force=True)

    scoreboard = list(await db.scoreboard(count=2))

    assert len(scoreboard) == 2
    assert scoreboard[0][3] == "Paradigm"
    assert scoreboard[1][3] == "FireBjorne"


@pytest.mark.asyncio
async def test_best_game_returns_highest_scoring_game(db: DatabaseHandler):
    worse = make_result(
        275,
        "🌟⬛⬛🦑🏮⬛🐟",
        game_number=46,
    )
    better = make_result(
        375,
        "🌟🌟⬛🦑🏮⬛🐟",
        game_number=47,
    )

    await db.log_result(4652, "FireBjorne", worse, force=True)
    await db.log_result(4652, "FireBjorne", better, force=True)

    best = await db.best_game(4652)

    assert best is not None

    game_result = KrillionResult.from_database_row(tuple(best))

    assert game_result.game_number == 47
    assert game_result.score == 375
    assert game_result.as_emoji() == "🌟🌟⬛🦑🏮⬛🐟"


@pytest.mark.asyncio
async def test_best_game_returns_none_for_unknown_user(db: DatabaseHandler):
    assert await db.best_game(999999) is None


@pytest.mark.asyncio
async def test_aggregate_stats(db: DatabaseHandler):
    first = make_result(
        375,
        "🌟🌟⬛🦑🏮⬛🐟",
        46
    )
    second = make_result(
        275,
        "🌟⬛⬛🦑🏮⬛🐟",
        47
    )

    await db.log_result(4652, "FireBjorne", first, force=True)
    await db.log_result(4652, "FireBjorne", second, force=True)

    stats = await db.aggregate_stats(4652)
    assert stats is not None
    #stats[0] is the latest row_id, not ever needed
    assert stats[1] == db.guild_id
    assert stats[2] == 4652
    assert stats[3] == 'FireBjorne'
    # stats[4] should be the most recent game played, not super important here
    assert stats[4] == 47
    assert stats[5] == first.score + second.score
    assert stats[6] == first.krillions + second.krillions
    assert stats[7] == first.deep_cuts + second.deep_cuts
    assert stats[8] == first.rares + second.rares
    assert stats[9] == first.schoolers + second.schoolers
    assert stats[10] == first.clevers + second.clevers
    assert stats[11] == first.planktons + second.planktons
    assert stats[12] == first.empties + second.empties
    # stats[13] is latest result, not needed here probably
    # stats[14] is latest submission timestamp, again not relevant


@pytest.mark.asyncio
async def test_aggregate_stats_for_unknown_user_returns_none(db: DatabaseHandler):
    stats = await db.aggregate_stats(999999)

    assert stats == None


@pytest.mark.asyncio
async def test_wipe_all_removes_all_results(db: DatabaseHandler):
    result = make_result(
        375,
        "🌟🌟⬛🦑🏮⬛🐟",
        current_game_number()
    )

    await db.log_result(4652, "FireBjorne", result)

    assert await db.check_user_submitted_today(4652) is True

    await db.wipe_all()

    assert await db.check_user_submitted_today(4652) is False
    assert await db.scoreboard() == []

@pytest.mark.asyncio
async def test_setup_guild_creates_guild_settings(db: DatabaseHandler):
    await db.setup_guild()

    async with aiosqlite.connect(db.db_file_location) as connection:
        cursor = await connection.execute(
            "SELECT guild_id, krillion_channel_id FROM guildSettings WHERE guild_id = ?",
            (db.guild_id,),
        )
        result = await cursor.fetchone()

    assert result == (db.guild_id, None)


@pytest.mark.asyncio
async def test_set_krillion_channel(db: DatabaseHandler):
    await db.setup_guild()

    await db.set_krillion_channel(987654321)

    assert await db.get_krillion_channel() == 987654321


@pytest.mark.asyncio
async def test_set_krillion_channel_updates_existing_guild(db: DatabaseHandler):
    await db.setup_guild()

    await db.set_krillion_channel(111111111)
    await db.set_krillion_channel(222222222)

    assert await db.get_krillion_channel() == 222222222

    async with aiosqlite.connect(db.db_file_location) as connection:
        cursor = await connection.execute(
            "SELECT COUNT(*) FROM guildSettings WHERE guild_id = ?",
            (db.guild_id,),
        )
        result = await cursor.fetchone()

    assert result is not None and result[0] == 1


@pytest.mark.asyncio
async def test_get_krillion_channel_returns_false_when_guild_does_not_exist(db: DatabaseHandler):
    assert await db.get_krillion_channel() is None


@pytest.mark.asyncio
async def test_get_krillion_channel_returns_false_when_channel_is_not_set(db: DatabaseHandler):
    await db.setup_guild()

    assert await db.get_krillion_channel() is None


@pytest.mark.asyncio
async def test_remove_guild_removes_guild_settings(db: DatabaseHandler):
    await db.setup_guild()
    await db.set_krillion_channel(987654321)

    await db.remove_guild()

    async with aiosqlite.connect(db.db_file_location) as connection:
        cursor = await connection.execute(
            "SELECT * FROM guildSettings WHERE guild_id = ?",
            (db.guild_id,),
        )
        result = await cursor.fetchone()

    assert result is None


@pytest.mark.asyncio
async def test_remove_guild_removes_guild_results(db: DatabaseHandler):
    await db.setup_guild()

    result = make_result(
        375,
        "🌟🌟⬛🦑🏮⬛🐟",
        current_game_number()
    )

    await db.log_result(4652, "FireBjorne", result)

    assert await db.check_user_submitted_today(4652) is True

    await db.remove_guild()

    assert await db.check_user_submitted_today(4652) is False
    assert await db.scoreboard() == []


@pytest.mark.asyncio
async def test_remove_guild_removes_channel_and_results(db: DatabaseHandler):
    await db.setup_guild()
    await db.set_krillion_channel(987654321)

    result = make_result(
        375,
        "🌟🌟⬛🦑🏮⬛🐟",
        current_game_number()
    )

    await db.log_result(4652, "FireBjorne", result)

    await db.remove_guild()

    assert await db.get_krillion_channel() is None
    assert await db.check_user_submitted_today(4652) is False
    assert await db.scoreboard() == []


@pytest.mark.asyncio
async def test_remove_guild_does_not_remove_another_guild(
    db: DatabaseHandler,
):
    await db.setup_guild()

    other_guild = DatabaseHandler(456)
    await other_guild.setup_guild()

    await db.set_krillion_channel(111111111)
    await other_guild.set_krillion_channel(222222222)

    await db.remove_guild()

    assert await db.get_krillion_channel() is None
    assert await other_guild.get_krillion_channel() == 222222222