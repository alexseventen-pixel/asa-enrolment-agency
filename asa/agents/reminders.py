"""Agent 3. Reminders: for every active enrolment with a lesson tomorrow, prepares a reminder
email to the parent (day, time, group, lesson topic). Run by the button or /api/reminders/run."""
from __future__ import annotations

from datetime import date, timedelta

from ..config import DAY_NAMES, LESSONS, PROGRAMS, TIMETABLE_NOTE, now, ts
from ..db import log, session
from ..mailer import draft
from . import applications as apps

AGENT = "Reminders"


def run(for_date: date | None = None) -> dict:
    target = for_date or (now().date() + timedelta(days=1))
    day = target.strftime("%a")
    made, skipped = [], 0
    if day not in DAY_NAMES:
        log(AGENT, f"Reminders for {target}", f"{target:%A}: no lessons, nothing to send")
        return {"date": str(target), "day": target.strftime("%A"), "created": [], "skipped": 0}
    with session() as con:
        rows = con.execute("SELECT e.*, s.child_name, s.parent_name, s.parent_email FROM enrolments e"
                           " JOIN students s USING (application_id) WHERE e.status = 'Active'").fetchall()
        done = {r["application_id"] + r["subject"] for r in con.execute(
            "SELECT application_id, subject FROM emails WHERE kind = 'Reminder' AND subject LIKE ?", (f"%{target}%",))}
    for e in rows:
        g = apps.group(e["group_id"])
        if g["day"] != day:
            continue
        n = min(e["reminders_sent"] + 1, len(LESSONS[e["program"]]))
        topic = LESSONS[e["program"]][n - 1]
        subject = f"Reminder: {PROGRAMS[e['program']]} tomorrow {target} at {g['time']}"
        if e["application_id"] + subject in done:
            skipped += 1
            continue
        body = (f"<p>Dear {e['parent_name']},</p><p>A friendly reminder: <b>{e['child_name']}</b> has "
                f"<b>{PROGRAMS[e['program']]}</b> tomorrow, {DAY_NAMES[day]} {target:%d.%m}, at <b>{g['time']}</b> "
                f"(group {g['group_id']}).</p><p>Lesson {n}: <b>{topic}</b>.</p>"
                f"<p>If your child cannot come, just reply to this email. {TIMETABLE_NOTE}</p><p>ASA team</p>")
        eid = draft(AGENT, "Reminder", e["application_id"], e["parent_email"], subject, body)
        with session() as con:
            con.execute("UPDATE enrolments SET reminders_sent = ?, updated_at = ? WHERE enrolment_id = ?", (n, ts(), e["enrolment_id"]))
        made.append({"email_id": eid, "application_id": e["application_id"], "child": e["child_name"],
                     "program": PROGRAMS[e["program"]], "group": g["group_id"], "time": g["time"], "lesson": f"{n}. {topic}"})
    log(AGENT, f"Reminders for {target:%A} {target}", f"{len(made)} reminder(s) drafted, {skipped} already done")
    return {"date": str(target), "day": target.strftime("%A"), "created": made, "skipped": skipped}
