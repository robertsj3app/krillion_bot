from enum import StrEnum
from typing import Self

class Emojis(StrEnum):
    '''
    Enum of the emoji symbols used by the Krillion game.
    
    The bot uses these values to map between the visual emoji text pasted in Discord and the
    normalized category metadata used in scoring logic.
    '''

    KRILLION = K = "🌟"
    DEEP_CUT = D = "🏮"
    RARE     = R = "🦑"
    SCHOOLER = S = "🐟"
    CLEVER   = C = "🤡"
    PLANKTON = P = "🫧"
    EMPTY    = E = "⬛"

    def to_unicode(self: Self) -> str:
        '''
        Convert the emoji to a Python-style escaped Unicode sequence.
        
        Returns:
            str:
                The emoji encoded as a backslash escape string.
        '''
        return self.strip().encode('ascii', errors='backslashreplace').decode('ascii')

    @staticmethod
    def from_unicode(unicode: str) -> 'Emojis':
        '''
        Reverse a stored Unicode escape back into an Emojis enum member.
        
        Args:
            unicode (str):
                A string like "\\U0001f31f" that names an emoji.
        
        Returns:
            Emojis:
                The matching emoji enum value.
        '''
        return next(e for e in Emojis if unicode.encode("utf-8").decode("unicode-escape") == e.value)