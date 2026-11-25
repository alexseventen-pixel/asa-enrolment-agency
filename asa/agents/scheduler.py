"""Scheduler: places valid requests into groups by program + age/level band and availability.

Clash rule: a child enrolled in both programs never gets two groups on the same day.
"""
from __future__ import annotations

from ..config import GROUP_CAPACITY, SLOTS
from ..db import session


def ensure_groups(con) -> None:
    for s in SLOTS:
        con.execute("INSERT OR IGNORE INTO groups (group_id, program, band, day, time, capacity) VALUES (?,?,?,?,?,?)",
                    (s["group_id"], s["program"], s["band"], s["day"], s["time"], GROUP_CAPACITY[s["program"]]))


def handle(task: dict) -> dict:
    placed = waitlisted = clashes_avoided = 0
    with session() as con:
        ensure_groups(con)
        groups = [dict(g) for g in con.execute("SELECT * FROM groups ORDER BY group_id")]
        gday = {g["group_id"]: g["day"] for g in groups}
        fill = {g["group_id"]: con.execute("SELECT COUNT(*) FROM applications WHERE group_id = ?",
                                           (g["group_id"],)).fetchone()[0] for g in groups}
        todo = con.execute("SELECT * FROM applications WHERE status IN ('Valid','Waitlist')"
                           " ORDER BY submitted_at, program").fetchall()
        for a in todo:
            days = set((a["availability"] or "").split(";"))
            busy = {gday[r["group_id"]] for r in con.execute(
                "SELECT group_id FROM applications WHERE child_ref = ? AND group_id != '' AND application_id != ?",
                (a["child_ref"], a["application_id"]))}
            matching = [g for g in groups if g["program"] == a["program"] and g["band"] == a["band"]
                        and g["day"] in days and fill[g["group_id"]] < g["capacity"]]
            options = [g for g in matching if g["day"] not in busy]
            if len(options) < len(matching):
                clashes_avoided += 1
            if options:
                g = min(options, key=lambda g: fill[g["group_id"]])  # balance groups
                fill[g["group_id"]] += 1
                con.execute("UPDATE applications SET status = 'Scheduled', group_id = ? WHERE application_id = ?",
                            (g["group_id"], a["application_id"]))
                placed += 1
            elif a["status"] != "Waitlist":
                con.execute("UPDATE applications SET status = 'Waitlist' WHERE application_id = ?", (a["application_id"],))
                waitlisted += 1
    summary = ", ".join(f"{k} {v}" for k, v in fill.items())
    return {"status": "Completed", "output": "exports/sheets/Schedule.csv",
            "note": f"Placed {placed}, waitlisted {waitlisted}, clashes avoided {clashes_avoided}. Fill: {summary}"}
