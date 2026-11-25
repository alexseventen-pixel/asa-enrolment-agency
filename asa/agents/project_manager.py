"""Project Manager (Chief of Staff): plans the day, dispatches tasks, audits the 7 employees,
keeps the ledger, and drafts the daily brief to the Boss."""
from __future__ import annotations

import time

from ..brief import build_brief
from ..config import EMPLOYEE_NAMES, now
from ..db import session
from ..ledger import create_task, set_status

DAILY_PLAN = [
    ("Intake Officer", "Import new applications", "Parse the ASA form export (AI + Chinese) into enrolment requests", "import", "High"),
    ("QA Auditor", "Audit new requests", "Check duplicates, consent, emails, ages, availability and Chinese level", "audit", "High"),
    ("Scheduler", "Build clash-free groups", "Place valid requests by program, age or level band and availability", "schedule", "High"),
    ("Intake Officer", "Import lesson registers", "Import attendance registers for lessons already held (sample registers)", "attendance", "Medium"),
    ("Communications Officer", "Draft confirmations", "Draft confirmation and waitlist emails per program", "confirmations", "Medium"),
    ("Communications Officer", "Draft lesson reminders", "Draft reminders for the next lesson of every placed child", "reminders", "Medium"),
    ("Communications Officer", "Send drafted emails", "Send all drafted parent emails", "send", "Medium"),
    ("Parent Support", "Triage parent inbox", "Categorise parent questions, draft FAQ replies, escalate the rest", "triage", "High"),
    ("Content Writer", "Weekly lesson posts", "Draft lesson posts for AI Club and Chinese on 4 channels", "lesson_posts", "Low"),
    ("Content Writer", "Poster copy", "Write poster copy announcing both ASA programs", "poster", "Low"),
    ("Analyst", "Refresh dashboards", "Compute KPIs split by program and export dashboard data", "kpis", "Medium"),
]


def audit() -> dict:
    """Check that each of the 7 employees has worked today and list problems."""
    today = now().strftime("%Y-%m-%d")
    with session() as con:
        worked = {r[0] for r in con.execute("SELECT DISTINCT agent_name FROM tasks WHERE substr(timestamp,1,10) = ?", (today,))}
        blocked = con.execute("SELECT COUNT(*) FROM tasks WHERE status = 'Blocked'").fetchone()[0]
    idle = [n for n in EMPLOYEE_NAMES if n != "Project Manager" and n not in worked]
    note = f"Audited 7 employees: {7 - len(idle)} active today, {blocked} blocked tasks" + (f", idle: {', '.join(idle)}" if idle else "")
    return {"status": "Completed", "output": "Ledger tab", "note": note}


def handle(task: dict) -> dict:
    kind = task.get("kind")
    if kind == "audit":
        return audit()
    if kind == "brief" or "brief" in task.get("task_description", "").lower():
        b = build_brief()
        return {"status": "Completed", "output": b["file"], "note": f"Daily brief drafted to Boss ({b['email_id']}, not sent)"}
    return audit()


def plan_day(assigned_by: str = "Project Manager") -> list[str]:
    ids = [create_task(a, t, d, k, p, assigned_by) for a, t, d, k, p in DAILY_PLAN]
    ids.append(create_task("Project Manager", "Audit employees", "Audit all 7 employees and update the ledger", "audit", "High", assigned_by))
    ids.append(create_task("Project Manager", "Daily brief", "Email the Boss a scannable daily brief", "brief", "High", assigned_by))
    return ids


def run_task(task: dict, delay: float = 0.0) -> dict:
    from . import HANDLERS
    set_status(task["task_id"], "In Progress", note="Picked up by " + task["agent_name"])
    if delay:
        time.sleep(delay)
    fn = handle if task["agent_name"] == "Project Manager" else HANDLERS[task["agent_name"]]
    try:
        res = fn(task)
    except Exception as exc:  # an employee failure becomes a Blocked task, never a crash
        res = {"status": "Blocked", "output": "", "note": f"Error: {exc}"}
    set_status(task["task_id"], res["status"], res.get("output", ""), res.get("note", ""))
    return res


def process_queue(delay: float = 0.0, log=print) -> int:
    n = 0
    while True:
        with session() as con:
            row = con.execute("SELECT * FROM tasks WHERE status = 'Queued' ORDER BY task_id LIMIT 1").fetchone()
        if not row:
            return n
        task = dict(row)
        res = run_task(task, delay)
        n += 1
        log(f"[{task['task_id']}] {task['agent_name']:<23} {res['status']:<10} {res.get('note', '')}")
