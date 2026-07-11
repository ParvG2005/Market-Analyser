from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from app.ingest.nse_calendar import is_in_session, is_trading_day, session_window

IST = ZoneInfo("Asia/Kolkata")


@pytest.mark.parametrize(
    "day,expected",
    [
        (date(2025, 1, 26), False),   # Republic Day (NSE holiday)
        (date(2025, 8, 15), False),   # Independence Day (NSE holiday)
        (date(2025, 12, 25), False),  # Christmas (NSE holiday)
        (date(2025, 6, 7), False),    # Saturday
        (date(2025, 6, 8), False),    # Sunday
        (date(2025, 6, 9), True),     # ordinary Monday trading day
    ],
)
def test_is_trading_day(day: date, expected: bool) -> None:
    assert is_trading_day(day) is expected


def test_session_window_bounds() -> None:
    open_dt, close_dt = session_window(date(2025, 6, 9))
    assert open_dt == datetime(2025, 6, 9, 9, 15, tzinfo=IST)
    assert close_dt == datetime(2025, 6, 9, 15, 30, tzinfo=IST)


@pytest.mark.parametrize(
    "dt,expected",
    [
        (datetime(2025, 6, 9, 9, 14, tzinfo=IST), False),
        (datetime(2025, 6, 9, 9, 15, tzinfo=IST), True),
        (datetime(2025, 6, 9, 12, 0, tzinfo=IST), True),
        (datetime(2025, 6, 9, 15, 30, tzinfo=IST), True),
        (datetime(2025, 6, 9, 15, 31, tzinfo=IST), False),
        (datetime(2025, 1, 26, 11, 0, tzinfo=IST), False),  # holiday, mid-day
    ],
)
def test_is_in_session(dt: datetime, expected: bool) -> None:
    assert is_in_session(dt) is expected
