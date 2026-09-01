from dataclasses import dataclass, field
from typing import Sequence, Self, TypeVar
import re
from textwrap import dedent
from krillion_bot.utils import AnswerCategories, KrillionCategory

T = TypeVar('T')
DatabaseRowType = tuple[int, int, int, str, int, int, int, int, int, int, int, int, int, str, str]

@dataclass
class KrillionResult:
    '''
    Parsed container for a single Krillion.io result.
    
    The game exports a short formatted block containing the game number, total score, and
    seven answer emoji values. This dataclass translates that block into a normalized object
    that can be validated, counted, and rendered back to Discord-friendly emoji text.
    
    Attributes:
        game_number (int):
            The numbered daily dive that the result belongs to.
        score (int):
            The total score printed by the game for this answer set.
        answers (Sequence[KrillionCategory]):
            The seven answer categories that make up the result.
        krillions (int):
            Number of One in a Krillion answers in the result.
        deep_cuts (int):
            Number of Deep Cut answers in the result.
        rares (int):
            Number of Rare answers in the result.
        schoolers (int):
            Number of Schooler answers in the result.
        clevers (int):
            Number of Too Clever answers in the result.
        planktons (int):
            Number of Plankton answers in the result.
        empties (int):
            Number of empty/No Response answers in the result.
    '''

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
        '''
        Count each answer category after initialization.
        
        Returns:
            None
        '''
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
        '''
        Return the original answer sequence as a contiguous emoji string.
        
        Returns:
            str:
                The emoji representation of all answer categories in order.
        '''
        return ''.join(a.as_emoji() for a in self.answers)

    @property
    def valid(self: Self) -> bool:
        '''
        Check whether the parsed answer values add up to the declared score.
        
        Returns:
            bool:
                True when the total score matches the answer-value sum, False otherwise.
        '''
        return sum(a.score for a in self.answers) == self.score

    @staticmethod
    def from_result_string(result: str) -> 'KrillionResult':
        '''
        Parse a raw Krillion "Copy Results" block into a structured result object.
        
        Args:
            result (str):
                The pasted text copied directly from the Krillion result modal.
        
        Returns:
            KrillionResult:
                A result object built from the game number, score, and answer sequence.
        
        Raises:
            ValueError:
                If the content is not in the expected Krillion result format.
        '''
        decoded = dedent(result.strip().encode('ascii', errors='backslashreplace').decode('ascii'))
        match = re.match(KrillionResult.FORMAT, decoded)
        if match:
            game_number, score, *answers_unicode = match.groups()
            return KrillionResult(int(game_number), int(score), [AnswerCategories.from_unicode(u).value for u in answers_unicode])
        else:
            raise ValueError('Tried to create KrillionResult from invalid string. Check formatting and make sure to paste exactly the result of selecting "Copy Results".')
    
    @staticmethod
    def from_database_row(row: DatabaseRowType):
        '''
        Reconstruct a KrillionResult from a row stored by the database handler.
        
        Args:
            row (DatabaseRowType):
                A tuple matching the schema of a krillionResults database row.
        
        Returns:
            KrillionResult:
                A result object rebuilt from the serialized answer text.
        '''
        _, _, _, _, game_number, score, _, _, _, _, _, _, _, answers_str, _, = row
        return KrillionResult(game_number, score, [AnswerCategories.from_char(c).value for c in answers_str])