from __future__ import annotations

from datetime import date, timedelta

from .config import CLUB_START

DAY_IDX = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4}


def lesson_date(day: str, lesson_no: int) -> date:
    start = date.fromisoformat(CLUB_START)
    first = start + timedelta(days=(DAY_IDX[day] - start.weekday()) % 7)
    return first + timedelta(weeks=lesson_no - 1)


def next_lesson(day: str, today: date) -> tuple[int, date] | None:
    for n in range(1, 11):
        d = lesson_date(day, n)
        if d >= today:
            return n, d
    return None
