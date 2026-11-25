"""Analyst: computes KPIs and writes the dashboard data files."""
from __future__ import annotations

import json

from ..bridges.sheets_bridge import export_all
from ..config import REPORTS, ts
from ..kpis import agency_kpis, funnel, group_fill


def handle(task: dict) -> dict:
    k = agency_kpis()
    data = {"generated_at": ts(), "kpis": k, "funnel": funnel(),
            "group_fill": group_fill().to_dict(orient="records")}
    (REPORTS / "kpis_latest.json").write_text(json.dumps(data, indent=2))
    export_all()
    return {"status": "Completed", "output": "reports/kpis_latest.json",
            "note": f"{k['applications_total']} applications, fill {k['group_fill_pct']}%, attendance {k['attendance_pct']}%"}
