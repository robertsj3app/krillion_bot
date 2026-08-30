from dataclasses import dataclass, field
from typing import Sequence, Self, TypeVar
import re
from textwrap import dedent

T = TypeVar('T')

@dataclass(frozen=True)
class KrillionCategory:

    unicode: str
    category: str
    score: int

    def __repr__(self):
        return f'KrillionCategory({self.category})'

    def as_emoji(self: Self):
        return self.unicode.encode("utf-8").decode("unicode-escape")


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
    CATEGORIES = [
        KrillionCategory(
            r"\U0001f31f",
            "One in a Krillion",
            100
        ),
        KrillionCategory(
            r"\U0001f991",
            "Deep Cut",
            85
        ),
        KrillionCategory(
            r"\U0001f3ee",
            "Rare",
            60
        ),
        KrillionCategory(
            r"\U0001f41f",
            "Schooler",
            30
        ),
        KrillionCategory(
            r"\U0001f921",
            "Too Clever",
            15
        ),
        KrillionCategory(
            r"\U0001fae7",
            "Plankton",
            10
        ),
        KrillionCategory(
            r"\u2b1b",
            "No Response",
            0
        )
    ]
    CATEGORY_LOOKUP_UNICODE = {
        c.unicode: c for c in CATEGORIES
    }
    CATEGORY_LOOKUP_CHAR = {
        c.category[0]: c for c in CATEGORIES
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
    def _parse_by_lookup(game_number, score, lookup: dict[T, KrillionCategory], keys: Sequence[T]):
        bad_lookup: list[T] = []
        answers: list[KrillionCategory] = []
        for k in keys:
            lookup_result = lookup.get(k)
            if isinstance(lookup_result, KrillionCategory):
                answers.append(lookup_result)
            else:
                bad_lookup.append(k)
            
        if len(bad_lookup) == 0:
            return KrillionResult(int(game_number), int(score), answers)
        else:
            raise ValueError(f'Unable to map found unicode string(s) to Krillion categories: {bad_lookup}')

    @staticmethod
    def from_result_string(result: str) -> 'KrillionResult':
        decoded = dedent(result.strip().encode('ascii', errors='backslashreplace').decode('ascii'))
        match = re.match(KrillionResult.FORMAT, decoded)
        if match:
            game_number, score, *answers_unicode = match.groups()
            return KrillionResult._parse_by_lookup(game_number, score, KrillionResult.CATEGORY_LOOKUP_UNICODE, answers_unicode)
        else:
            raise ValueError('Tried to create KrillionResult from invalid string. Check formatting and make sure to paste exactly the result of selecting "Copy Results".')
            
    @staticmethod
    def from_database_row(row: tuple[int, int, int, str, int, int, int, int, int, int, int, int, int, str, str]):
        _, _, _, _, game_number, score, _, _, _, _, _, _, _, answers_str, _, = row
        return KrillionResult._parse_by_lookup(game_number, score, KrillionResult.CATEGORY_LOOKUP_CHAR, answers_str)
                

        