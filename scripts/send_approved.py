"""Send drafted emails ONLY after the Boss approves.

  ASA_ALLOW_SEND=yes python scripts/send_approved.py --kind daily_brief --send
Without --send and ASA_ALLOW_SEND=yes it only lists what would be sent.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from asa.bridges.email_bridge import send_file  # noqa: E402
from asa.config import WORK  # noqa: E402
from asa.db import session  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--kind", default="daily_brief", help="daily_brief | confirmations | waitlist | reminders")
ap.add_argument("--send", action="store_true")
a = ap.parse_args()
with session() as con:
    rows = con.execute("SELECT email_id, to_addr, subject, file FROM emails WHERE kind = ? AND status = 'Draft (not sent)'",
                       (a.kind,)).fetchall()
    for r in rows:
        res = send_file(str(WORK / r["file"]), a.send)
        print(r["email_id"], r["to_addr"], r["subject"][:60], "->", res)
        if res == "sent":
            con.execute("UPDATE emails SET status = 'Sent' WHERE email_id = ?", (r["email_id"],))
