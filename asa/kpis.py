"""KPI calculations shared by the Analyst, the daily brief, the dashboard and the PM chat."""
from __future__ import annotations

from datetime import timedelta

import pandas as pd

from .config import EMPLOYEE_NAMES, now
from .db import df


def tasks() -> pd.DataFrame:
    t = df("SELECT * FROM tasks ORDER BY task_id")
    for c in ("timestamp", "started_at", "completion_time"):
        t[c] = pd.to_datetime(t[c].replace("", None), errors="coerce")
    return t


def funnel(program: str | None = None) -> dict:
    a = df("SELECT status FROM applications" + (" WHERE program = ?" if program else ""), (program,) if program else ())
    s = a["status"].value_counts().to_dict() if len(a) else {}
    placed = s.get("Scheduled", 0) + s.get("Confirmation drafted", 0)
    return {"Applied": len(a), "Passed QA": len(a) - s.get("Needs fix", 0) - s.get("Duplicate", 0) - s.get("New", 0),
            "Placed in group": placed, "Confirmation drafted": s.get("Confirmation drafted", 0),
            "Waitlist": s.get("Waitlist", 0), "Needs fix": s.get("Needs fix", 0), "Duplicate": s.get("Duplicate", 0)}


def group_fill() -> pd.DataFrame:
    return df("SELECT g.group_id, g.program, g.band, g.day, g.time, g.capacity,"
              " (SELECT COUNT(*) FROM applications a WHERE a.group_id = g.group_id) AS enrolled FROM groups g ORDER BY g.group_id")


def attendance_rate() -> pd.DataFrame:
    a = df("SELECT * FROM attendance")
    if a.empty:
        return a
    a["rate"] = (a["present"] / a["enrolled"]).round(3)
    return a


def per_employee(period_days: int | None = None) -> pd.DataFrame:
    t = tasks()
    if period_days is not None and not t.empty:
        t = t[t["timestamp"] >= pd.Timestamp(now().replace(tzinfo=None) - timedelta(days=period_days))]
    rows = []
    for name in EMPLOYEE_NAMES:
        e = t[t["agent_name"] == name] if not t.empty else t
        done = e[e["status"] == "Completed"] if not e.empty else e
        dur = (done["completion_time"] - done["started_at"]).dt.total_seconds() if not done.empty else pd.Series(dtype=float)
        rows.append({"Employee": name, "Completed": len(done),
                     "In Progress": int((e["status"] == "In Progress").sum()) if not e.empty else 0,
                     "Queued": int((e["status"] == "Queued").sum()) if not e.empty else 0,
                     "Blocked": int((e["status"] == "Blocked").sum()) if not e.empty else 0,
                     "Avg completion (s)": round(float(dur.mean()), 1) if len(dur) else 0.0})
    return pd.DataFrame(rows)


def agency_kpis() -> dict:
    f = funnel()
    g = group_fill()
    att = attendance_rate()
    msgs = df("SELECT status FROM messages")
    posts = df("SELECT platform, created_at FROM posts")
    emails = df("SELECT kind, status FROM emails")
    today = now().strftime("%Y-%m-%d")
    by_prog = {p: funnel(p) for p in ("AI", "ZH")}
    return {
        "applications_total": f["Applied"],
        "requests_ai": by_prog["AI"]["Applied"], "requests_chinese": by_prog["ZH"]["Applied"],
        "placed_ai": by_prog["AI"]["Placed in group"], "placed_chinese": by_prog["ZH"]["Placed in group"],
        "children_in_both": int(df("SELECT COUNT(*) AS n FROM (SELECT child_ref FROM applications WHERE group_id != ''"
                                   " GROUP BY child_ref HAVING COUNT(DISTINCT program) = 2)")["n"][0]),
        "applications_today": int((df("SELECT submitted_at FROM applications")["submitted_at"].str[:10] == today).sum()),
        "placed": f["Placed in group"], "waitlist": f["Waitlist"],
        "qa_issues": f["Needs fix"] + f["Duplicate"],
        "group_fill_pct": round(100 * g["enrolled"].sum() / max(1, g["capacity"].sum()), 1) if len(g) else 0.0,
        "attendance_pct": round(100 * att["present"].sum() / max(1, att["enrolled"].sum()), 1) if len(att) else 0.0,
        "messages_answered": int((msgs["status"] == "Draft reply ready").sum()) if len(msgs) else 0,
        "messages_escalated": int((msgs["status"] == "Escalated to Boss").sum()) if len(msgs) else 0,
        "posts_today": int((posts["created_at"].str[:10] == today).sum()) if len(posts) else 0,
        "email_drafts": int((emails["status"] == "Draft (not sent)").sum()) if len(emails) else 0,
    }
