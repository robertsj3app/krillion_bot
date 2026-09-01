from discord.ext import commands, tasks
import discord
import os
from krillion_bot.services.database import DatabaseHandler, DoubleSubmissionException
from krillion_bot.services.parser import KrillionResult
from krillion_bot.services.displays import DailyScoreboard
from krillion_bot.utils.time import MIDNIGHT_EST
from krillion_bot.utils import current_game_number

def register_events(bot: commands.Bot):
    '''
    Register the bot lifecycle and message-processing event handlers.

    Args:
        bot (commands.Bot):
            The active Discord bot instance receiving the event hooks.
    '''
    
    @tasks.loop(time=MIDNIGHT_EST)
    async def midnight_show_scoreboard():
        '''
        Publish the complete daily scoreboard when the Krillion reset window arrives.

        Returns:
            None
        '''
        for guild in bot.guilds:
            h = DatabaseHandler(guild.id)
            krillion_channel_id = await h.get_krillion_channel()
            if krillion_channel_id:
                data = [tuple(d) for d in await DatabaseHandler(guild.id).scoreboard(current_game_number()-1)]
                s = DailyScoreboard.from_database_result(data)
                krillion_channel = bot.get_channel(krillion_channel_id)
                if isinstance(krillion_channel, discord.TextChannel):
                    await krillion_channel.send(s.as_message(final_result=True))
                    await krillion_channel.send("🦐 [A new daily dive is available!](https://krillion.io/) 🦐")
    
    @bot.event
    async def on_ready():
        '''
        Initialize the database and start the daily scoreboard loop once the bot is ready.

        Returns:
            None
        '''
        print(f"Logged in as {bot.user}")
        DatabaseHandler.initial_setup(os.environ['DB_FILE_LOCATION'])
        if not midnight_show_scoreboard.is_running():
            print("starting midnight scoreboard loop!")
            midnight_show_scoreboard.start()

    @bot.event
    async def on_message(message: discord.Message):
        '''
        Watch the configured Krillion channel for pasted result strings and validate submissions.

        Args:
            message (discord.Message):
                The incoming Discord message to inspect.
        '''
        # Don't process our own messages.
        if message.author == bot.user:
            return

        if message.guild:
            h = DatabaseHandler(message.guild.id)
            if message.channel.id == await h.get_krillion_channel():
                try:
                    result = KrillionResult.from_result_string(message.content)
                    if result.valid:
                        try:
                            await h.log_result(message.author.id, message.author.mention, result)
                            await message.add_reaction("✅")
                        except DoubleSubmissionException as e:
                            await message.reply(str(e))
                            await message.delete()
                    else:
                        await message.add_reaction("❌")
                except:
                    pass

        await bot.process_commands(message)

    @bot.event
    async def on_guild_join(guild: discord.Guild):
        '''
        Create the storage baseline when the bot joins a new Discord guild.

        Args:
            guild (discord.Guild):
                The Discord server the bot just joined.
        '''
        # Establish a baseline profile entry right away
        await DatabaseHandler(guild.id).setup_guild()

    @bot.event
    async def on_guild_remove(guild: discord.Guild):
        '''
        Remove the guild's stored data when the bot leaves a Discord server.

        Args:
            guild (discord.Guild):
                The Discord server the bot is leaving.
        '''
        # Wipe server footprint if it removes the bot 
        await DatabaseHandler(guild.id).remove_guild()