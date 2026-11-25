"""All settings in one place. Values marked TBC are placeholders to be confirmed by the school."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
WORK = Path(os.environ.get("ASA_WORKDIR", ROOT))
STATE = WORK / "state"
OUTBOX = WORK / "outbox"
DB_PATH = Path(os.environ.get("ASA_DB", STATE / "asa.db"))
TZ = ZoneInfo("Europe/Riga")

AGENCY_NAME = "ASA Enrolment Agency"
SCHOOL = "International School Premjers, Riga"
CLUB_EMAIL = os.environ.get("ASA_CLUB_EMAIL", "alexseventen@gmail.com")
CURRENCY = "EUR"

AGENTS = ["Applications", "Support", "Reminders", "Accountant"]

PROGRAMS = {"AI": "AI Club", "ZH": "Chinese"}

# Monthly fees: PLACEHOLDERS, to be confirmed by the school.
PRICES = {"AI": float(os.environ.get("ASA_PRICE_AI", "45")), "ZH": float(os.environ.get("ASA_PRICE_ZH", "40"))}
PRICES_CONFIRMED = os.environ.get("ASA_PRICES_CONFIRMED", "no").lower() == "yes"
PRICE_NOTE = "" if PRICES_CONFIRMED else " (placeholder, to be confirmed)"

# Groups: days and times are a draft timetable, to be confirmed.
GROUPS = [
    {"group_id": "AI-1", "program": "AI", "band": "7-9", "day": "Mon", "time": "15:30", "capacity": 12},
    {"group_id": "AI-2", "program": "AI", "band": "7-9", "day": "Wed", "time": "15:30", "capacity": 12},
    {"group_id": "AI-3", "program": "AI", "band": "10-12", "day": "Tue", "time": "16:00", "capacity": 12},
    {"group_id": "AI-4", "program": "AI", "band": "10-12", "day": "Thu", "time": "16:00", "capacity": 12},
    {"group_id": "AI-5", "program": "AI", "band": "13-15", "day": "Fri", "time": "15:00", "capacity": 12},
    {"group_id": "ZH-1", "program": "ZH", "band": "Beginner 7-10", "day": "Tue", "time": "15:30", "capacity": 8},
    {"group_id": "ZH-2", "program": "ZH", "band": "Beginner 7-10", "day": "Thu", "time": "15:30", "capacity": 8},
    {"group_id": "ZH-3", "program": "ZH", "band": "Beginner 11-15", "day": "Mon", "time": "16:30", "capacity": 8},
    {"group_id": "ZH-4", "program": "ZH", "band": "HSK1", "day": "Wed", "time": "16:30", "capacity": 8},
    {"group_id": "ZH-5", "program": "ZH", "band": "HSK2-3", "day": "Fri", "time": "16:00", "capacity": 8},
]
TIMETABLE_NOTE = "Draft timetable, to be confirmed."
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
DAY_NAMES = {"Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday", "Thu": "Thursday", "Fri": "Friday"}
LEVELS = ["Beginner", "HSK1", "HSK2-3"]

LESSONS = {
    "AI": ["Where AI Hides", "Teaching a Machine to See", "Bad Data, Bad AI", "How a Chatbot Thinks",
           "AI Artist and Composer", "Deepfakes and Online Safety", "Playing Games with AI",
           "Build Your Own AI Helper", "From Problem to Product", "Mini Demo Day"],
    # Draft topics, the teacher replaces them with the real syllabus.
    "ZH": ["Hello! 你好", "Numbers 1 to 100", "My Family", "Colours and Animals", "Food and Drinks",
           "My School Day", "Characters Workshop", "Hobbies and Sports", "Chinese Festivals", "Show and Tell"],
}


def now() -> datetime:
    return datetime.now(TZ).replace(microsecond=0)


def ts(dt: datetime | None = None) -> str:
    return (dt or now()).strftime("%Y-%m-%d %H:%M:%S")
