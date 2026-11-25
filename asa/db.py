"""SQLite store. Single source of truth for the ledger, dashboard and chat."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

import pandas as pd

from .config import DB_PATH, STATE, ts

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    assigned_by TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    title TEXT NOT NULL,
    task_description TEXT NOT NULL,
    kind TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'Medium',
    deadline TEXT,
    status TEXT NOT NULL DEFAULT 'Queued',
    output_link TEXT DEFAULT '',
    blocked_reason TEXT DEFAULT '',
    started_at TEXT DEFAULT '',
    completion_time TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS task_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT, timestamp TEXT, status TEXT, note TEXT
);
CREATE TABLE IF NOT EXISTS applications (
    application_id TEXT PRIMARY KEY, child_ref TEXT, program TEXT, chinese_level TEXT DEFAULT '',
    submitted_at TEXT, child_name TEXT, age INTEGER,
    grade INTEGER, parent_name TEXT, parent_email TEXT, parent_phone TEXT,
    availability TEXT, experience TEXT, consent_data TEXT, consent_photo TEXT,
    source TEXT, data_label TEXT, band TEXT DEFAULT '', status TEXT DEFAULT 'New',
    qa_flags TEXT DEFAULT '', group_id TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS groups (
    group_id TEXT PRIMARY KEY, program TEXT, band TEXT, day TEXT, time TEXT, capacity INTEGER
);
CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY, received_at TEXT, from_email TEXT, subject TEXT,
    body TEXT, data_label TEXT, program TEXT DEFAULT '', category TEXT DEFAULT '', priority TEXT DEFAULT '',
    status TEXT DEFAULT 'New', draft_reply TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS posts (
    post_id TEXT PRIMARY KEY, created_at TEXT, program TEXT DEFAULT '', platform TEXT, title TEXT, body TEXT,
    status TEXT DEFAULT 'Draft', file TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS emails (
    email_id TEXT PRIMARY KEY, created_at TEXT, program TEXT DEFAULT '', kind TEXT, to_addr TEXT, subject TEXT,
    file TEXT, status TEXT DEFAULT 'Draft (not sent)'
);
CREATE TABLE IF NOT EXISTS attendance (
    group_id TEXT, program TEXT, lesson_no INTEGER, lesson_date TEXT, enrolled INTEGER,
    present INTEGER, data_label TEXT, PRIMARY KEY (group_id, lesson_no)
);
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, channel TEXT,
    role TEXT, content TEXT
);
"""


def connect() -> sqlite3.Connection:
    STATE.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


@contextmanager
def session():
    con = connect()
    try:
        yield con
        con.commit()
    finally:
        con.close()


def df(sql: str, params: tuple = ()) -> pd.DataFrame:
    with session() as con:
        return pd.read_sql_query(sql, con, params=params)


def next_id(con: sqlite3.Connection, table: str, col: str, prefix: str) -> str:
    row = con.execute(f"SELECT {col} FROM {table} WHERE {col} LIKE ? ORDER BY {col} DESC LIMIT 1",
                      (prefix + "%",)).fetchone()
    n = int(row[0][len(prefix):]) + 1 if row else 1
    return f"{prefix}{n:04d}"


def save_chat(channel: str, role: str, content: str) -> None:
    with session() as con:
        con.execute("INSERT INTO chat_history (timestamp, channel, role, content) VALUES (?,?,?,?)",
                    (ts(), channel, role, content))
