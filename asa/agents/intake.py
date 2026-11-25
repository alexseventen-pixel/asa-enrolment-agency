"""Intake Officer: parses the ASA application form export (CSV) into enrolment requests.

One form row can ask for AI, Chinese or both. "both" becomes two enrolment requests
(APP-004-AI and APP-004-ZH) that share child_ref APP-004, so the Scheduler can avoid clashes.
"""
from __future__ import annotations

import csv
import json
import os

from ..config import REPORTS, SAMPLE
from ..db import session

FORM_CSV = os.environ.get("ASA_FORM_CSV", str(SAMPLE / "applications_sample.csv"))
PROGRAM_MAP = {"ai": ["AI"], "chinese": ["ZH"], "both": ["AI", "ZH"]}


def band(program: str, age: int, level: str) -> str:
    if not 7 <= age <= 15:
        return "out of range"
    if program == "AI":
        return "7-9" if age <= 9 else "10-12" if age <= 12 else "13-15"
    level = (level or "").strip()
    if level == "Beginner":
        return "Beginner 7-10" if age <= 10 else "Beginner 11-15"
    if level == "HSK1":
        return "HSK1"
    if level in ("HSK2", "HSK3"):
        return "HSK2-3"
    return "level missing"


def import_registers() -> dict:
    """Demo: registers come from the synthetic simulator. Real use: read the teacher's register CSV."""
    import importlib.util
    from ..config import ROOT
    spec = importlib.util.spec_from_file_location("sim", ROOT / "scripts" / "simulate_attendance.py")
    sim = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sim)
    n = sim.main()
    return {"status": "Completed", "output": "exports/sheets/Attendance.csv",
            "note": f"Imported {n} lesson registers (synthetic sample registers)"}


def handle(task: dict) -> dict:
    if task.get("kind") == "attendance":
        return import_registers()
    new, seen = 0, 0
    with open(FORM_CSV, newline="") as f, session() as con:
        for r in csv.DictReader(f):
            seen += 1
            try:
                age = int(r["age"])
            except ValueError:
                age = -1
            for prog in PROGRAM_MAP.get(r["program"].strip().lower(), ["AI"]):
                app_id = f"{r['application_id']}-{prog}"
                if con.execute("SELECT 1 FROM applications WHERE application_id = ?", (app_id,)).fetchone():
                    continue
                level = r.get("chinese_level", "") if prog == "ZH" else ""
                con.execute(
                    "INSERT INTO applications (application_id, child_ref, program, chinese_level, submitted_at,"
                    " child_name, age, grade, parent_name, parent_email, parent_phone, availability, experience,"
                    " consent_data, consent_photo, source, data_label, band, status)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'New')",
                    (app_id, r["application_id"], prog, level, r["submitted_at"], r["child_name"], age, r["grade"],
                     r["parent_name"], r["parent_email"], r["parent_phone"], r["availability"], r["experience"],
                     r["consent_data"], r["consent_photo"], r["source"], r["data_label"], band(prog, age, level)))
                new += 1
        total = con.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        by_prog = dict(con.execute("SELECT program, COUNT(*) FROM applications GROUP BY program").fetchall())
    out = REPORTS / "intake_latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"form_rows": seen, "new_requests": new, "total_requests": total,
                               "by_program": by_prog, "source": os.path.basename(FORM_CSV)}, indent=2))
    return {"status": "Completed", "output": "reports/intake_latest.json",
            "note": f"{seen} form rows, {new} new enrolment requests (AI {by_prog.get('AI', 0)}, Chinese {by_prog.get('ZH', 0)})"}
