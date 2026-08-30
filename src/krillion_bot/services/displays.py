from dataclasses import dataclass, field
from krillion_bot.services.parser import KrillionResult
from typing import Self, Optional

@dataclass
class ScoreboardRow:

    user: str
    result: KrillionResult

@dataclass
class Scoreboard:

    winner: str = field(init=False)
    entries: list[ScoreboardRow]

    def __post_init__(self: Self):
        self.entries = sorted(self.entries, key=lambda e: e.result.score, reverse=True)
        self.winner = self.entries[0].user

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

        return "```text\n" + "\n".join(lines) + "\n```"

class DailyScoreboard(Scoreboard):

    game_number: int = field(init=False)

    def __post_init__(self: Self):
        super().__post_init__()
        if not len(set(e.result.game_number for e in self.entries)) == 1:
            raise ValueError('Cannot create daily scoreboard for entries from different games!')
        self.game_number = self.entries[0].result.game_number

    def as_message(self: Self, top_n: Optional[int] = None) -> str:
        winner = self.entries[0] if self.entries else None

        scoreboard = super().as_message(top_n)

        if winner:
            winner_line = (
                f"🥳 🎉 **Today's Winner: @{winner.user}!** 🎉 🥳\n"
                f"🏆 **Score:** {winner.result.score} "
            )
        else:
            winner_line = "😢 **No results yet today!**"

        return (
            "🏆 **TODAY'S SCOREBOARD** 🏆\n"
            "\n"
            f"{winner_line}\n"
            "\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{scoreboard}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

