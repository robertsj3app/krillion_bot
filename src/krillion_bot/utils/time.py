from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

EASTERN_TIMEZONE = ZoneInfo("America/New_York")
MIDNIGHT_EASTERN = time(hour=0, minute=0, second=0, tzinfo=EASTERN_TIMEZONE)


def get_next_eastern_boundary_from(dt: datetime):
    '''
    Compute the next midnight boundary in the Eastern time zone.
    
    Args:
        dt (datetime):
            The reference time to anchor the next rollover from.
    
    Returns:
        datetime:
            The next midnight timestamp in the Eastern time zone.
    '''
    eastern_dt = (
        dt.replace(tzinfo=EASTERN_TIMEZONE)
        if dt.tzinfo is None
        else dt.astimezone(EASTERN_TIMEZONE)
    )
    next_boundary = eastern_dt.date() + timedelta(days=1)
    return datetime.combine(next_boundary, time.min, tzinfo=EASTERN_TIMEZONE)

def format_datetime_for_discord(dt: datetime):
    '''
    Format a datetime for Discord's timestamp markdown syntax.
    
    Args:
        dt (datetime):
            The datetime to convert to a Discord-friendly short timestamp.
    
    Returns:
        str:
            A Discord timestamp snippet such as "\\<t:1700000000:t\\>".
    '''
    return f"<t:{int(dt.timestamp())}:t>"
