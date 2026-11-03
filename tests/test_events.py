from datetime import datetime
from functools import partial
from unittest.mock import AsyncMock, Mock
from zoneinfo import ZoneInfo

import discord
import pytest

from krillion_bot import events


def make_message(content=""):
    message = Mock()
    message.author = Mock()
    message.author.id = 42
    message.author.mention = "<@42>"
    message.channel = Mock()
    message.channel.id = 456
    message.guild = Mock()
    message.guild.id = 123
    message.content = content
    message.add_reaction = AsyncMock()
    message.reply = AsyncMock()
    message.delete = AsyncMock()
    return message


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("now", "expect_overall"),
    [
        (datetime(2026, 11, 7, 0, 0, tzinfo=ZoneInfo("America/New_York")), True),
        (datetime(2026, 11, 8, 0, 0, tzinfo=ZoneInfo("America/New_York")), False),
    ],
)
async def test_midnight_scoreboard_posts_overall_rankings_only_on_saturday(
    monkeypatch,
    now,
    expect_overall,
):
    channel = Mock(spec=discord.TextChannel)
    channel.send = AsyncMock()
    guild = Mock()
    guild.id = 123
    guild.members = [Mock(id=1), Mock(id=2)]
    bot = Mock()
    bot.guilds = [guild]
    bot.get_channel.return_value = channel

    handler = Mock()
    handler.get_krillion_channel = AsyncMock(return_value=456)
    handler.scoreboard = AsyncMock(return_value=[])
    handler.aggregate_stats = AsyncMock(return_value=None)
    monkeypatch.setattr(events, "DatabaseHandler", lambda guild_id: handler)

    await events.midnight_show_scoreboard(bot, now)

    sent_messages = [call.args[0] for call in channel.send.await_args_list]
    assert len(sent_messages) == (3 if expect_overall else 2)
    assert sent_messages[0].startswith("🏆 **SCOREBOARD FOR GAME #")
    if expect_overall:
        assert sent_messages[1].startswith("🏆 **OVERALL RANKINGS**")
        assert handler.aggregate_stats.await_count == 2
    else:
        assert handler.aggregate_stats.await_count == 0
    assert "A new daily dive is available!" in sent_messages[-1]


@pytest.mark.asyncio
@pytest.mark.parametrize("loop_running", [False, True])
async def test_on_ready_initializes_database_and_starts_loop_once(
    monkeypatch,
    loop_running,
    capsys,
):
    database_setup = Mock()
    monkeypatch.setattr(events.DatabaseHandler, "initial_setup", database_setup)
    monkeypatch.setenv("DB_FILE_LOCATION", "scores.db")
    bot = Mock(user="Krillion bot")
    scoreboard_loop = Mock()
    scoreboard_loop.is_running.return_value = loop_running

    await events.on_ready(bot, scoreboard_loop)

    database_setup.assert_called_once_with("scores.db")
    scoreboard_loop.is_running.assert_called_once_with()
    if loop_running:
        scoreboard_loop.start.assert_not_called()
    else:
        scoreboard_loop.start.assert_called_once_with()
    assert "Logged in as Krillion bot" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_on_message_ignores_messages_from_the_bot(monkeypatch):
    bot = Mock()
    bot.user = Mock()
    message = make_message()
    message.author = bot.user
    database_handler = Mock()
    monkeypatch.setattr(events, "DatabaseHandler", lambda guild_id: database_handler)

    await events.on_message(bot, message)

    database_handler.get_krillion_channel.assert_not_called()
    message.add_reaction.assert_not_awaited()


@pytest.mark.asyncio
async def test_on_message_ignores_messages_outside_configured_channel(monkeypatch):
    bot = Mock()
    bot.user = Mock()
    message = make_message()
    handler = Mock()
    handler.get_krillion_channel = AsyncMock(return_value=999)
    monkeypatch.setattr(events, "DatabaseHandler", lambda guild_id: handler)

    await events.on_message(bot, message)

    handler.get_krillion_channel.assert_awaited_once_with()
    message.add_reaction.assert_not_awaited()


@pytest.mark.asyncio
async def test_on_message_logs_valid_result_and_reacts(monkeypatch):
    bot = Mock()
    bot.user = Mock()
    message = make_message("Krillion #46 🦐\n375\n\n🌟🌟⬛🦑🏮⬛🐟")
    handler = Mock()
    handler.get_krillion_channel = AsyncMock(return_value=456)
    handler.log_result = AsyncMock()
    monkeypatch.setattr(events, "DatabaseHandler", lambda guild_id: handler)

    await events.on_message(bot, message)

    handler.log_result.assert_awaited_once()
    args = handler.log_result.await_args.args
    assert args[:2] == (42, "<@42>")
    assert args[2].game_number == 46
    message.add_reaction.assert_awaited_once_with("✅")


@pytest.mark.asyncio
async def test_on_message_reacts_to_invalid_result(monkeypatch):
    bot = Mock()
    bot.user = Mock()
    message = make_message("Krillion #46 🦐\n1\n\n🌟🌟⬛🦑🏮⬛🐟")
    handler = Mock()
    handler.get_krillion_channel = AsyncMock(return_value=456)
    handler.log_result = AsyncMock()
    monkeypatch.setattr(events, "DatabaseHandler", lambda guild_id: handler)

    await events.on_message(bot, message)

    message.add_reaction.assert_awaited_once_with("❌")
    handler.log_result.assert_not_awaited()


@pytest.mark.asyncio
async def test_on_message_replies_and_deletes_duplicate_submission(monkeypatch):
    bot = Mock()
    bot.user = Mock()
    message = make_message("Krillion #46 🦐\n375\n\n🌟🌟⬛🦑🏮⬛🐟")
    handler = Mock()
    handler.get_krillion_channel = AsyncMock(return_value=456)
    handler.log_result = AsyncMock(
        side_effect=events.DoubleSubmissionException("Already submitted")
    )
    monkeypatch.setattr(events, "DatabaseHandler", lambda guild_id: handler)

    await events.on_message(bot, message)

    message.reply.assert_awaited_once_with("Already submitted")
    message.delete.assert_awaited_once_with()
    message.add_reaction.assert_not_awaited()


@pytest.mark.asyncio
async def test_on_message_ignores_unparseable_result(monkeypatch):
    bot = Mock()
    bot.user = Mock()
    message = make_message("not a result")
    handler = Mock()
    handler.get_krillion_channel = AsyncMock(return_value=456)
    monkeypatch.setattr(events, "DatabaseHandler", lambda guild_id: handler)

    await events.on_message(bot, message)

    message.add_reaction.assert_not_awaited()


@pytest.mark.asyncio
async def test_on_guild_join_sets_up_guild(monkeypatch):
    handler = Mock()
    handler.setup_guild = AsyncMock()
    monkeypatch.setattr(events, "DatabaseHandler", lambda guild_id: handler)
    guild = Mock(id=123)

    await events.on_guild_join(guild)

    handler.setup_guild.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_on_guild_remove_removes_guild(monkeypatch):
    handler = Mock()
    handler.remove_guild = AsyncMock()
    monkeypatch.setattr(events, "DatabaseHandler", lambda guild_id: handler)
    guild = Mock(id=123)

    await events.on_guild_remove(guild)

    handler.remove_guild.assert_awaited_once_with()


def test_register_events_registers_all_handlers(monkeypatch):
    bot = Mock()
    loop = Mock()
    loop_decorator = Mock(return_value=loop)
    monkeypatch.setattr(events.tasks, "loop", Mock(return_value=loop_decorator))

    events.register_events(bot)

    assert [call.kwargs["name"] for call in bot.add_listener.call_args_list] == [
        "on_ready",
        "on_message",
        "on_guild_join",
        "on_guild_remove",
    ]
    assert isinstance(bot.add_listener.call_args_list[0].args[0], partial)
    assert bot.add_listener.call_args_list[1].kwargs["name"] == "on_message"
