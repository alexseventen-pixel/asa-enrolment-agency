"""Assign a task from the terminal and let the agency process the queue.

  python scripts/assign_task.py "Content Writer" "Write 3 LinkedIn posts about our new service" --priority High --due 2026-11-26
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from asa.agents.project_manager import process_queue  # noqa: E402
from asa.ledger import create_task  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("agent"); ap.add_argument("description")
ap.add_argument("--priority", default="Medium"); ap.add_argument("--due")
ap.add_argument("--no-run", action="store_true")
a = ap.parse_args()
tid = create_task(a.agent, a.description[:60], a.description, "freeform", a.priority, "Boss (terminal)", a.due)
print("Created", tid)
if not a.no_run:
    process_queue()
