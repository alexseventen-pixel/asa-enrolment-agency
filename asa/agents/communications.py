"""Communications Officer: drafts confirmation, waitlist and reminder emails per program.

Drafts only. Sending is a separate task that stays Blocked until the Boss approves.
"""
from __future__ import annotations

from ..bridges.email_bridge import draft_email
from ..config import AGENCY_NAME, CLUB_VENUE, LESSONS, PROGRAMS, now
from ..db import session
from ..schedule_utils import lesson_date, next_lesson

STYLE = "font-family:Arial,sans-serif;color:#1d2433;max-width:620px"
FOOT = f'<p style="color:#888;font-size:11px">Prepared by {AGENCY_NAME}. Sample data, demo only.</p></div>'
INTRO = {
    "AI": "The AI Club has 10 lessons and ends with a Mini Demo Day for parents. No experience is needed.",
    "ZH": "The Chinese class works in small groups by level. Your child learns through games, songs and characters.",
}
TEAM = {"AI": "AI Club team", "ZH": "Chinese class team"}


def _group_line(g) -> str:
    return f"{g['band']}" if g["program"] == "ZH" else f"ages {g['band']}"


def _confirmation(a, g) -> str:
    p = a["program"]
    first = lesson_date(g["day"], 1)
    return f"""<div style="{STYLE}"><p>Dear {a['parent_name']},</p>
<p>Thank you for registering <b>{a['child_name']}</b> for <b>{PROGRAMS[p]}</b> (after-school activities). We are happy to confirm a place:</p>
<ul><li>Group: <b>{g['group_id']}</b> ({_group_line(g)})</li>
<li>Day and time: <b>{g['day']} {g['time']}</b></li>
<li>First lesson: <b>{first:%d %B %Y}</b>, Lesson 1 "{LESSONS[p][0][1]}"</li>
<li>Place: {CLUB_VENUE}</li></ul>
<p>{INTRO[p]}</p>
<p>Please reply to this email if the time no longer suits you.</p>
<p>Best regards,<br>{TEAM[p]}</p>{FOOT}"""


def _waitlist(a) -> str:
    p = a["program"]
    return f"""<div style="{STYLE}"><p>Dear {a['parent_name']},</p>
<p>Thank you for registering <b>{a['child_name']}</b> for <b>{PROGRAMS[p]}</b>. All {PROGRAMS[p]} groups for {a['band']}
on the days you chose are full or clash with another activity, so {a['child_name'].split()[0]} is on the waiting list.</p>
<p>We will write as soon as a place opens. If other days suit you, just reply with them.</p>
<p>Best regards,<br>{TEAM[p]}</p>{FOOT}"""


def _reminder(a, g, n, d) -> str:
    p = a["program"]
    title, about = LESSONS[p][n - 1][1], LESSONS[p][n - 1][2]
    return f"""<div style="{STYLE}"><p>Dear {a['parent_name']},</p>
<p>A quick reminder: <b>{a['child_name']}</b> has <b>{PROGRAMS[p]}</b> on <b>{d:%A %d %B} at {g['time']}</b>.</p>
<p>Lesson {n}: <b>{title}</b>. {about}</p>
<p>Best regards,<br>{TEAM[p]}</p>{FOOT}"""


def handle(task: dict) -> dict:
    kind = task.get("kind", "confirmations")
    if kind == "send":
        with session() as con:
            pending = con.execute("SELECT COUNT(*) FROM emails WHERE status = 'Draft (not sent)'").fetchone()[0]
        return {"status": "Blocked", "output": "outbox/",
                "note": f"{pending} drafts ready. Waiting for Boss approval to send (policy: nothing is sent without approval)"}
    made = []
    with session() as con:
        groups = {g["group_id"]: dict(g) for g in con.execute("SELECT * FROM groups")}
        if kind in ("confirmations", "freeform"):
            for a in con.execute("SELECT * FROM applications WHERE status = 'Scheduled'").fetchall():
                g = groups[a["group_id"]]
                made.append(draft_email("confirmations", a["parent_email"],
                                        f"{PROGRAMS[a['program']]}: place confirmed, group {g['group_id']}, {g['day']} {g['time']}",
                                        _confirmation(a, g), program=a["program"]))
                con.execute("UPDATE applications SET status = 'Confirmation drafted' WHERE application_id = ?",
                            (a["application_id"],))
                con.commit()
            for a in con.execute("SELECT a.* FROM applications a WHERE a.status = 'Waitlist' AND NOT EXISTS"
                                 " (SELECT 1 FROM emails e WHERE e.to_addr = a.parent_email AND e.kind = 'waitlist'"
                                 " AND e.program = a.program)").fetchall():
                made.append(draft_email("waitlist", a["parent_email"], f"{PROGRAMS[a['program']]}: you are on the waiting list",
                                        _waitlist(a), program=a["program"]))
        if kind == "reminders":
            today = now().date()
            for a in con.execute("SELECT * FROM applications WHERE status = 'Confirmation drafted'").fetchall():
                g = groups[a["group_id"]]
                nl = next_lesson(g["day"], today)
                if nl:
                    n, d = nl
                    made.append(draft_email("reminders", a["parent_email"],
                                            f"Reminder: {PROGRAMS[a['program']]} Lesson {n} on {d:%a %d %b}",
                                            _reminder(a, g, n, d), program=a["program"]))
    return {"status": "Completed", "output": f"outbox/{'reminders' if kind == 'reminders' else 'confirmations'}/",
            "note": f"Drafted {len(made)} {kind} emails (not sent)"}
