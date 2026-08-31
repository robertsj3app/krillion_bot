from discord.ext import commands
import discord
import os
from krillion_bot.services.database import DatabaseHandler, DoubleSubmissionException
from krillion_bot.services.parser import KrillionResult

def register_events(bot: commands.Bot):
    @bot.event
    async def on_ready():
        print(f"Logged in as {bot.user}")
        DatabaseHandler.initial_setup(os.environ['DB_FILE_LOCATION'])

    @bot.event
    async def on_message(message: discord.Message):
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