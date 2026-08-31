import os

import discord
from discord import Message
from discord.ext import commands
from dotenv import load_dotenv

from krillion_bot.commands import register_commands
from krillion_bot.events import register_events

load_dotenv()

TOKEN = os.environ["DISCORD_TOKEN"]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
)

register_events(bot)
register_commands(bot)

bot.run(TOKEN)
