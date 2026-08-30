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

    print(
        f"{message.author}: {message.content}"
    )

    # Eventually:
    # await database.log_message(message)

    # Eventually:
    # await parse_message(message)

    # --------------------------------
    # Then let !commands be processed
    # --------------------------------

    await bot.process_commands(message)


# @bot.command()
# async def hello(ctx):
#     await ctx.send("Hello!")


# @bot.command()
# async def stats(ctx):
#     await ctx.send("Stats go here.")


bot.run(TOKEN)
