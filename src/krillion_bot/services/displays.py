from dataclasses import dataclass, field
from krillion_bot.services.parser import KrillionResult, DatabaseRowType
from krillion_bot.utils.time import get_next_utc_4_boundary_from, format_datetime_for_discord
from krillion_bot.utils import current_game_number, Emojis
from typing import Self, Optional
from datetime import datetime

@dataclass
class ScoreboardRow:
    '''
    A user's entry on a Scoreboard. Maps a username string to a result.
    
    Attributes:
        user (str):
            The display name (or ideally mention string) for the user
        result (KrillionResult):
            The game result to score that user on.
    '''

    user: str
    result: KrillionResult

    @staticmethod
    def from_database_row(row: DatabaseRowType) -> 'ScoreboardRow':
        '''
        Instantiate a ScoreboardRow from a tuple matching the format returned
        by a database query.
        
        Args:
            row (DatabaseRowType):
                The database game row query to instantiate from
        
        Returns:
            A new ScoreboardRow for the provided database entry
        '''
        return ScoreboardRow(row[3], KrillionResult.from_database_row(row))


@dataclass
class Scoreboard:
    '''
    Dataclass to track ordered results for a set of users. Allows rows to
    be ordered by variable criteria from the row's KrillionResult.
    
    Attributes:
        winner (str):
            The display name (or ideally mention string) of the top-scoring user
        entries (list[ScoreboardRow]):
            The constituent user->result mappings that make up the Scoreboard
        sort_by (str):
            The metric to sort entries by to determine the winner. Defaults to total points.
    '''

    winner: str = field(init=False)
    entries: list[ScoreboardRow]
    sort_by: str = field(default='score')

    def __post_init__(self: Self):
        '''
        Sort entries by the selected comparison metric and set the current leader.
        
        Returns:
            None
        '''
        self.entries = sorted(self.entries, key=lambda e: getattr(e.result, self.sort_by), reverse=True)
        self.winner = self.entries[0].user if self.entries else ""

    def as_message(self: Self, top_n: Optional[int] = None) -> str:
        '''
        Return this Scoreboard formatted as a Discord message.
        
        Args:
            top_n (Optional[int]):
                If set, limit the scoreboard to the top N scorers.
                
        Returns
            A pretty-printed string with emojis and visuals to display in Discord
        '''
        if top_n is None:
            top_n = len(self.entries)
        medals = ["🥇", "🥈", "🥉"]

        lines = [
            f"{medals[i] if i < 3 else f'{i + 1}.'} "
            f"{element.user} - "
            f"{getattr(element.result, self.sort_by)} " +
            (f"({element.result.as_emoji()})" if self.sort_by == 'score' else "")
            for i, element in enumerate(self.entries[:top_n])
        ]

        return "\n".join(lines)

    @classmethod
    def from_database_result(cls, result: list[DatabaseRowType]):
        '''
        Instantiate a Scoreboard from a set of database results.
        
        Args:
            result (list[DatabaseRowType]):
                The list of database-schema-formatted tuples to build the
                constituent ScoreboardRows from
        '''
        return cls([ScoreboardRow.from_database_row(r) for r in result])


@dataclass
class DailyScoreboard(Scoreboard):
    '''
    Extends the base Scoreboard with additional formatting fluff to indicate
    that this Scoreboard is for a daily game result.
    
    Args:
        game_number (int):
            The game number that this Scoreboard is representing.
    '''
    game_number: int = field(init=False)

    def __post_init__(self: Self):
        '''
        Validate all daily entries share the same game before publishing the leaderboard.
        
        Returns:
            None
        
        Raises:
            ValueError:
                If entries come from multiple different game numbers.
        '''
        super().__post_init__()
        if len(set(e.result.game_number for e in self.entries)) > 1:
            raise ValueError('Cannot create daily scoreboard for entries from different games!')

        # TODO: This results in unexpected behavior if querying a scoreboard for a past game with no data in DB
        self.game_number = self.entries[0].result.game_number if self.entries else current_game_number()

    def as_message(self: Self, top_n: Optional[int] = None, final_result: bool = True) -> str:
        '''
        Return this Scoreboard formatted as a Discord message.
        
        Args:
            top_n (Optional[int]):
                If set, limit the scoreboard to the top N scorers.
            final_result (bool):
                If True, change formatting to declare a definitive winner,
                otherwise declare the top player as the leader and indicate
                that scoring is still open.
                
        Returns
            A pretty-printed string with emojis and visuals to display in Discord
        '''
        winner = self.entries[0] if self.entries else None

        scoreboard = super().as_message(top_n)

        if winner and final_result:
            winner_line = (
                f"🎉 **Today's Winner: {winner.user}!** 🎉\n"
                f"🏆 **Score:** {winner.result.score} "
            )
        elif winner and not final_result:
            winner_line = (
                f"**Leaderboard is not set in stone yet! Scores close at {format_datetime_for_discord(get_next_utc_4_boundary_from(datetime.now()))}!**\n"
                f"🙌 **Current Leader: {winner.user}!** 🙌\n"
                f"🏆 **Score:** {winner.result.score} "
            )
        else:
            winner_line = "😢 **No results yet today!**"

        return (
            f"🏆 **SCOREBOARD FOR GAME #{self.game_number}** 🏆\n"
            "\n"
            f"{winner_line}\n"
            "\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{scoreboard}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    

@dataclass
class OverallScoreboard(Scoreboard):
    '''
    Extends Scoreboard to indicate that rankings here are global lifetime rankings,
    and display a second set of rankings using a sub-Scoreboard based on total number
    of One-in-a-Krillion results.
    '''
    
    def as_message(self: Self, top_n: int | None = None) -> str:
        '''
        Render both the overall points leaderboard and the lifetime Krillion leaderboards.
        
        Args:
            top_n (int | None):
                Maximum number of entries to include in each leaderboard segment.
        
        Returns:
            str:
                A multi-section Discord message covering total points and total Krillions.
        '''
        winner = self.entries[0] if self.entries else None
        scoreboard_msg = super().as_message(top_n)
        
        scoreboard_krillions = Scoreboard(self.entries, sort_by='krillions')
        winner_krillions = scoreboard_krillions.entries[0] if scoreboard_krillions.entries else None
        scoreboard_krillions_msg = scoreboard_krillions.as_message(top_n)
        winner_line = ""
        winner_line_krillions = ""
        if winner:
            winner_line = (
                f"🎉 **Overall Points Leader: {winner.user}!** 🎉\n"
                f"🏆 **Score:** {winner.result.score} "
            )
        else:
            winner_line = winner_line_krillions = "😢 **No results ever logged!**"

        if winner_krillions:
            winner_line_krillions = (
                f"🌟 **Total # Krillions Leader: {winner_krillions.user}!** 🌟\n"
                f"🦐🏆 **Score:** {winner_krillions.result.krillions} "
            )

        return (
            f"🏆 **OVERALL RANKINGS** 🏆\n"
            "\n"
            f"{winner_line}\n"
            "\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{scoreboard_msg}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "\n"
            f"{winner_line_krillions}\n"
            "\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{scoreboard_krillions_msg}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    

@dataclass
class UserStats:
    '''
    Lifetime scoring summary for a single Discord user.
    
    This object aggregates a player's total lifetime score and category totals, and also keeps
    track of their best and most recent game so the bot can explain their performance in a clean
    summary message.
    
    Attributes:
        user_name (str):
            The display name associated with this user's results in this server.
        total_score (int):
            The sum of all points across this user's logged games.
        total_krillions (int):
            Total number of One in a Krillion results logged across all games.
        total_deep_cuts (int):
            Total number of Deep Cut results logged across all games.
        total_rares (int):
            Total number of Rare results logged across all games.
        total_schoolers (int):
            Total number of Schooler results logged across all games.
        total_clevers (int):
            Total number of Too Clever results logged across all games.
        total_planktons (int):
            Total number of Plankton results logged across all games.
        total_blanks (int):
            Total number of blanks logged across all games.
        best_game (KrillionResult):
            The user's highest-scoring result in this server.
        latest_game (KrillionResult):
            The user's most recently logged result in this server.
    '''

    user_name: str
    total_score: int
    total_krillions: int
    total_deep_cuts: int
    total_rares: int
    total_schoolers: int
    total_clevers: int
    total_planktons: int
    total_blanks: int
    best_game: KrillionResult
    latest_game: KrillionResult

    def __post_init__(self):
        '''
        Build a category-to-total lookup used for readable stats output.
        
        Returns:
            None
        '''
        self.EMOJI_MAPPING = {
            Emojis.K: self.total_krillions,
            Emojis.D: self.total_deep_cuts,
            Emojis.R: self.total_rares,
            Emojis.S: self.total_schoolers,
            Emojis.C: self.total_clevers,
            Emojis.P: self.total_planktons,
            Emojis.E: self.total_blanks
        }

    @classmethod
    def from_database_result(cls, agg_result: DatabaseRowType, best_game_result: DatabaseRowType, latest_game_result: DatabaseRowType) -> 'UserStats':
        '''
        Create a UserStats object from the aggregate row and the user's best/latest games.
        
        Args:
            agg_result (DatabaseRowType):
                The lifetime aggregate row returned by `DatabaseHandler.aggregate_stats()`.
            best_game_result (DatabaseRowType):
                The user's best game row from the database.
            latest_game_result (DatabaseRowType):
                The user's most recent game row from the database.
        
        Returns:
            UserStats:
                The lifetime summary for the selected user.
        
        Raises:
            ValueError:
                If the provided rows do not all belong to the same user.
        '''
        _, _, _, _, _, total_score, total_krillions, total_deep_cuts, total_rares, total_schoolers, total_clevers, total_planktons, total_blanks, _, _ = agg_result

        user_name_1 = agg_result[3]
        user_name_2 = best_game_result[3]
        user_name_3 = latest_game_result[3]

        if user_name_1 != user_name_2 != user_name_3:
            raise ValueError('Cannot build user stats from results for different users!')
        return UserStats(
            user_name_1, 
            total_score, 
            total_krillions, 
            total_deep_cuts, 
            total_rares, 
            total_schoolers, 
            total_clevers, 
            total_planktons, 
            total_blanks, 
            KrillionResult.from_database_row(best_game_result),
            KrillionResult.from_database_row(latest_game_result)
        )

    def as_message(self: Self):
        '''
        Render the user's lifetime stats as a Discord-ready summary.
        
        Returns:
            str:
                A multi-line message listing the latest game, best game, lifetime score,
                and category totals.
        '''
        return (
            f"**STATS FOR USER {self.user_name}**\n"
            "\n"
            f"**Latest Game:** #{self.latest_game.game_number} ({self.latest_game.score} - {self.latest_game.as_emoji()})\n"
            f"**Best Game:** #{self.best_game.game_number} ({self.best_game.score} - {self.best_game.as_emoji()})\n"
            f"**Lifetime Score:** {self.total_score}\n"
            f"**Total Responses by Category:**\n" +
            ("\n".join(f"{k}: {v}" for k,v in self.EMOJI_MAPPING.items()))
        )