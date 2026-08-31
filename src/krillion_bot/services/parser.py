from dataclasses import dataclass, field
from typing import Sequence, Self, TypeVar
import re
from textwrap import dedent
from krillion_bot.utils import AnswerCategories, KrillionCategory

T = TypeVar('T')
DatabaseRowType = tuple[int, int, int, str, int, int, int, int, int, int, int, int, int, str, str]

@dataclass
class KrillionResult:

    game_number: int
    score: int
    answers: Sequence[KrillionCategory]
    krillions: int = field(init=False)
    deep_cuts: int = field(init=False)
    rares: int = field(init=False)
    schoolers: int = field(init=False)
    clevers: int = field(init=False)
    planktons: int = field(init=False)
    empties: int = field(init=False)

    FORMAT = re.compile((r'Krillion #(\d+) \\U0001f990\n(\d+)\n\n' + (r'(\\[U|u][a-fA-F0-9]{4,})' * 7)))

    #TODO: Deprecated, remove from tests
    CATEGORY_LOOKUP_UNICODE = {
        c.value.unicode: c.value for c in AnswerCategories
    }
    CATEGORY_LOOKUP_CHAR = {
        c.value.category[0]: c.value for c in AnswerCategories
    }

    def __post_init__(self: Self):
        self.krillions = 0
        self.deep_cuts = 0
        self.rares = 0
        self.schoolers = 0
        self.clevers = 0
        self.planktons = 0
        self.empties = 0
        for a in self.answers:
            match a.score:
                case 100:
                    self.krillions += 1
                case 85:
                    self.deep_cuts += 1
                case 60:
                    self.rares += 1
                case 30:
                    self.schoolers += 1
                case 15:
                    self.clevers += 1
                case 10:
                    self.planktons += 1
                case _:
                    self.empties += 1

    def as_emoji(self: Self):
        return ''.join(a.as_emoji() for a in self.answers)

    @property
    def valid(self: Self) -> bool:
        return sum(a.score for a in self.answers) == self.score

    @staticmethod
    def from_result_string(result: str) -> 'KrillionResult':
        decoded = dedent(result.strip().encode('ascii', errors='backslashreplace').decode('ascii'))
        match = re.match(KrillionResult.FORMAT, decoded)
        if match:
            game_number, score, *answers_unicode = match.groups()
            return KrillionResult(int(game_number), int(score), [AnswerCategories.from_unicode(u).value for u in answers_unicode])
        else:
            raise ValueError('Tried to create KrillionResult from invalid string. Check formatting and make sure to paste exactly the result of selecting "Copy Results".')
            
    @staticmethod
    def from_database_row(row: DatabaseRowType):
        _, _, _, _, game_number, score, _, _, _, _, _, _, _, answers_str, _, = row
        return KrillionResult(game_number, score, [AnswerCategories.from_char(c).value for c in answers_str])