from datetime import datetime, timezone

from krillion_bot.utils import current_game_number
from krillion_bot.utils.time import (
    EASTERN_TIMEZONE,
    get_next_eastern_boundary_from,
)


def test_current_game_number_changes_at_eastern_midnight_in_standard_time():
    before_midnight = datetime(2026, 11, 2, 4, 59, tzinfo=timezone.utc)
    after_midnight = datetime(2026, 11, 2, 5, 0, tzinfo=timezone.utc)

    assert current_game_number(after_midnight) == current_game_number(before_midnight) + 1


def test_eastern_midnight_boundary_uses_daylight_and_standard_offsets():
    before_fall_transition = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)
    after_fall_transition = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)

    daylight_boundary = get_next_eastern_boundary_from(before_fall_transition)
    standard_boundary = get_next_eastern_boundary_from(after_fall_transition)

    assert daylight_boundary.utcoffset().total_seconds() == -4 * 60 * 60
    assert standard_boundary.utcoffset().total_seconds() == -5 * 60 * 60
    assert daylight_boundary.tzinfo is EASTERN_TIMEZONE
    assert standard_boundary.tzinfo is EASTERN_TIMEZONE
