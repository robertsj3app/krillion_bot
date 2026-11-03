from datetime import date, datetime

from krillion_bot.utils.time import EASTERN_TIMEZONE

ANCHOR = (date(2026, 8, 30), 46)


def current_game_number(now: datetime | None = None):
    '''
    Determine the active Krillion game number for the current Eastern date.
    
    The game is anchored to the first known daily dive and increments by one for each day
    after that date. An optional timestamp can be supplied for deterministic calculations.
    
    Returns:
        int:
            The current game number according to the configured anchor.
    '''
    if now is None:
        now = datetime.now(EASTERN_TIMEZONE)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=EASTERN_TIMEZONE)
    else:
        now = now.astimezone(EASTERN_TIMEZONE)

    num_days_diff = (now.date() - ANCHOR[0]).days
    return ANCHOR[1] + num_days_diff
