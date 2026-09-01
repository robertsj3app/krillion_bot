from dataclasses import dataclass
from typing import Self
from enum import Enum
from .emojis import Emojis

@dataclass(frozen=True)
class KrillionCategory:
    '''
    Metadata for a single Krillion answer bucket.
    
    Each category maps a specific emoji to a score and a readable label. The bot uses these
    objects to verify pasted results, count scores, and render player answers back to Discord.
    
    Attributes:
        emoji (Emojis):
            The emoji used by Krillion to represent a response category.
        letter_code (str):
            Short, one-character code used in persisted database strings.
        category (str):
            Human-readable bucket name.
        score (int):
            Numeric score attached to the category.
    '''

    emoji: Emojis
    # unicode: str
    letter_code: str
    category: str
    score: int

    @property
    def unicode(self) -> str:
        '''
        Return the escaped Unicode representation of this category's emoji.
        
        Returns:
            str:
                The emoji encoded as a Python-style Unicode escape string.
        '''
        return self.emoji.to_unicode()

    def __repr__(self):
        '''
        Return a compact debug representation of this category.
        
        Returns:
            str:
                A readable summary containing the category label.
        '''
        return f'KrillionCategory({self.category})'

    def as_emoji(self: Self):
        '''
        Return the emoji value associated with this category.
        
        Returns:
            Emojis:
                The category's display emoji.
        '''
        return self.emoji

class AnswerCategories(Enum):
    '''
    Enum of all valid Krillion answer categories and their scoring metadata.
    
    These values are used both for parsing pasted data and for counting answer totals in a
    result.
    '''

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
        '''
        Find a category by its escaped Unicode representation.
        
        Args:
            unicode (str):
                The escaped Unicode value such as "\\U0001f31f".
        
        Returns:
            AnswerCategories:
                The matching enum value.
        '''
        return next(c for c in AnswerCategories if c.value.unicode == unicode)

    @staticmethod
    def from_char(char: str) -> 'AnswerCategories':
        '''
        Find a category by its stored one-character database code.
        
        Args:
            char (str):
                The single-letter code for the category.
        
        Returns:
            AnswerCategories:
                The matching enum value.
        
        Raises:
            ValueError:
                If the input is not a valid one-character string.
        '''
        if not isinstance(char, str) and len(char) == 1:
            raise ValueError("from_char must take a string of length 1 only!")
        return next(c for c in AnswerCategories if c.value.letter_code == char)

    @staticmethod
    def from_emoji(emoji: str) -> 'AnswerCategories':
        '''
        Find a category by its concrete emoji character.
        
        Args:
            emoji (str):
                The rendered emoji string for the category.
        
        Returns:
            AnswerCategories:
                The matching enum value.
        '''
        return next(c for c in AnswerCategories if c.value.emoji == emoji)

    