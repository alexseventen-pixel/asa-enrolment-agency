"""Draw the Boss -> Project Manager -> 7 employees workflow as docs/workflow.svg."""
from pathlib import Path

W, H = 980, 520
box = lambda x, y, w, h, t, sub, fill: (
    f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="#24395f" stroke-width="1.5"/>'
    f'<text x="{x + w / 2}" y="{y + 24}" text-anchor="middle" font-weight="bold" font-size="14">{t}</text>'
    f'<text x="{x + w / 2}" y="{y + 42}" text-anchor="middle" font-size="11" fill="#445">{sub}</text>')
arrow = lambda x1, y1, x2, y2, label="": (
    f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#24395f" stroke-width="1.5" marker-end="url(#a)"/>'
    + (f'<text x="{(x1 + x2) / 2 + 4}" y="{(y1 + y2) / 2 - 4}" font-size="10" fill="#667">{label}</text>' if label else ""))
parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="Arial">',
         '<defs><marker id="a" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0, 10 3.5, 0 7" fill="#24395f"/></marker></defs>',
         box(360, 10, 260, 56, "Boss (Oleg)", "Dashboard, chat, approvals", "#ffe8b0"),
         box(360, 110, 260, 56, "1 Project Manager", "Plans, audits, ledger, daily brief", "#cfe0ff"),
         arrow(490, 66, 490, 110, "tasks, questions"),
         box(20, 120, 210, 46, "Google Sheet ledger", "Ledger + Dashboard tabs", "#e3f5e1"),
         box(750, 120, 210, 46, "Daily brief email", "draft, sent after approval", "#e3f5e1"),
         arrow(360, 138, 230, 143), arrow(620, 138, 750, 143)]
flow = [("2 Intake Officer", "form CSV to requests"), ("8 QA Auditor", "duplicates, consent"),
        ("3 Scheduler", "clash-free groups"), ("4 Communications", "confirm, remind")]
side = [("5 Parent Support", "FAQ triage"), ("6 Content Writer", "posts, poster"), ("7 Analyst", "KPIs, dashboards")]
for i, (t, s) in enumerate(flow):
    x = 20 + i * 245
    parts.append(box(x, 250, 210, 56, t, s, "#ffffff"))
    if i:
        parts.append(arrow(x - 35, 278, x, 278))
for i, (t, s) in enumerate(side):
    x = 130 + i * 260
    parts.append(box(x, 380, 210, 56, t, s, "#ffffff"))
parts.append(arrow(490, 166, 125, 250, "dispatch"))
parts.append(arrow(490, 166, 490, 380))
parts.append(arrow(895, 306, 895, 360))
parts.append('<text x="850" y="378" font-size="11" fill="#a33">approval gate (Boss)</text>')
parts.append('<text x="20" y="480" font-size="12" fill="#445">Every task: Queued, In Progress, Completed or Blocked, logged to the ledger. '
             'Analyst feeds the dashboard. PM answers chat from the same data.</text>')
parts.append("</svg>")
out = Path(__file__).resolve().parent.parent / "docs" / "workflow.svg"
out.write_text("\n".join(parts))
print(out)
