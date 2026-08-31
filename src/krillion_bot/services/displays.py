from dataclasses import dataclass, field
from krillion_bot.services.parser import KrillionResult, DatabaseRowType
from krillion_bot.utils.time import get_next_utc_4_boundary_from, format_datetime_for_discord
from krillion_bot.utils import current_game_number, Emojis
from typing import Self, Optional
from datetime import datetime

@dataclass
class ScoreboardRow:

    user: str
    result: KrillionResult

    @staticmethod
    def from_database_row(row: DatabaseRowType) -> 'ScoreboardRow':
        return ScoreboardRow(row[3], KrillionResult.from_database_row(row))


@dataclass
class Scoreboard:

    winner: str = field(init=False)
    entries: list[ScoreboardRow]
    sort_by: str = field(default='score')

    def __post_init__(self: Self):
        self.entries = sorted(self.entries, key=lambda e: getattr(e.result, self.sort_by), reverse=True)
        self.winner = self.entries[0].user if self.entries else ""

    def as_message(self: Self, top_n: Optional[int] = None) -> str:
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
        return cls([ScoreboardRow.from_database_row(r) for r in result])


@dataclass
class DailyScoreboard(Scoreboard):

    game_number: int = field(init=False)

    def __post_init__(self: Self):
        super().__post_init__()
        if len(set(e.result.game_number for e in self.entries)) > 1:
            raise ValueError('Cannot create daily scoreboard for entries from different games!')

        # TODO: This results in unexpected behavior if querying a scoreboard for a past game with no data in DB
        self.game_number = self.entries[0].result.game_number if self.entries else current_game_number()

    def as_message(self: Self, top_n: Optional[int] = None, final_result: bool = True) -> str:
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
    
    def as_message(self: Self, top_n: int | None = None) -> str:
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
        return (
            f"**STATS FOR USER {self.user_name}**\n"
            "\n"
            f"**Latest Game:** #{self.latest_game.game_number} ({self.latest_game.score} - {self.latest_game.as_emoji()})\n"
            f"**Best Game:** #{self.best_game.game_number} ({self.best_game.score} - {self.best_game.as_emoji()})\n"
            f"**Lifetime Score:** {self.total_score}\n"
            f"**Total Responses by Category:**\n" +
            ("\n".join(f"{k}: {v}" for k,v in self.EMOJI_MAPPING.items()))
        )