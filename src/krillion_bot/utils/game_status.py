from datetime import datetime

ANCHOR = (datetime(2026, 8, 30, 0, 0), 46)

def current_game_number():
    '''
    Determine the active Krillion game number for the current date.
    
    The game is anchored to the first known daily dive and increments by one for each day
    after that timestamp. This lets the bot compare results against the current server day.
    
    Returns:
        int:
            The current game number according to the configured anchor.
    '''
    num_days_diff = (datetime.now() - ANCHOR[0]).days
    return ANCHOR[1] + num_days_diff