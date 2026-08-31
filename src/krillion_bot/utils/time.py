from datetime import datetime, timedelta, timezone
import datetime as dt

UTC_MINUS_4 = timezone(timedelta(hours=-4))
MIDNIGHT_EST = dt.time(hour=0, minute=0, second=0, tzinfo=UTC_MINUS_4)

def get_next_utc_4_boundary_from(dt: datetime):
    next_boundary = (dt.date() + timedelta(days=1))
    next_boundary_dt = datetime.combine(
        next_boundary, datetime.min.time(), tzinfo=UTC_MINUS_4
    )
    return next_boundary_dt

def format_datetime_for_discord(dt: datetime):
    return f"<t:{int(dt.timestamp())}:t>"

