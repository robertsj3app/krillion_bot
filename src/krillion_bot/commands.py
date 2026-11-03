from datetime import datetime
from typing import Optional

import discord
from discord.ext import commands

from krillion_bot.services.database import DatabaseHandler
from krillion_bot.services.displays import DailyScoreboard, OverallScoreboard, UserStats
from krillion_bot.utils import current_game_number
from krillion_bot.utils.time import format_datetime_for_discord


async def sync(ctx: commands.Context):
    '''
    Sync application commands to the current guild immediately.

    Args:
        ctx (commands.Context):
            The invoking command context.
    '''
    if ctx.guild:
        assert isinstance(ctx.bot, commands.Bot)
        ctx.bot.tree.copy_global_to(guild=ctx.guild)
        await ctx.bot.tree.sync(guild=ctx.guild)
        await ctx.send(f"Synced to {ctx.guild.name}")


async def link(interaction: discord.Interaction):
    '''
    Send a short link to the Krillion game homepage.

    Args:
        interaction (discord.Interaction):
            The slash-command interaction object.
    '''
    await interaction.response.send_message(
        "🦐 [Click here for the daily dive!](https://krillion.io/) 🦐"
    )


async def set_krillion_channel(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
):
    '''
    Set the channel that the bot watches for result submissions.

    Args:
        interaction (discord.Interaction):
            The slash-command interaction object.
        channel (discord.TextChannel):
            The Discord channel to monitor for result submissions.
    '''
    if interaction.guild:
        await DatabaseHandler(interaction.guild.id).set_krillion_channel(channel.id)
        await interaction.response.send_message(
            f"🎯 Target channel successfully set to {channel.mention}",
            ephemeral=True,
        )


async def reset_scores(interaction: discord.Interaction):
    '''
    Clear the current server's score history.

    Args:
        interaction (discord.Interaction):
            The slash-command interaction object.
    '''
    if interaction.guild:
        await DatabaseHandler(interaction.guild.id).wipe()
        await interaction.response.send_message(
            f"**Attention:** Scoring history has been reset for "
            f"{interaction.guild.name} at "
            f"{format_datetime_for_discord(datetime.now())}"
        )
        message = await interaction.original_response()
        await message.pin()


async def scoreboard(
    interaction: discord.Interaction,
    game_number: Optional[int],
    ephemeral: bool = True,
):
    '''
    Show the leaderboard for a selected game number.

    Args:
        interaction (discord.Interaction):
            The slash-command interaction object.
        game_number (Optional[int]):
            The game number to fetch. Defaults to the current game if omitted.
        ephemeral (bool):
            Whether the response is visible only to the invoking user.
    '''
    if not game_number:
        game_number = current_game_number()

    if game_number > current_game_number():
        await interaction.response.send_message(
            "That game number hasn't happened yet!"
        )

    if interaction.guild:
        data = await DatabaseHandler(interaction.guild.id).scoreboard(game_number)
        scoreboard_display = DailyScoreboard.from_database_result(data)
        await interaction.response.send_message(
            scoreboard_display.as_message(
                final_result=game_number < current_game_number()
            ),
            ephemeral=ephemeral,
        )


async def overall_scoreboard(
    interaction: discord.Interaction,
    ephemeral: bool = True,
):
    '''
    Show the overall rankings for this server by KrELO and Krillion totals.

    Args:
        interaction (discord.Interaction):
            The slash-command interaction object.
        ephemeral (bool):
            Whether the response is visible only to the invoking user.
    '''
    if interaction.guild:
        handler = DatabaseHandler(interaction.guild.id)
        aggregate_results = [
            result
            for result in [
                await handler.aggregate_stats(member.id)
                for member in interaction.guild.members
            ]
            if result is not None
        ]
        scoreboard_display = OverallScoreboard.from_database_result(aggregate_results)
        await interaction.response.send_message(
            scoreboard_display.as_message(),
            ephemeral=ephemeral,
        )


async def user_stats(
    interaction: discord.Interaction,
    user: discord.User,
    ephemeral: bool = True,
):
    '''
    Display the lifetime stats for an individual user.

    Args:
        interaction (discord.Interaction):
            The slash-command interaction object.
        user (discord.User):
            The user whose results should be summarized.
        ephemeral (bool):
            Whether the response is visible only to the invoking user.
    '''
    if interaction.guild:
        handler = DatabaseHandler(interaction.guild.id)
        stats = await handler.aggregate_stats(user.id)
        best_game = await handler.best_game(user.id)
        latest_game = await handler.latest_game(user.id)
        if stats and best_game and latest_game:
            stats_display = UserStats.from_database_result(
                stats,
                best_game,
                latest_game,
            )
            await interaction.response.send_message(
                stats_display.as_message(),
                ephemeral=ephemeral,
            )
        else:
            await interaction.response.send_message(
                f"❌ No results found for user {user.mention}",
                ephemeral=ephemeral,
            )


def register_commands(bot: commands.Bot):
    '''
    Register the Discord command surface for the Krillion bot.

    Args:
        bot (commands.Bot):
            The active Discord bot instance receiving the event hooks.
    '''
    bot.command()(commands.is_owner()(sync))
    
    bot.tree.command(
        name="link",
        description="Post a link to the daily dive.",
    )(link)
    
    bot.tree.command(
        name="set_krillion_channel",
        description=(
            f"Set the channel for {bot.user.name if bot.user else 'this bot'} "
            "to monitor for posted responses and send scoreboards to."
        ),
    )(commands.has_permissions(manage_channels=True)(set_krillion_channel))
    
    bot.tree.command(
        name="reset_scores",
        description="Wipe the slate clean. Clears all recorded results for this server.",
    )(commands.has_permissions(manage_channels=True)(reset_scores))
    
    bot.tree.command(
        name="scoreboard",
        description="Show a scoreboard for a past game.",
    )(scoreboard)
    
    bot.tree.command(
        name="overall_scoreboard",
        description=(
            "Show the overall rankings for this server by KrELO and "
            "number of krillions."
        ),
    )(overall_scoreboard)
    
    bot.tree.command(
        name="user_stats",
        description="Show the lifetime stats for a user.",
    )(user_stats)
