import functools
import os

import discord
from discord.ext import commands, tasks

from krillion_bot.services.database import DatabaseHandler, DoubleSubmissionException
from krillion_bot.services.displays import DailyScoreboard
from krillion_bot.services.parser import KrillionResult
from krillion_bot.utils import current_game_number
from krillion_bot.utils.time import MIDNIGHT_EST


async def midnight_show_scoreboard(bot: commands.Bot):
    '''
    Publish the complete daily scoreboard when the Krillion reset window arrives.

    Args:
        bot (commands.Bot):
            The bot whose guilds should receive the scoreboard.
    '''
    for guild in bot.guilds:
        handler = DatabaseHandler(guild.id)
        krillion_channel_id = await handler.get_krillion_channel()
        if krillion_channel_id:
            data = await handler.scoreboard(current_game_number() - 1)
            scoreboard = DailyScoreboard.from_database_result(data)
            krillion_channel = bot.get_channel(krillion_channel_id)
            if isinstance(krillion_channel, discord.TextChannel):
                await krillion_channel.send(scoreboard.as_message(final_result=True))
                await krillion_channel.send(
                    "🦐 [A new daily dive is available!](https://krillion.io/) 🦐"
                )


async def on_ready(
    bot: commands.Bot,
    scoreboard_loop: tasks.Loop,
):
    '''
    Initialize the database and start the daily scoreboard loop once the bot is ready.

    Args:
        bot (commands.Bot):
            The bot that has completed startup.
        scoreboard_loop (tasks.Loop):
            The scheduled daily scoreboard task.
    '''
    print(f"Logged in as {bot.user}")
    DatabaseHandler.initial_setup(os.environ["DB_FILE_LOCATION"])
    if not scoreboard_loop.is_running():
        print("starting midnight scoreboard loop!")
        scoreboard_loop.start()


async def on_message(bot: commands.Bot, message: discord.Message):
    '''
    Watch the configured Krillion channel for pasted result strings and validate submissions.

    Args:
        bot (commands.Bot):
            The bot receiving the message.
        message (discord.Message):
            The incoming Discord message to inspect.
    '''
    if message.author == bot.user:
        return

    if message.guild:
        handler = DatabaseHandler(message.guild.id)
        if message.channel.id == await handler.get_krillion_channel():
            try:
                result = KrillionResult.from_result_string(message.content)
                if result.valid:
                    try:
                        await handler.log_result(
                            message.author.id,
                            message.author.mention,
                            result,
                        )
                        await message.add_reaction("✅")
                    except DoubleSubmissionException as error:
                        await message.reply(str(error))
                        await message.delete()
                else:
                    await message.add_reaction("❌")
            except Exception:
                pass

    # await bot.process_commands(message)


async def on_guild_join(guild: discord.Guild):
    '''
    Create the storage baseline when the bot joins a new Discord guild.

    Args:
        guild (discord.Guild):
            The Discord server the bot just joined.
    '''
    await DatabaseHandler(guild.id).setup_guild()


async def on_guild_remove(guild: discord.Guild):
    '''
    Remove the guild's stored data when the bot leaves a Discord server.

    Args:
        guild (discord.Guild):
            The Discord server the bot is leaving.
    '''
    await DatabaseHandler(guild.id).remove_guild()


def register_events(bot: commands.Bot):
    '''
    Register the bot lifecycle and message-processing event handlers.

    Args:
        bot (commands.Bot):
            The active Discord bot instance receiving the event hooks.
    '''
    scoreboard_loop = tasks.loop(time=MIDNIGHT_EST)(
        functools.partial(midnight_show_scoreboard, bot)
    )
    bot.add_listener(
        functools.partial(on_ready, bot, scoreboard_loop),
        name="on_ready",
    )
    bot.add_listener(
        functools.partial(on_message, bot), 
        name="on_message"
    )
    bot.add_listener(
        on_guild_join, 
        name="on_guild_join"
    )
    bot.add_listener(
        on_guild_remove, 
        name="on_guild_remove"
    )
