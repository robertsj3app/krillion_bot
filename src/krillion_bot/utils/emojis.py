from enum import StrEnum
from typing import Self

class Emojis(StrEnum):

    KRILLION = K = "🌟"
    DEEP_CUT = D = "🦑"
    RARE     = R = "🏮"
    SCHOOLER = S = "🐟"
    CLEVER   = C = "🤡"
    PLANKTON = P = "🫧"
    EMPTY    = E = "⬛"

    def to_unicode(self: Self) -> str:
        return self.strip().encode('ascii', errors='backslashreplace').decode('ascii')

    @staticmethod
    def from_unicode(unicode: str) -> 'Emojis':
        return next(e for e in Emojis if unicode.encode("utf-8").decode("unicode-escape") == e.value)