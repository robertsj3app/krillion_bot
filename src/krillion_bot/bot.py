import os

import discord
from discord import Message, app_commands
from discord.ext import commands
from dotenv import load_dotenv

from krillion_bot.services.database import DatabaseHandler, DoubleSubmissionException
from krillion_bot.services.parser import KrillionResult
from krillion_bot.services.displays import DailyScoreboard
from krillion_bot.utils import current_game_number

from typing import Optional

load_dotenv()

TOKEN = os.environ["DISCORD_TOKEN"]

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    DatabaseHandler.initial_setup(os.environ['DB_FILE_LOCATION'])

@bot.event
async def on_message(message: Message):
    # Don't process our own messages.
    if message.author == bot.user:
        return

    if message.guild:
        h = DatabaseHandler(message.guild.id)
        if message.channel.id == await h.get_krillion_channel():
            try:
                result = KrillionResult.from_result_string(message.content)
                try:
                    await h.log_result(message.author.id, message.author.mention, result)
                    await message.add_reaction("✅")
                except DoubleSubmissionException as e:
                    await message.reply(str(e))
                    await message.delete()
            except:
                pass

    await bot.process_commands(message)

@bot.event
async def on_guild_join(guild: discord.Guild):
    # Establish a baseline profile entry right away
    await DatabaseHandler(guild.id).setup_guild()

@bot.event
async def on_guild_remove(guild: discord.Guild):
    # Wipe server footprint if it removes the bot 
    await DatabaseHandler(guild.id).remove_guild()

@bot.command()
@commands.is_owner()
async def sync_guild(ctx):
    # Copies global commands to this specific server instantly
    bot.tree.copy_global_to(guild=ctx.guild)
    await bot.tree.sync(guild=ctx.guild)
    await ctx.send("Synced to this guild instantly!")

@bot.tree.command(name="set_krillion_channel", description="Set the channel for MechaShrimp to monitor for posted responses and send scoreboards to.")
@commands.has_permissions(manage_channels=True) # Restrict this command to admins/mods
async def set_krillion_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if interaction.guild:
        await DatabaseHandler(interaction.guild.id).set_krillion_channel(channel.id)
        await interaction.response.send_message(f"🎯 Target channel successfully set to {channel.mention}")

@bot.tree.command(name="reset_scores", description="Wipe the slate clean! Clears all recorded results for this server.")
@commands.has_permissions(manage_channels=True) # Restrict this command to admins/mods
async def reset_scores(interaction: discord.Interaction):
    if interaction.guild:
        await DatabaseHandler(interaction.guild.id).wipe()
        await interaction.response.send_message(f"Scores cleared!")

@bot.tree.command(name="daily_scoreboard", description="Show today's scoreboard! Positions may change as new results are added.")
async def daily_scoreboard(interaction: discord.Interaction):
    if interaction.guild:
        data = [tuple(d) for d in await DatabaseHandler(interaction.guild.id).scoreboard('daily')]
        s = DailyScoreboard.from_database_result(data)
        await interaction.response.send_message(s.as_message(final_result=False))

@bot.tree.command(name="past_scoreboard", description="Show a scoreboard for a past game.")
async def past_scoreboard(interaction: discord.Interaction, game_number: int):
    if game_number > current_game_number():
        await interaction.response.send_message("That game number hasn't happened yet!")
    if interaction.guild:
        data = [tuple(d) for d in await DatabaseHandler(interaction.guild.id).scoreboard(game_number)]
        s = DailyScoreboard.from_database_result(data)
        await interaction.response.send_message(s.as_message(final_result=True if game_number < current_game_number() else False))

bot.run(TOKEN)
