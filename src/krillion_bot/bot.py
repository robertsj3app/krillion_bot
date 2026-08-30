import os

import discord
from discord import Message
from discord.ext import commands
from dotenv import load_dotenv

from krillion_bot.services.database import DatabaseHandler

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
    DatabaseHandler.initial_setup(r"C:\Users\100 Acre Wood\Documents\Coding\krillion_bot\test.db")


@bot.event
async def on_message(message: Message):
    # Don't process our own messages.
    if message.author == bot.user:
        return

    # --------------------------------
    # Handle EVERY incoming message
    # --------------------------------

    # Eventually:
    # await database.log_message(message)

    # Eventually:
    # await parse_message(message)

    # --------------------------------
    # Then let !commands be processed
    # --------------------------------

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
@commands.has_permissions(manage_channels=True) # Restrict this command to admins/mods
async def set_krillion_channel(ctx: commands.Context, channel: discord.TextChannel):
    if ctx.guild:
        await DatabaseHandler(ctx.guild.id).set_krillion_channel(channel.id)
        await ctx.send(f"🎯 Target channel successfully set to {channel.mention}")


# @bot.command()
# async def stats(ctx):
#     await ctx.send("Stats go here.")


bot.run(TOKEN)
