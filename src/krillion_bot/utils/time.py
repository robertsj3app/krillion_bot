from datetime import datetime, timedelta, timezone
import datetime as dt

UTC_MINUS_4 = timezone(timedelta(hours=-4))
MIDNIGHT_EST = dt.time(hour=0, minute=0, second=0, tzinfo=UTC_MINUS_4)

def get_next_utc_4_boundary_from(dt: datetime):
    '''
    Compute the next midnight boundary in UTC-4 time.
    
    Args:
        dt (datetime):
            The reference time to anchor the next rollover from.
    
    Returns:
        datetime:
            The next midnight timestamp in the server's UTC-4 timezone.
    '''
    next_boundary = (dt.date() + timedelta(days=1))
    next_boundary_dt = datetime.combine(
        next_boundary, datetime.min.time(), tzinfo=UTC_MINUS_4
    )
    return next_boundary_dt

def format_datetime_for_discord(dt: datetime):
    '''
    Format a datetime for Discord's timestamp markdown syntax.
    
    Args:
        dt (datetime):
            The datetime to convert to a Discord-friendly short timestamp.
    
    Returns:
        str:
            A Discord timestamp snippet such as "<t:1700000000:t>".
    '''
    return f"<t:{int(dt.timestamp())}:t>"

