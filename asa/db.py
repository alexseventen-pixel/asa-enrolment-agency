"""SQLite store shared by the 4 agents, the dashboard and the landing page."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

import pandas as pd

from .config import DB_PATH, STATE, ts

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    application_id TEXT PRIMARY KEY, created_at TEXT, child_name TEXT, age INTEGER, grade TEXT,
    parent_name TEXT, parent_email TEXT, parent_phone TEXT, days TEXT, notes TEXT,
    consent_photo TEXT, source TEXT, label TEXT
);
CREATE TABLE IF NOT EXISTS enrolments (
    enrolment_id TEXT PRIMARY KEY, application_id TEXT, program TEXT, level TEXT, band TEXT,
    group_id TEXT DEFAULT '', status TEXT, reminders_sent INTEGER DEFAULT 0, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS emails (
    email_id TEXT PRIMARY KEY, created_at TEXT, agent TEXT, kind TEXT, application_id TEXT,
    to_addr TEXT, subject TEXT, html TEXT, file TEXT, status TEXT
);
CREATE TABLE IF NOT EXISTS invoices (
    invoice_no TEXT PRIMARY KEY, issued_at TEXT, application_id TEXT, enrolment_id TEXT, program TEXT,
    period TEXT, amount REAL, status TEXT, paid_at TEXT DEFAULT '',
    lessons INTEGER DEFAULT 0, unit_price REAL DEFAULT 0, note TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT, agent TEXT, action TEXT, result TEXT
);
CREATE TABLE IF NOT EXISTS chats (
    session_id TEXT PRIMARY KEY, state TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, time TEXT, role TEXT, text TEXT
);
"""


def connect() -> sqlite3.Connection:
    STATE.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    cols = {r[1] for r in con.execute("PRAGMA table_info(invoices)")}
    for col, typ in (("lessons", "INTEGER DEFAULT 0"), ("unit_price", "REAL DEFAULT 0"), ("note", "TEXT DEFAULT ''")):
        if col not in cols:
            con.execute(f"ALTER TABLE invoices ADD COLUMN {col} {typ}")
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


def next_id(con, table: str, col: str, prefix: str, width: int = 4) -> str:
    row = con.execute(f"SELECT {col} FROM {table} WHERE {col} LIKE ? ORDER BY {col} DESC LIMIT 1", (prefix + "%",)).fetchone()
    n = int(row[0][len(prefix):]) + 1 if row else 1
    return f"{prefix}{n:0{width}d}"


def log(agent: str, action: str, result: str) -> None:
    """The ledger: time, agent, action, result."""
    with session() as con:
        con.execute("INSERT INTO ledger (time, agent, action, result) VALUES (?,?,?,?)", (ts(), agent, action, result))


def reset() -> None:
    DB_PATH.unlink(missing_ok=True)
