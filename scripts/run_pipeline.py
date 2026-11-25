"""Run one full agency day end to end on the sample data.

  python scripts/run_pipeline.py            # one day
  python scripts/run_pipeline.py --reset    # wipe state first
  python scripts/run_pipeline.py --delay 1  # slow down so the dashboard shows In Progress
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from asa.agents.project_manager import plan_day, process_queue  # noqa: E402
from asa.bridges.sheets_bridge import export_all, push  # noqa: E402
from asa.config import AGENCY_NAME, DB_PATH, EXPORTS, OUTBOX, REPORTS, SYNTHETIC_LABEL, now  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--delay", type=float, default=0.0)
    args = ap.parse_args()
    if args.reset:
        DB_PATH.unlink(missing_ok=True)
        for d in (OUTBOX, REPORTS, EXPORTS):
            shutil.rmtree(d, ignore_errors=True)
    for d in (OUTBOX, REPORTS, EXPORTS):
        d.mkdir(parents=True, exist_ok=True)
    print(f"== {AGENCY_NAME} | {now():%Y-%m-%d %H:%M} Riga | {SYNTHETIC_LABEL}")
    ids = plan_day()
    print(f"Project Manager planned {len(ids)} tasks: {ids[0]} .. {ids[-1]}")
    process_queue(args.delay)
    paths = export_all()
    print("Sheets bridge CSVs:", ", ".join(Path(p).name for p in paths.values()))
    print("Live push:", push(paths))
    print("Email drafts in outbox/ (nothing sent). Dashboard: streamlit run dashboard/app.py")
    if os.environ.get("ASA_SERVE_ASGI", "no").lower() in ("1", "yes", "true"):
        # One process serves the dashboard at / and the landing page at /apply (see asgi.py).
        port = os.environ.get("PORT", "8501")
        print(f"Serving dashboard + landing page on port {port}")
        os.chdir(Path(__file__).resolve().parent.parent)
        os.execvp(sys.executable, [sys.executable, "-m", "uvicorn", "asgi:app", "--host", "0.0.0.0", "--port", port])


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
