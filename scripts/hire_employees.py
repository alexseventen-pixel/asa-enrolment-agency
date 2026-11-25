"""Write the 8 employee kits in ai-employees style and their .installed.json receipts.

Follows markfulton/ai-employees conventions: employees/<slug>/employee.json (schema ai-employee/1),
ROLE.md, work-profile.json and an .installed.json receipt (schema ai-employee-receipt/1) holding a
sha256 (first 16 hex) per kit file, like installer/upgrade.mjs writeReceipt().
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from asa.config import AGENCY_NAME, now  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
VERSION = "0.1.0"

ROLES = {
    "project-manager": dict(
        name="Project Manager", role="Chief of Staff", reports_to="Boss (Oleg)", hands_to="All 7 employees",
        module="asa/agents/project_manager.py",
        responsibilities=["Plan the daily task list and dispatch it", "Audit all 7 employees", "Keep the Google Sheet ledger",
                          "Draft the daily brief email to the Boss", "Answer the Boss in chat from real data"],
        inputs=["Boss tasks (dashboard, chat, terminal)", "Ledger and database"], outputs=["Ledger rows", "Daily brief (.eml/.html)", "Chat answers"],
        tools=["Google Sheets", "Email (SMTP, approval gated)", "SQLite"], kpis=["Tasks completed per day", "Blocked tasks resolved", "Brief delivered daily"],
        routines=[("pm-plan-day", "mon-fri", "07:30"), ("pm-daily-brief", "mon-fri", "18:00")]),
    "intake-officer": dict(
        name="Intake Officer", role="Applications Intake (AI + Chinese)", reports_to="Project Manager", hands_to="QA Auditor",
        module="asa/agents/intake.py",
        responsibilities=["Read the ASA registration form export", "Split 'both' into one AI and one Chinese request",
                          "Compute age band (AI) or level band (Chinese)", "Import lesson registers"],
        inputs=["Form CSV (Google Form export)", "Teacher registers"], outputs=["Enrolment requests", "reports/intake_latest.json"],
        tools=["Google Forms/Sheets CSV", "SQLite"], kpis=["New requests per day", "Parse error rate"],
        routines=[("intake-import", "mon-fri", "08:00")]),
    "qa-auditor": dict(
        name="QA Auditor", role="Data Quality and Consent", reports_to="Project Manager", hands_to="Scheduler",
        module="asa/agents/qa_auditor.py",
        responsibilities=["Find duplicates", "Check data consent", "Validate emails and ages 7 to 15", "Check availability and Chinese level"],
        inputs=["New enrolment requests"], outputs=["Valid / Needs fix / Duplicate status", "reports/qa_latest.md"],
        tools=["Python rules", "SQLite"], kpis=["Issues found", "Share of requests passing QA"],
        routines=[("qa-audit", "mon-fri", "08:15")]),
    "scheduler": dict(
        name="Scheduler", role="Groups and Clash-free Timetable", reports_to="Project Manager", hands_to="Communications Officer",
        module="asa/agents/scheduler.py",
        responsibilities=["Match children to groups by program, band and availability", "Balance group sizes",
                          "Never give a child in both programs two groups on one day", "Keep a waitlist"],
        inputs=["Valid requests", "Group slots and capacity"], outputs=["Group assignments", "Waitlist", "Schedule tab"],
        tools=["Python", "SQLite", "Google Sheets"], kpis=["Group fill %", "Waitlist size", "Clashes avoided"],
        routines=[("scheduler-run", "mon-fri", "08:30")]),
    "communications": dict(
        name="Communications Officer", role="Parent Emails", reports_to="Project Manager", hands_to="Boss (approval)",
        module="asa/agents/communications.py",
        responsibilities=["Draft confirmation emails per program", "Draft waitlist emails", "Draft lesson reminders",
                          "Hold sending until the Boss approves"],
        inputs=["Group assignments", "Lesson plans"], outputs=["outbox/*.eml and .html drafts"],
        tools=["Email bridge (draft first, SMTP after approval)"], kpis=["Drafts ready", "Emails sent after approval"],
        routines=[("comms-drafts", "mon-fri", "09:00")]),
    "parent-support": dict(
        name="Parent Support", role="FAQ and Triage", reports_to="Project Manager", hands_to="Boss (escalations)",
        module="asa/agents/parent_support.py",
        responsibilities=["Categorise parent questions", "Draft replies from the FAQ base", "Escalate fees, medical and unknown questions"],
        inputs=["Parent inbox export", "data/faq_kb.json"], outputs=["Triage table", "Draft replies", "reports/support_latest.md"],
        tools=["Rules + optional LLM", "Email inbox export"], kpis=["Messages answered", "Escalations", "Response time"],
        routines=[("support-triage", "mon-fri", "10:00")]),
    "content-writer": dict(
        name="Content Writer", role="Posts and Poster Copy", reports_to="Project Manager", hands_to="Boss (approval)",
        module="asa/agents/content_writer.py",
        responsibilities=["Weekly lesson posts for AI Club and Chinese", "Poster copy for both programs", "Posts on request from the Boss"],
        inputs=["Lesson plans", "Boss requests"], outputs=["exports/posts/*.md drafts"],
        tools=["Templates + optional LLM"], kpis=["Posts created per day", "Posts approved"],
        routines=[("content-weekly", "mon", "11:00")]),
    "analyst": dict(
        name="Analyst", role="Dashboards and KPIs", reports_to="Project Manager", hands_to="Project Manager",
        module="asa/agents/analyst.py",
        responsibilities=["Compute KPIs split by program", "Refresh dashboard data and Sheets exports", "Flag bottlenecks"],
        inputs=["All tables"], outputs=["reports/kpis_latest.json", "exports/sheets/*.csv"],
        tools=["pandas", "Plotly", "Google Sheets"], kpis=["Dashboard freshness", "KPIs reported"],
        routines=[("analyst-refresh", "mon-fri", "17:30")]),
}


def h(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def main() -> None:
    for slug, r in ROLES.items():
        d = ROOT / "employees" / slug
        d.mkdir(parents=True, exist_ok=True)
        manifest = {
            "schema": "ai-employee/1", "slug": slug, "name": r["name"], "role": r["role"], "version": VERSION,
            "standard": "1.5", "agency": AGENCY_NAME, "repository": "https://github.com/markfulton/ai-employees (style)",
            "license": "MIT", "requires": {"python": ">=3.10", "harness": ["python-cli", "streamlit", "grok-bot", "claude-code"]},
            "entrypoint": r["module"],
            "connections": [{"capability": c, "providers": p, "required": False, "readonly": ro} for c, p, ro in [
                ("sheet.write", ["google-sheets"], False), ("mail.draft", ["smtp", "gmail"], False), ("db", ["sqlite"], False)]],
            "routines": [{"id": i, "days": days, "fire": fire, "budget": "10 min", "browser": "never"} for i, days, fire in r["routines"]],
            "workflow": {"reports_to": r["reports_to"], "hands_to": r["hands_to"]},
            "guardrails": ["Never send email or post without Boss approval", "Synthetic sample data only in the demo",
                           "Never invent facts: escalate"],
            "files": {"kit": ["employee.json", "ROLE.md", "work-profile.json"], "member": [".installed.json", "state/**"]},
        }
        (d / "employee.json").write_text(json.dumps(manifest, indent=2) + "\n")
        (d / "work-profile.json").write_text(json.dumps({"schema": 1, "objective": r["responsibilities"][0],
            "reviewer": "project-manager", "routines": {i: {"kind": "produce", "acceptance": "Output written and logged to the ledger"}
                                                       for i, _, _ in r["routines"]}}, indent=2) + "\n")
        role = [f"# {r['name']} ({r['role']})", "", f"Agency: {AGENCY_NAME}", f"Code: `{r['module']}`",
                f"Reports to: {r['reports_to']}. Hands work to: {r['hands_to']}.", "", "## Responsibilities"]
        role += [f"- {x}" for x in r["responsibilities"]]
        for title, key in (("Inputs", "inputs"), ("Outputs", "outputs"), ("Tools", "tools"), ("KPIs", "kpis")):
            role += ["", f"## {title}"] + [f"- {x}" for x in r[key]]
        (d / "ROLE.md").write_text("\n".join(role) + "\n")
        receipt = {"schema": "ai-employee-receipt/1", "slug": slug, "version": VERSION, "standard": "1.5",
                   "installed_on": now().strftime("%Y-%m-%d"),
                   "files": {f: h(d / f) for f in ("employee.json", "ROLE.md", "work-profile.json")}, "pending": []}
        (d / ".installed.json").write_text(json.dumps(receipt, indent=2) + "\n")
    agency = {"schema": "asa-agency/1", "name": AGENCY_NAME, "programs": ["AI Club", "Chinese"],
              "employees": [{"slug": s, "name": r["name"], "role": r["role"], "reports_to": r["reports_to"]} for s, r in ROLES.items()]}
    (ROOT / "agency.json").write_text(json.dumps(agency, indent=2) + "\n")
    top = {"schema": "ai-employee-receipt/1", "agency": AGENCY_NAME, "version": VERSION, "installed_on": now().strftime("%Y-%m-%d"),
           "employees": {s: json.loads((ROOT / "employees" / s / ".installed.json").read_text())["files"] for s in ROLES}}
    (ROOT / ".installed.json").write_text(json.dumps(top, indent=2) + "\n")
    print(f"Hired {len(ROLES)} employees, wrote .installed.json receipts")


if __name__ == "__main__":
    main()
