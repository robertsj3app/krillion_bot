from discord.ext import commands, tasks
import discord
from krillion_bot.services.database import DatabaseHandler
from krillion_bot.services.displays import DailyScoreboard, OverallScoreboard, UserStats
from krillion_bot.utils import current_game_number
from krillion_bot.utils.time import format_datetime_for_discord
from datetime import datetime
from typing import Optional

def register_commands(bot: commands.Bot):
    '''
    Register the Discord command surface for the Krillion bot.
    
    Args:
        bot (commands.Bot):
            The active Discord bot instance to attach commands to.
    '''
    
    @bot.command()
    @commands.is_owner()
    async def sync(ctx: commands.Context):
        '''
        Sync application commands to the current guild immediately.
        
        Args:
            ctx (commands.Context):
                The invoking command context.
        '''
        # Copies global commands to this specific server instantly
        if ctx.guild:
            bot.tree.copy_global_to(guild=ctx.guild)
            await bot.tree.sync(guild=ctx.guild)
            await ctx.send(f"Synced to {ctx.guild.name}")

    @bot.tree.command(name="link", description="Post a link to the daily dive.")
    async def link(interaction: discord.Interaction):
        '''
        Send a short link to the Krillion game homepage.

        Args:
            interaction (discord.Interaction):
                The slash-command interaction object.
        '''
        await interaction.response.send_message("🦐 [Click here for the daily dive!](https://krillion.io/) 🦐")

    @bot.tree.command(name="set_krillion_channel", description=f"Set the channel for {bot.user.name if bot.user else 'this bot'} to monitor for posted responses and send scoreboards to.")
    @commands.has_permissions(manage_channels=True) # Restrict this command to admins/mods
    async def set_krillion_channel(interaction: discord.Interaction, channel: discord.TextChannel):
        '''
        Set the channel that the bot watches for result submissions.

        Args:
            interaction (discord.Interaction):
                The slash-command interaction object.
            channel (discord.TextChannel):
                The Discord channel to monitor for Krillion results.
        '''
        if interaction.guild:
            await DatabaseHandler(interaction.guild.id).set_krillion_channel(channel.id)
            await interaction.response.send_message(f"🎯 Target channel successfully set to {channel.mention}", ephemeral=True)

    @bot.tree.command(name="reset_scores", description="Wipe the slate clean. Clears all recorded results for this server.")
    @commands.has_permissions(manage_channels=True) # Restrict this command to admins/mods
    async def reset_scores(interaction: discord.Interaction):
        '''
        Clear the current server's score history.

        Args:
            interaction (discord.Interaction):
                The slash-command interaction object.
        '''
        if interaction.guild:
            await DatabaseHandler(interaction.guild.id).wipe()
            await interaction.response.send_message(f"**Attention:** Scoring history has been reset for {interaction.guild.name} at {format_datetime_for_discord(datetime.now())}")
            message = await interaction.original_response()
            await message.pin()

    # @bot.tree.command(name="daily_scoreboard", description="Show today's scoreboard. Positions may change as new results are added.")
    # async def daily_scoreboard(interaction: discord.Interaction):
    #     if interaction.guild:
    #         data = [tuple(d) for d in await DatabaseHandler(interaction.guild.id).scoreboard('daily')]
    #         s = DailyScoreboard.from_database_result(data)
    #         await interaction.response.send_message(s.as_message(final_result=False))

    @bot.tree.command(name="scoreboard", description="Show a scoreboard for a past game.")
    async def scoreboard(interaction: discord.Interaction, game_number: Optional[int]):
        '''
        Show the leaderboard for a selected game number.

        Args:
            interaction (discord.Interaction):
                The slash-command interaction object.
            game_number (Optional[int]):
                The game number to fetch. Defaults to the current game if omitted.
        '''
        if not game_number:
            game_number = current_game_number()
             
        if game_number > current_game_number():
            await interaction.response.send_message("That game number hasn't happened yet!")
        
        if interaction.guild:
            data = [tuple(d) for d in await DatabaseHandler(interaction.guild.id).scoreboard(game_number)]
            s = DailyScoreboard.from_database_result(data)
            await interaction.response.send_message(s.as_message(final_result=True if game_number < current_game_number() else False))

    @bot.tree.command(name="overall_scoreboard", description="Show the overall rankings for this server, both for total points and number of krillions.")
    async def overall_scoreboard(interaction: discord.Interaction):
        '''
        Show the lifetime ranking for the server across points and Krillion totals.

        Args:
            interaction (discord.Interaction):
                The slash-command interaction object.
        '''
        if interaction.guild:
            h = DatabaseHandler(interaction.guild.id)
            aggregate_results = []
            for u in interaction.guild.members:
                stats = await h.aggregate_stats(u.id)
                if stats:
                    aggregate_results.append(tuple(stats))
             
            s = OverallScoreboard.from_database_result(aggregate_results)
            await interaction.response.send_message(s.as_message())

    @bot.tree.command(name="user_stats", description="Show the lifetime stats for a user.")
    async def user_stats(interaction: discord.Interaction, user: discord.User):
        '''
        Display the lifetime stats for an individual user.

        Args:
            interaction (discord.Interaction):
                The slash-command interaction object.
            user (discord.User):
                The user whose results should be summarized.
        '''
        if interaction.guild:
            h = DatabaseHandler(interaction.guild.id)
            stats = await h.aggregate_stats(user.id)
            best_game = await h.best_game(user.id)
            latest_game = await h.latest_game(user.id)
            if stats and best_game and latest_game:
                s = UserStats.from_database_result(tuple(stats), tuple(best_game), tuple(latest_game))
                await interaction.response.send_message(s.as_message())
            else:
                await interaction.response.send_message(f"❌ No results found for user {user.mention}")