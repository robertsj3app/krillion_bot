from datetime import datetime

ANCHOR = (datetime(2026, 8, 30, 0, 0), 46)

def current_game_number():
    num_days_diff = (datetime.now() - ANCHOR[0]).days
    return ANCHOR[1] + num_days_diff