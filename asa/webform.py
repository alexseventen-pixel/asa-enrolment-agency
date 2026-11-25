"""Landing page form: validate a parent's application, save it, and let the agency process it.

Real submissions are appended to state/web_applications.csv (same columns as the form export),
then the Project Manager dispatches Intake -> QA -> Scheduler -> Communications at once.
Emails are drafts only (ASA_ALLOW_SEND stays no).
"""
from __future__ import annotations

import csv
import re
import threading

from .config import STATE, now
from .db import session

FIELDS = ["application_id", "submitted_at", "program", "chinese_level", "child_name", "age", "grade", "parent_name",
          "parent_email", "parent_phone", "availability", "experience", "consent_data", "consent_photo", "source",
          "data_label", "notes"]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
PROGRAM_IN = {"ai": "AI", "chinese": "Chinese", "both": "both"}
LEVELS = ["Beginner", "HSK1", "HSK2-3"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
_lock = threading.Lock()
WEB_CSV = STATE / "web_applications.csv"


def validate(form: dict[str, list[str]]) -> tuple[dict, list[str]]:
    g = lambda k: (form.get(k) or [""])[0].strip()
    errors = []
    data = {"parent_name": g("parent_name")[:80], "parent_email": g("parent_email")[:120], "parent_phone": g("parent_phone")[:40],
            "child_name": g("child_name")[:80], "grade": g("grade")[:20], "notes": g("notes")[:500]}
    for k, label in (("parent_name", "Parent name"), ("parent_email", "Parent email"), ("child_name", "Child name")):
        if not data[k]:
            errors.append(f"{label} is required.")
    if data["parent_email"] and not EMAIL_RE.match(data["parent_email"]):
        errors.append("Please enter a valid email address.")
    try:
        age = int(g("age"))
        if not 5 <= age <= 18:
            raise ValueError
    except ValueError:
        age = 0
        errors.append("Please enter the child's age (5 to 18).")
    data["age"] = age
    prog = PROGRAM_IN.get(g("program").lower())
    if not prog:
        errors.append("Please choose a programme.")
    data["program"] = prog or ""
    level = g("chinese_level")
    if prog in ("Chinese", "both"):
        if level not in LEVELS:
            errors.append("Please choose a Chinese level.")
        data["chinese_level"] = level
    else:
        data["chinese_level"] = ""
    days = [d for d in form.get("days", []) if d in DAYS]
    if not days:
        errors.append("Please choose at least one preferred day.")
    data["availability"] = ";".join(sorted(days, key=DAYS.index))
    if g("consent") != "yes":
        errors.append("Please give consent so we can process the application.")
    data["consent_photo"] = "yes" if g("consent_photo") == "yes" else "no"
    data["is_test"] = g("test") == "1" or data["notes"].upper().startswith("TEST")
    return data, errors


def submit(data: dict) -> dict:
    """Save the application and run the agency pipeline for it. Returns status for the thank-you page."""
    from .agents.project_manager import process_queue
    from .ledger import create_task
    with _lock:
        STATE.mkdir(parents=True, exist_ok=True)
        new_file = not WEB_CSV.exists()
        n = 1
        if not new_file:
            with open(WEB_CSV, newline="") as f:
                n = sum(1 for _ in csv.DictReader(f)) + 1
        app_id = f"WEB-{n:03d}"
        row = {"application_id": app_id, "submitted_at": now().strftime("%Y-%m-%d %H:%M"), "program": data["program"],
               "chinese_level": data["chinese_level"], "child_name": data["child_name"], "age": data["age"],
               "grade": data["grade"], "parent_name": data["parent_name"], "parent_email": data["parent_email"],
               "parent_phone": data["parent_phone"], "availability": data["availability"], "experience": "",
               "consent_data": "yes", "consent_photo": data["consent_photo"], "source": "Web form",
               "data_label": "TEST SUBMISSION" if data["is_test"] else "WEB FORM (real)", "notes": data["notes"]}
        with open(WEB_CSV, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            if new_file:
                w.writeheader()
            w.writerow(row)
        by = "Web form"
        create_task("Intake Officer", f"Import web application {app_id}", f"New application {app_id} from the landing page form", "import", "High", by)
        create_task("QA Auditor", f"Audit {app_id}", f"Check consent, email, age, availability and level for {app_id}", "audit", "High", by)
        create_task("Scheduler", f"Place {app_id}", f"Place {app_id} into a group or the waitlist", "schedule", "High", by)
        create_task("Communications Officer", f"Confirmation for {app_id}", f"Draft confirmation or waitlist email for {app_id}", "confirmations", "High", by)
        create_task("Analyst", f"Refresh KPIs after {app_id}", "Recompute dashboard KPIs", "kpis", "Low", by)
        process_queue(log=lambda m: None)
        with session() as con:
            reqs = [dict(r) for r in con.execute(
                "SELECT a.application_id, a.program, a.status, a.qa_flags, a.group_id, g.day FROM applications a"
                " LEFT JOIN groups g ON g.group_id = a.group_id WHERE a.child_ref = ? ORDER BY a.program", (app_id,))]
    return {"application_id": app_id, "requests": reqs}
