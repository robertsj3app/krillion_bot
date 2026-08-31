from dataclasses import dataclass
from typing import Self
from enum import Enum
from .emojis import Emojis

@dataclass(frozen=True)
class KrillionCategory:

    emoji: Emojis
    # unicode: str
    letter_code: str
    category: str
    score: int

    @property
    def unicode(self) -> str:
        return self.emoji.to_unicode()

    def __repr__(self):
        return f'KrillionCategory({self.category})'

    def as_emoji(self: Self):
        return self.emoji

class AnswerCategories(Enum):

    KRILLION = K = KrillionCategory(
        Emojis.K,
        "O",
        "One in a Krillion",
        100
    )
    DEEP_CUT = D = KrillionCategory(
        Emojis.D,
        "D",
        "Deep Cut",
        85
    )
    RARE = R = KrillionCategory(
        Emojis.R,
        "R",
        "Rare",
        60
    )
    SCHOOLER = S = KrillionCategory(
        Emojis.S,
        "S",
        "Schooler",
        30
    )
    CLEVER = C = KrillionCategory(
        Emojis.C,
        "T",
        "Too Clever",
        15
    )
    PLANKTON = P = KrillionCategory(
        Emojis.P,
        "P",
        "Plankton",
        10
    )
    EMPTY = E = KrillionCategory(
        Emojis.E,
        "N",
        "No Response",
        0
    )

    @staticmethod
    def from_unicode(unicode: str) -> 'AnswerCategories':
        return next(c for c in AnswerCategories if c.value.unicode == unicode)

    @staticmethod
    def from_char(char: str) -> 'AnswerCategories':
        if not isinstance(char, str) and len(char) == 1:
            raise ValueError("from_char must take a string of length 1 only!")
        return next(c for c in AnswerCategories if c.value.letter_code == char)

    @staticmethod
    def from_emoji(emoji: str) -> 'AnswerCategories':
        return next(c for c in AnswerCategories if c.value.emoji == emoji)

    