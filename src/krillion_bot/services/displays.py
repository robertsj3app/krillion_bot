from dataclasses import dataclass, field
from krillion_bot.services.parser import KrillionResult, DatabaseRowType
from krillion_bot.utils.time import get_next_utc_4_boundary_from, format_datetime_for_discord
from krillion_bot.utils import current_game_number
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
            f"{element.result.score} "
            f"({element.result.as_emoji()})"
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
                f"🥳 🎉 **Today's Winner: {winner.user}!** 🎉 🥳\n"
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

    def __post_init__(self: Self):
        super().__post_init__()
        self.entries_krillions = sorted(self.entries, key=lambda e: e.result.krillions)
    
    def as_message(self: Self, top_n: int | None = None) -> str:
        winner = self.entries[0] if self.entries else None
        scoreboard = super().as_message(top_n)
        
        if winner:
            winner_line = (
                f"🥳 🎉 **Overall Leader: {winner.user}!** 🎉 🥳\n"
                f"🏆 **Score:** {winner.result.score} "
            )
        