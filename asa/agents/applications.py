"""Agent 1. Applications: saves each application, places the child in a group (or waitlist)
and generates the auto-reply confirmation email immediately."""
from __future__ import annotations

import re

from ..config import DAY_NAMES, DAYS, GROUPS, LEVELS, PROGRAMS, TIMETABLE_NOTE, ts
from ..db import log, next_id, session
from ..mailer import draft

AGENT = "Applications"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
PROGRAM_IN = {"ai": ["AI"], "ai club": ["AI"], "chinese": ["ZH"], "both": ["AI", "ZH"]}


def band(program: str, age: int, level: str) -> str:
    if program == "AI":
        return "7-9" if age <= 9 else "10-12" if age <= 12 else "13-15"
    if level == "Beginner":
        return "Beginner 7-10" if age <= 10 else "Beginner 11-15"
    return "HSK1" if level == "HSK1" else "HSK2-3"


def validate(d: dict) -> list[str]:
    errors = []
    for k, label in (("parent_name", "Parent name"), ("parent_email", "Parent email"), ("child_name", "Child name")):
        if not str(d.get(k, "")).strip():
            errors.append(f"{label} is required.")
    if d.get("parent_email") and not EMAIL_RE.match(d["parent_email"]):
        errors.append("Please enter a valid email address.")
    try:
        if not 7 <= int(d.get("age", 0)) <= 15:
            errors.append("The programmes are for ages 7 to 15.")
    except (TypeError, ValueError):
        errors.append("Please enter the child's age.")
    if str(d.get("program", "")).lower() not in PROGRAM_IN:
        errors.append("Please choose a programme.")
    elif "ZH" in PROGRAM_IN[str(d["program"]).lower()] and d.get("level") not in LEVELS:
        errors.append("Please choose a Chinese level.")
    if not [x for x in d.get("days", []) if x in DAYS]:
        errors.append("Please choose at least one preferred day.")
    if not d.get("consent"):
        errors.append("Consent is needed to process the application.")
    return errors


def place(con, application_id: str, program: str, band_: str, days: list[str], exclude_enrolment: str = "") -> str:
    """Pick the least full group for this programme and band on a preferred day,
    never on a day the child already has another activity."""
    busy = {group(r["group_id"])["day"] for r in con.execute(
        "SELECT group_id FROM enrolments WHERE application_id = ? AND status = 'Active' AND enrolment_id != ?",
        (application_id, exclude_enrolment))}
    best, best_fill = "", None
    for g in GROUPS:
        if g["program"] != program or g["band"] != band_ or g["day"] not in days or g["day"] in busy:
            continue
        fill = con.execute("SELECT COUNT(*) FROM enrolments WHERE group_id = ? AND status = 'Active'", (g["group_id"],)).fetchone()[0]
        if fill < g["capacity"] and (best_fill is None or fill < best_fill):
            best, best_fill = g["group_id"], fill
    return best


def group(gid: str) -> dict:
    return next(g for g in GROUPS if g["group_id"] == gid)


def enrolment_lines(con, application_id: str) -> str:
    items = []
    for e in con.execute("SELECT * FROM enrolments WHERE application_id = ? ORDER BY program", (application_id,)):
        name = PROGRAMS[e["program"]] + (f" ({e['level']})" if e["level"] else "")
        if e["status"] == "Active":
            g = group(e["group_id"])
            items.append(f"<li><b>{name}</b>: group {g['group_id']}, every {DAY_NAMES[g['day']]} at {g['time']}</li>")
        elif e["status"] == "Waitlist":
            items.append(f"<li><b>{name}</b>: waiting list (groups on your days are full). We will write when a place opens.</li>")
        else:
            items.append(f"<li><b>{name}</b>: cancelled</li>")
    return "<ul>" + "".join(items) + "</ul>"


def submit(d: dict, source: str = "Web form") -> dict:
    """Save an application, place it, draft the auto-reply. Returns a summary."""
    programs = PROGRAM_IN[str(d["program"]).lower()]
    days = [x for x in DAYS if x in d.get("days", [])]
    age = int(d["age"])
    label = "TEST" if d.get("test") else ("DEMO" if source == "Demo data" else "REAL")
    with session() as con:
        app_id = next_id(con, "students", "application_id", "ASA-")
        con.execute("INSERT INTO students VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (app_id, ts(), d["child_name"].strip(), age, d.get("grade", ""), d["parent_name"].strip(),
                     d["parent_email"].strip(), d.get("parent_phone", ""), ";".join(days), d.get("notes", ""),
                     "yes" if d.get("consent_photo") else "no", source, label))
        results = []
        for p in programs:
            level = d.get("level", "") if p == "ZH" else ""
            b = band(p, age, level)
            gid = place(con, app_id, p, b, days)
            status = "Active" if gid else "Waitlist"
            eid = f"{app_id}-{p}"
            con.execute("INSERT INTO enrolments VALUES (?,?,?,?,?,?,?,0,?)", (eid, app_id, p, level, b, gid, status, ts()))
            results.append({"program": PROGRAMS[p], "group": gid, "day": group(gid)["day"] if gid else "", "status": status})
        lines = enrolment_lines(con, app_id)
    first = d["child_name"].strip().split()[0]
    body = (f"<p>Dear {d['parent_name'].strip()},</p><p>Thank you! We received the application for <b>{d['child_name'].strip()}</b>. "
            f"Your application ID is <b>{app_id}</b>.</p>{lines}<p>{TIMETABLE_NOTE} To change or cancel, reply to this email "
            f"or use the chat on our page with your email and application ID.</p><p>We look forward to seeing {first}!<br>ASA team</p>")
    email_id = draft(AGENT, "Auto-reply", app_id, d["parent_email"].strip(), f"Application {app_id} received: {d['child_name'].strip()}", body)
    log(AGENT, f"New application {app_id} ({source})",
        "; ".join(f"{r['program']}: {r['group'] or 'waitlist'}" for r in results) + f". Auto-reply {email_id} drafted")
    return {"application_id": app_id, "enrolments": results, "email_id": email_id}
