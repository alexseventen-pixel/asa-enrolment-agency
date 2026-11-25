"""Task ledger: create tasks, move them through statuses, mirror to CSV.

Columns follow the lecturer's brief:
Task ID | Timestamp | Assigned By | Agent Name | Task Description | Priority |
Status (Queued / In Progress / Blocked / Completed) | Output / Result Link | Completion Time
"""
from __future__ import annotations

import csv

from .config import EMPLOYEE_NAMES, EXPORTS, ts
from .db import next_id, session

STATUSES = ["Queued", "In Progress", "Blocked", "Completed"]
PRIORITIES = ["Low", "Medium", "High", "Urgent"]
LEDGER_COLUMNS = ["Task ID", "Timestamp", "Assigned By", "Agent Name", "Task Description",
                  "Priority", "Status", "Output / Result Link", "Completion Time"]


def create_task(agent_name: str, title: str, description: str, kind: str = "freeform",
                priority: str = "Medium", assigned_by: str = "Project Manager",
                deadline: str | None = None) -> str:
    if agent_name not in EMPLOYEE_NAMES:
        raise ValueError(f"Unknown employee: {agent_name}")
    with session() as con:
        task_id = next_id(con, "tasks", "task_id", "T-")
        con.execute(
            "INSERT INTO tasks (task_id, timestamp, assigned_by, agent_name, title, task_description,"
            " kind, priority, deadline, status) VALUES (?,?,?,?,?,?,?,?,?, 'Queued')",
            (task_id, ts(), assigned_by, agent_name, title, description, kind, priority, deadline))
        con.execute("INSERT INTO task_events (task_id, timestamp, status, note) VALUES (?,?,?,?)",
                    (task_id, ts(), "Queued", f"Assigned by {assigned_by}"))
    export_csv()
    return task_id


def set_status(task_id: str, status: str, output_link: str = "", note: str = "") -> None:
    assert status in STATUSES, status
    with session() as con:
        fields = {"status": status}
        if status == "In Progress":
            fields["started_at"] = ts()
        if status == "Completed":
            fields["completion_time"] = ts()
            fields["blocked_reason"] = ""
        if status == "Blocked":
            fields["blocked_reason"] = note
        if output_link:
            fields["output_link"] = output_link
        sets = ", ".join(f"{k} = ?" for k in fields)
        con.execute(f"UPDATE tasks SET {sets} WHERE task_id = ?", (*fields.values(), task_id))
        con.execute("INSERT INTO task_events (task_id, timestamp, status, note) VALUES (?,?,?,?)",
                    (task_id, ts(), status, note))
    export_csv()


def ledger_rows() -> list[list[str]]:
    with session() as con:
        rows = con.execute(
            "SELECT task_id, timestamp, assigned_by, agent_name, CASE WHEN instr(task_description, title) = 1"
            " THEN task_description ELSE title || ': ' || task_description END,"
            " priority, status, output_link, completion_time FROM tasks ORDER BY task_id").fetchall()
    return [[("" if v is None else str(v)) for v in r] for r in rows]


def export_csv() -> str:
    path = EXPORTS / "sheets" / "Ledger.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(LEDGER_COLUMNS)
        w.writerows(ledger_rows())
    return str(path)
