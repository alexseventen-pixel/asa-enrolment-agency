"""Google Sheets bridge.

1. export_all() writes one CSV per tab to exports/sheets/ (always works, no credentials).
2. push() uploads those CSVs to the live Google Sheet when a service account is configured:
     ASA_SHEET_ID=<spreadsheet id>
     GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json   (share the sheet with that account)
   Requires: pip install gspread google-auth
Tabs: Applications, Schedule, Ledger, Attendance. The Dashboard tab is computed by formulas inside the sheet.
"""
from __future__ import annotations

import csv
import os

from ..config import EXPORTS
from ..db import df
from ..ledger import export_csv

TABS = {
    "Applications": "SELECT application_id AS 'Request ID', child_ref AS 'Form Row', CASE program WHEN 'ZH' THEN 'Chinese'"
                    " ELSE 'AI Club' END AS 'Program', submitted_at AS 'Submitted', child_name AS 'Child (sample)',"
                    " age AS 'Age', chinese_level AS 'Chinese Level', band AS 'Band', availability AS 'Availability',"
                    " consent_data AS 'Data Consent', consent_photo AS 'Photo Consent', source AS 'Source',"
                    " status AS 'Status', qa_flags AS 'QA Flags', group_id AS 'Group', data_label AS 'Data Label'"
                    " FROM applications ORDER BY child_ref, program",
    "Schedule": "SELECT g.group_id AS 'Group', CASE g.program WHEN 'ZH' THEN 'Chinese' ELSE 'AI Club' END AS 'Program',"
                " g.band AS 'Band', g.day AS 'Day', g.time AS 'Time', g.capacity AS 'Capacity',"
                " (SELECT COUNT(*) FROM applications a WHERE a.group_id = g.group_id) AS 'Enrolled',"
                " (SELECT COUNT(*) FROM applications a WHERE a.status = 'Waitlist' AND a.program = g.program"
                " AND a.band = g.band) AS 'Waitlist (band)' FROM groups g ORDER BY g.group_id",
    "Attendance": "SELECT group_id AS 'Group', CASE program WHEN 'ZH' THEN 'Chinese' ELSE 'AI Club' END AS 'Program',"
                  " lesson_no AS 'Lesson', lesson_date AS 'Date', enrolled AS 'Enrolled', present AS 'Present',"
                  " data_label AS 'Data Label' FROM attendance ORDER BY group_id, lesson_no",
}


def export_all() -> dict[str, str]:
    folder = EXPORTS / "sheets"
    folder.mkdir(parents=True, exist_ok=True)
    paths = {"Ledger": export_csv()}
    for tab, sql in TABS.items():
        p = folder / f"{tab}.csv"
        df(sql).to_csv(p, index=False)
        paths[tab] = str(p)
    return paths


def push(paths: dict[str, str] | None = None) -> str:
    sheet_id = os.environ.get("ASA_SHEET_ID")
    creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not (sheet_id and creds):
        return "skipped: set ASA_SHEET_ID and GOOGLE_APPLICATION_CREDENTIALS to push live"
    import gspread  # optional dependency
    gc = gspread.service_account(filename=creds)
    sh = gc.open_by_key(sheet_id)
    paths = paths or export_all()
    for tab, p in paths.items():
        with open(p, newline="") as f:
            rows = list(csv.reader(f))
        ws = sh.worksheet(tab)
        ws.batch_clear(["A1:Z2000"])
        ws.update(rows, "A1", value_input_option="USER_ENTERED")
    return f"pushed {len(paths)} tabs to {sheet_id}"
