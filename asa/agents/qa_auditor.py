"""QA Auditor: duplicates, missing consent, invalid email, age out of range, no availability, missing Chinese level."""
from __future__ import annotations

import re

from ..config import REPORTS, ts
from ..db import session

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.I)


def handle(task: dict) -> dict:
    issues = []
    with session() as con:
        rows = con.execute("SELECT * FROM applications WHERE status IN ('New','Needs fix') ORDER BY submitted_at").fetchall()
        seen = {}
        for r in con.execute("SELECT application_id, child_name, parent_email, program FROM applications"
                             " WHERE status NOT IN ('New','Needs fix','Duplicate') ORDER BY submitted_at"):
            seen[(r["child_name"].lower(), r["parent_email"].lower(), r["program"])] = r["application_id"]
        for r in rows:
            flags = []
            key = (r["child_name"].lower(), r["parent_email"].lower(), r["program"])
            if key in seen:
                flags.append(f"duplicate of {seen[key]}")
            if r["band"] == "out of range":
                flags.append(f"age {r['age']} outside 7-15")
            if r["band"] == "level missing":
                flags.append("Chinese level missing")
            if not EMAIL_RE.match(r["parent_email"] or ""):
                flags.append("invalid parent email")
            if not (r["availability"] or "").strip():
                flags.append("no availability given")
            if (r["consent_data"] or "").lower() != "yes":
                flags.append("data consent missing")
            if flags and flags[0].startswith("duplicate"):
                status = "Duplicate"
            elif flags:
                status = "Needs fix"
            else:
                status = "Valid"
                seen[key] = r["application_id"]
            con.execute("UPDATE applications SET status = ?, qa_flags = ? WHERE application_id = ?",
                        (status, "; ".join(flags), r["application_id"]))
            if flags:
                issues.append((r["application_id"], status, "; ".join(flags)))
        valid = con.execute("SELECT COUNT(*) FROM applications WHERE status NOT IN ('New','Needs fix','Duplicate')").fetchone()[0]
    lines = [f"# QA report {ts()}", "", f"Checked {len(rows)} applications. Valid so far: {valid}.", "",
             "| Application | Status | Issues |", "|---|---|---|"]
    lines += [f"| {a} | {s} | {f} |" for a, s, f in issues]
    (REPORTS / "qa_latest.md").write_text("\n".join(lines) + "\n")
    return {"status": "Completed", "output": "reports/qa_latest.md",
            "note": f"Checked {len(rows)}, flagged {len(issues)}"}
