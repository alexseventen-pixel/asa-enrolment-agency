"""Shared settings for the ASA Enrolment Agency (AI + Chinese)."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SAMPLE = DATA / "sample"
WORK = Path(os.environ.get("ASA_WORKDIR", ROOT))  # where outputs go (tests use a temp dir)
STATE = WORK / "state"
OUTBOX = WORK / "outbox"
REPORTS = WORK / "reports"
EXPORTS = WORK / "exports"
DB_PATH = Path(os.environ.get("ASA_DB", STATE / "agency.db"))
TZ = ZoneInfo("Europe/Riga")

AGENCY_NAME = "ASA Enrolment Agency (AI + Chinese)"
CLIENT = "After-school activities (ASA): AI Club and Chinese classes, International School Premjers, Riga"
BOSS_NAME = os.environ.get("ASA_BOSS_NAME", "Oleg Mishchenko")
BOSS_EMAIL = os.environ.get("ASA_BOSS_EMAIL", "alexseventen@gmail.com")
CLUB_EMAIL = os.environ.get("ASA_CLUB_EMAIL", "alexseventen@gmail.com")

SYNTHETIC_LABEL = "SYNTHETIC SAMPLE DATA (no real children or parents)"

PROGRAMS = {"AI": "AI Club", "ZH": "Chinese"}
CHINESE_LEVELS = ["Beginner", "HSK1", "HSK2", "HSK3"]

# Group slots per program. "band" is an age band for AI and a level band for Chinese.
GROUP_CAPACITY = {"AI": 12, "ZH": 8}
SLOTS = [
    {"group_id": "AI-1", "program": "AI", "band": "7-9", "day": "Mon", "time": "15:30"},
    {"group_id": "AI-2", "program": "AI", "band": "7-9", "day": "Wed", "time": "15:30"},
    {"group_id": "AI-3", "program": "AI", "band": "10-12", "day": "Tue", "time": "16:00"},
    {"group_id": "AI-4", "program": "AI", "band": "10-12", "day": "Thu", "time": "16:00"},
    {"group_id": "AI-5", "program": "AI", "band": "13-15", "day": "Fri", "time": "15:00"},
    {"group_id": "ZH-1", "program": "ZH", "band": "Beginner 7-10", "day": "Tue", "time": "15:30"},
    {"group_id": "ZH-2", "program": "ZH", "band": "Beginner 7-10", "day": "Thu", "time": "15:30"},
    {"group_id": "ZH-3", "program": "ZH", "band": "Beginner 11-15", "day": "Mon", "time": "16:30"},
    {"group_id": "ZH-4", "program": "ZH", "band": "HSK1", "day": "Wed", "time": "16:30"},
    {"group_id": "ZH-5", "program": "ZH", "band": "HSK2-3", "day": "Fri", "time": "16:00"},
]

LESSONS = {
    "AI": [
        (1, "Where AI Hides", "Spot AI in everyday apps, games and devices."),
        (2, "Teaching a Machine to See", "Train an image classifier with your own photos."),
        (3, "Bad Data, Bad AI", "How biased or messy data breaks a model."),
        (4, "How a Chatbot Thinks", "Prompts, tokens and why chatbots make mistakes."),
        (5, "AI Artist and Composer", "Make pictures and music with AI, and talk about authorship."),
        (6, "Deepfakes and Online Safety", "Recognise fakes and protect your data."),
        (7, "Playing Games with AI", "Build a small game that learns from the player."),
        (8, "Build Your Own AI Helper", "Design a simple assistant for a real school task."),
        (9, "From Problem to Product", "Turn an idea into a prototype and a pitch."),
        (10, "Mini Demo Day", "Teams present their projects to parents."),
    ],
    # DRAFT topic list for the demo. The teacher replaces it with the real Chinese syllabus.
    "ZH": [
        (1, "Hello! 你好", "Greetings, names and the four tones."),
        (2, "Numbers 1 to 100", "Counting games, ages and phone numbers."),
        (3, "My Family", "Family words and simple sentences."),
        (4, "Colours and Animals", "Describe animals and colours with picture cards."),
        (5, "Food and Drinks", "Order food and say what you like."),
        (6, "My School Day", "Days of the week, time and school subjects."),
        (7, "Characters Workshop", "Stroke order and first characters."),
        (8, "Hobbies and Sports", "Talk about what you like to do."),
        (9, "Chinese Festivals", "Spring Festival traditions, songs and crafts."),
        (10, "Show and Tell", "Short performances for parents."),
    ],
}

EMPLOYEES = [
    {"slug": "project-manager", "name": "Project Manager", "title": "Chief of Staff"},
    {"slug": "intake-officer", "name": "Intake Officer", "title": "Applications Intake (AI + Chinese)"},
    {"slug": "scheduler", "name": "Scheduler", "title": "Groups and Clash-free Timetable"},
    {"slug": "communications", "name": "Communications Officer", "title": "Parent Emails"},
    {"slug": "parent-support", "name": "Parent Support", "title": "FAQ and Triage"},
    {"slug": "content-writer", "name": "Content Writer", "title": "Posts and Poster Copy"},
    {"slug": "analyst", "name": "Analyst", "title": "Dashboards and KPIs"},
    {"slug": "qa-auditor", "name": "QA Auditor", "title": "Data Quality and Consent"},
]
EMPLOYEE_NAMES = [e["name"] for e in EMPLOYEES]


def now() -> datetime:
    return datetime.now(TZ).replace(microsecond=0)


def ts(dt: datetime | None = None) -> str:
    return (dt or now()).strftime("%Y-%m-%d %H:%M:%S")

# Demo timeline: first week of lessons. Placeholder until the Boss confirms the real start date.
CLUB_START = os.environ.get("ASA_CLUB_START", "2026-11-16")
CLUB_VENUE = os.environ.get("ASA_CLUB_VENUE", "International School Premjers, Riga (room to be confirmed)")

