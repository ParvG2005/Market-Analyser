from datetime import date, datetime, time
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

SESSION_OPEN = time(9, 15)
SESSION_CLOSE = time(15, 30)

# NSE trading holidays (add per calendar year as published by NSE).
NSE_HOLIDAYS: set[date] = {
    date(2025, 1, 26),   # Republic Day
    date(2025, 3, 14),   # Holi
    date(2025, 3, 31),   # Eid-Ul-Fitr
    date(2025, 4, 10),   # Mahavir Jayanti
    date(2025, 4, 14),   # Dr. Ambedkar Jayanti
    date(2025, 4, 18),   # Good Friday
    date(2025, 5, 1),    # Maharashtra Day
    date(2025, 8, 15),   # Independence Day
    date(2025, 8, 27),   # Ganesh Chaturthi
    date(2025, 10, 2),   # Gandhi Jayanti / Dussehra
    date(2025, 10, 21),  # Diwali Laxmi Pujan
    date(2025, 10, 22),  # Diwali Balipratipada
    date(2025, 11, 5),   # Guru Nanak Jayanti
    date(2025, 12, 25),  # Christmas
}


def is_trading_day(day: date) -> bool:
    if day.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    return day not in NSE_HOLIDAYS


def session_window(day: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(day, SESSION_OPEN, tzinfo=IST),
        datetime.combine(day, SESSION_CLOSE, tzinfo=IST),
    )


def is_in_session(dt: datetime) -> bool:
    local = dt.astimezone(IST)
    if not is_trading_day(local.date()):
        return False
    open_dt, close_dt = session_window(local.date())
    return open_dt <= local <= close_dt
