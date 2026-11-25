"""Parent Support: triages the parent inbox, drafts replies from the FAQ base, escalates the rest."""
from __future__ import annotations

import csv
import json
import os

from ..config import DATA, REPORTS, SAMPLE
from ..db import session

INBOX_CSV = os.environ.get("ASA_INBOX_CSV", str(SAMPLE / "parent_inbox_sample.csv"))
def program_of(text: str) -> str:
    t = text.lower()
    zh = any(w in t for w in ["chinese", "hsk", "character"])
    ai = any(w in t for w in ["ai ", "ai club", "ai website", "ai tools", "laptop", "tablet"])
    return "both" if (zh and ai) or "both" in t else "ZH" if zh else "AI" if ai else "general"


RULES = [
    ("urgent", ["medical", "allerg", "emergency", "injur"]),
    ("missed", ["miss"]),
    ("chinese", ["chinese", "hsk", "character", "homework"]),
    ("schedule", ["switch", "group", "time", "day"]),
    ("consent", ["consent", "sign"]),
    ("price", ["fee", "free", "pay", "buy", "cost", "price"]),
    ("tech", ["laptop", "tablet", "account", "device"]),
    ("safety", ["safe", "tools"]),
]


def classify(text: str) -> str:
    t = text.lower()
    for cat, words in RULES:
        if any(w in t for w in words):
            return cat
    return "other"


def handle(task: dict) -> dict:
    kb = json.loads((DATA / "faq_kb.json").read_text())
    counts = {"answered": 0, "escalated": 0}
    with open(INBOX_CSV, newline="") as f, session() as con:
        for m in csv.DictReader(f):
            if con.execute("SELECT 1 FROM messages WHERE message_id = ?", (m["message_id"],)).fetchone():
                continue
            cat = classify(m["body"])
            if cat in kb and not cat.startswith("_"):
                status, prio, draft = "Draft reply ready", "Normal", kb[cat]
                counts["answered"] += 1
            else:
                status = "Escalated to Boss"
                prio = "High" if cat == "urgent" else "Normal"
                draft = "" if cat != "urgent" else "Escalated: needs a personal reply from the teacher today."
            if cat == "price":
                status, prio, draft = "Escalated to Boss", "Normal", "Fee question: not in the knowledge base, Boss decides."
                counts["escalated"] += 1
            con.execute("INSERT INTO messages (message_id, received_at, from_email, subject, body, data_label, program,"
                        " category, priority, status, draft_reply) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (m["message_id"], m["received_at"], m["from_email"], m["subject"], m["body"], m["data_label"],
                         program_of(m["body"]), cat, prio, status, draft))
        rows = con.execute("SELECT * FROM messages ORDER BY received_at").fetchall()
    counts = {"answered": sum(r["status"] == "Draft reply ready" for r in rows),
              "escalated": sum(r["status"] == "Escalated to Boss" for r in rows)}
    lines = ["# Parent inbox triage", "", "| Message | Program | Category | Priority | Status | Draft reply |", "|---|---|---|---|---|---|"]
    lines += [f"| {r['message_id']} | {r['program']} | {r['category']} | {r['priority']} | {r['status']} | {r['draft_reply'][:80]} |" for r in rows]
    (REPORTS / "support_latest.md").write_text("\n".join(lines) + "\n")
    return {"status": "Completed", "output": "reports/support_latest.md",
            "note": f"Answered {counts['answered']} from FAQ, escalated {counts['escalated']}"}
