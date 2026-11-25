"""Daily status bulletin from the Project Manager to the Boss (drafted, never auto-sent)."""
from __future__ import annotations

from .bridges.email_bridge import draft_email
from .config import AGENCY_NAME, BOSS_EMAIL, REPORTS, now
from .db import df
from .kpis import agency_kpis, per_employee

CSS = ("font-family:Arial,sans-serif;color:#1d2433;max-width:720px", "border-collapse:collapse;width:100%;font-size:13px",
       "border:1px solid #d8dde6;padding:4px 6px;text-align:left")


def _table(frame) -> str:
    if frame.empty:
        return "<p><i>None</i></p>"
    head = "".join(f'<th style="{CSS[2]};background:#24395f;color:#fff">{c}</th>' for c in frame.columns)
    body = "".join("<tr>" + "".join(f'<td style="{CSS[2]}">{v}</td>' for v in r) + "</tr>" for r in frame.astype(str).values)
    return f'<table style="{CSS[1]}"><tr>{head}</tr>{body}</table>'


def build_brief() -> dict:
    today = now().strftime("%Y-%m-%d")
    t = df("SELECT task_id AS 'Task', agent_name AS 'Employee', title AS 'Title', status AS 'Status',"
           " blocked_reason AS 'Blocked reason', output_link AS 'Output', timestamp FROM tasks"
           " WHERE (substr(timestamp,1,10) = ? OR status IN ('Queued','In Progress','Blocked')) AND kind != 'brief'"
           " ORDER BY task_id", (today,))
    k = agency_kpis()
    done = t[t["Status"] == "Completed"].drop(columns=["timestamp", "Blocked reason"])
    prog = t[t["Status"].isin(["Queued", "In Progress"])].drop(columns=["timestamp", "Blocked reason"])
    blocked = t[t["Status"] == "Blocked"].drop(columns=["timestamp"])
    tiles = [("Enrolment requests", k["applications_total"]), ("AI / Chinese", f"{k['requests_ai']} / {k['requests_chinese']}"),
             ("Placed AI / Chinese", f"{k['placed_ai']} / {k['placed_chinese']}"), ("In both programs", k["children_in_both"]),
             ("Waitlist", k["waitlist"]), ("Group fill", f"{k['group_fill_pct']}%"), ("Attendance", f"{k['attendance_pct']}%"),
             ("QA issues", k["qa_issues"]), ("Email drafts", k["email_drafts"]), ("Posts today", k["posts_today"]),
             ("Parent msgs answered / escalated", f"{k['messages_answered']} / {k['messages_escalated']}")]
    cells = [f'<td style="{CSS[2]};text-align:center"><div style="font-size:18px;font-weight:bold">{v}</div>'
             f'<div style="font-size:11px;color:#667">{n}</div></td>' for n, v in tiles]
    html = f"""<div style="{CSS[0]}"><h2 style="margin-bottom:0">{AGENCY_NAME}: daily brief</h2>
<p style="color:#667;margin-top:2px">{now():%A %d %B %Y, %H:%M} (Riga time). Synthetic sample data, demo only.</p>
<p><b>Summary:</b> {len(done)} tasks completed, {len(prog)} queued or in progress, {len(blocked)} blocked.</p>
<table style="{CSS[1]}"><tr>{"".join(cells[:6])}</tr></table>
<table style="{CSS[1]};margin-top:4px"><tr>{"".join(cells[6:])}</tr></table>
<h3>Blocked (needs you)</h3>{_table(blocked)}
<h3>Completed today</h3>{_table(done)}
<h3>Queued / in progress</h3>{_table(prog)}
<h3>KPIs per employee</h3>{_table(per_employee())}
<p style="color:#888;font-size:11px">Sent by the Project Manager agent. Ledger: Google Sheet tab "Ledger".</p></div>"""
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / f"daily_brief_{today}.html").write_text(html, encoding="utf-8")
    email = draft_email("daily_brief", BOSS_EMAIL, f"[{AGENCY_NAME}] Daily brief {today}: "
                        f"{len(done)} done, {len(prog)} open, {len(blocked)} blocked", html)
    return {"html": f"reports/daily_brief_{today}.html", **email}
