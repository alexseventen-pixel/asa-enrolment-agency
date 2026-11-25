"""Chat with the Project Manager or any employee. Every answer is computed from the
database (the same data as the ledger and dashboard). Nothing is invented: if the data
does not cover a question, the agent says so. The chat can also create tasks."""
from __future__ import annotations

import re
from datetime import timedelta

import pandas as pd

from .config import EMPLOYEE_NAMES, PROGRAMS, now
from .db import df, save_chat
from .kpis import agency_kpis, group_fill, per_employee
from .ledger import create_task

ALIASES = {
    "project manager": "Project Manager", "pm": "Project Manager", "chief of staff": "Project Manager",
    "intake": "Intake Officer", "intake officer": "Intake Officer", "sales": "Intake Officer",
    "scheduler": "Scheduler", "communications": "Communications Officer", "communications officer": "Communications Officer",
    "parent support": "Parent Support", "support": "Parent Support",
    "content writer": "Content Writer", "content": "Content Writer", "writer": "Content Writer",
    "analyst": "Analyst", "qa": "QA Auditor", "qa auditor": "QA Auditor", "auditor": "QA Auditor",
}
HELP = ("I answer from the live ledger and database. Try: How many tasks are currently running? / "
        "How many enrolment requests came in today? / How many posts were created today, and on which platforms? / "
        "Which tasks are blocked, and why? / Which employee completed the most tasks this week? / "
        "How full are the groups? / Assign a new task to the Content Writer: write 3 LinkedIn posts about our new service, due tomorrow.")


def _find_employee(text: str) -> str | None:
    t = text.lower()
    for alias in sorted(ALIASES, key=len, reverse=True):
        if re.search(r"\b" + re.escape(alias) + r"\b", t):
            return ALIASES[alias]
    return None


def _assign(q: str) -> str:
    m = re.search(r"assign (?:a )?(?:new )?task to (?:the )?(.+?):\s*(.+)", q, re.I)
    if not m:
        return "To assign, write: Assign a new task to the <employee>: <what to do>, due <tomorrow|YYYY-MM-DD>."
    agent = _find_employee(m.group(1))
    if not agent:
        return f"I do not know an employee called '{m.group(1)}'. Employees: {', '.join(EMPLOYEE_NAMES)}."
    desc = m.group(2).strip()
    due = None
    dm = re.search(r"due (tomorrow|today|\d{4}-\d{2}-\d{2})", desc, re.I)
    if dm:
        word = dm.group(1).lower()
        d = now().date() + timedelta(days=1 if word == "tomorrow" else 0) if word in ("tomorrow", "today") else word
        due = str(d)
    prio = "High" if re.search(r"urgent|asap|high priority", desc, re.I) else "Medium"
    title = re.sub(r",?\s*due .*$", "", desc, flags=re.I)[:60]
    tid = create_task(agent, title, desc, "freeform", prio, "Boss (chat)", due)
    return f"Done. Created {tid} for the {agent}: '{title}' (priority {prio}{', due ' + due if due else ''}). Status: Queued. It is in the Google Sheet ledger export now."


def answer(question: str, channel: str = "Project Manager") -> str:
    q = question.strip()
    ql = q.lower()
    today = now().strftime("%Y-%m-%d")
    t = df("SELECT * FROM tasks")
    if channel != "Project Manager" and not ql.startswith("assign"):
        reply = _employee_answer(channel, ql, t)
    elif ql.startswith("assign") or "assign a new task" in ql:
        reply = _assign(q)
    elif "blocked" in ql:
        b = t[t["status"] == "Blocked"]
        reply = (f"{len(b)} blocked task(s):\n" + "\n".join(
            f"- {r.task_id} {r.agent_name}: {r.title}. Why: {r.blocked_reason}" for r in b.itertuples())) if len(b) else "No tasks are blocked right now."
    elif re.search(r"(running|in progress|open|active).*(task|project)|(task|project)s?.*(running|in progress|open)", ql):
        run = t[t["status"].isin(["In Progress", "Queued"])]
        reply = (f"{(t['status'] == 'In Progress').sum()} in progress and {(t['status'] == 'Queued').sum()} queued "
                 f"({len(t)} tasks in the ledger in total, {(t['status'] == 'Completed').sum()} completed, "
                 f"{(t['status'] == 'Blocked').sum()} blocked).")
        if len(run):
            reply += "\n" + "\n".join(f"- {r.task_id} {r.agent_name}: {r.title} [{r.status}]" for r in run.itertuples())
    elif re.search(r"most tasks|completed the most|best employee|top employee", ql):
        tt = t.copy()
        tt["completion_time"] = pd.to_datetime(tt["completion_time"].replace("", None), errors="coerce")
        week = tt[(tt["status"] == "Completed") & (tt["completion_time"] >= pd.Timestamp(now().replace(tzinfo=None) - timedelta(days=7)))]
        counts = week["agent_name"].value_counts()
        reply = ("Completed tasks in the last 7 days: " + ", ".join(f"{k} {v}" for k, v in counts.items())
                 + ". Top: " + " and ".join(counts[counts == counts.iloc[0]].index) + f" with {counts.iloc[0]}.") if len(counts) else "No completed tasks in the last 7 days."
    elif re.search(r"post|publish", ql):
        p = df("SELECT * FROM posts WHERE substr(created_at,1,10) = ?", (today,))
        pub = (p["status"] == "Published").sum() if len(p) else 0
        by = p.groupby(["program", "platform"]).size() if len(p) else []
        reply = (f"Today the Content Writer created {len(p)} posts ({pub} published, {len(p) - pub} drafts waiting for your approval). "
                 + "By program and platform: " + ", ".join(f"{PROGRAMS.get(pr, 'Both')} {pl} {n}" for (pr, pl), n in by.items())
                 + ".\n" + "\n".join(f"- {r.post_id} [{r.platform}] {r.title}" for r in p.itertuples())) if len(p) else "No posts were created today."
    elif re.search(r"lead|enrol|application|request|sales|registration|sign.?up", ql):
        a = df("SELECT * FROM applications")
        k = agency_kpis()
        today_rows = a[a["submitted_at"].str[:10] == today]
        reply = (f"Enrolment pipeline (the 'sales' of this agency): {k['applications_total']} requests "
                 f"(AI Club {k['requests_ai']}, Chinese {k['requests_chinese']}). Today: {len(today_rows)} new. "
                 f"Placed: AI {k['placed_ai']}, Chinese {k['placed_chinese']}; waitlist {k['waitlist']}; QA issues {k['qa_issues']}.")
        recent = (today_rows if len(today_rows) else a.sort_values("submitted_at").tail(5))
        label = "Today's requests" if len(today_rows) else "Latest 5 requests"
        reply += f"\n{label}:\n" + "\n".join(
            f"- {r.application_id} {r.child_name} (age {r.age}), {PROGRAMS[r.program]}, source {r.source}, status {r.status}"
            for r in recent.itertuples())
    elif re.search(r"group|fill|capacity|schedule|waitlist", ql):
        g = group_fill()
        reply = "Group fill:\n" + "\n".join(f"- {r.group_id} {PROGRAMS[r.program]} {r.band}, {r.day} {r.time}: {r.enrolled}/{r.capacity}"
                                            for r in g.itertuples())
    elif "attendance" in ql:
        k = agency_kpis()
        reply = f"Average attendance so far: {k['attendance_pct']}% (sample registers)."
    elif re.search(r"parent|inbox|message|question|support", ql):
        k = agency_kpis()
        reply = f"Parent inbox: {k['messages_answered']} draft replies ready, {k['messages_escalated']} escalated to you."
    elif re.search(r"email|mail", ql):
        e = df("SELECT kind, status, COUNT(*) n FROM emails GROUP BY kind, status")
        reply = "Emails: " + ", ".join(f"{r.kind} {r.n} ({r.status})" for r in e.itertuples()) + ". Nothing is sent without your approval."
    elif re.search(r"summary|status|report|how are we", ql):
        k = agency_kpis()
        reply = (f"Agency summary: {(t['status'] == 'Completed').sum()} tasks completed, {(t['status'] == 'Blocked').sum()} blocked. "
                 f"{k['applications_total']} enrolment requests, group fill {k['group_fill_pct']}%, attendance {k['attendance_pct']}%, "
                 f"{k['email_drafts']} email drafts waiting for approval.")
    else:
        reply = HELP
    save_chat(channel, "boss", q)
    save_chat(channel, "agent", reply)
    return reply


def _employee_answer(name: str, ql: str, t: pd.DataFrame) -> str:
    e = t[t["agent_name"] == name].sort_values("task_id")
    if e.empty:
        return f"I am the {name}. I have no tasks in the ledger yet."
    pe = per_employee().set_index("Employee").loc[name]
    last = e.iloc[-1]
    return (f"I am the {name}. Completed {pe['Completed']}, in progress {pe['In Progress']}, queued {pe['Queued']}, "
            f"blocked {pe['Blocked']}. Latest: {last.task_id} '{last.title}' is {last.status}"
            + (f" ({last.blocked_reason})" if last.status == "Blocked" else "")
            + (f", output: {last.output_link}" if last.output_link else "") + ".")
