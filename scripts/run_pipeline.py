"""Start-up script (also used as the Render start command).
--reset   clear the database and outbox
--demo    load the small synthetic demo set (also if ASA_DEMO=yes)
If ASA_SERVE_ASGI=yes it then serves the app (dashboard + landing page) with uvicorn on $PORT."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from asa import config, db  # noqa: E402
from asa.demo import load_demo  # noqa: E402

args = sys.argv[1:]
if "--reset" in args:
    db.reset()
    shutil.rmtree(config.OUTBOX, ignore_errors=True)
    print("Database and outbox cleared.")
with db.session():
    pass
if "--demo" in args or os.environ.get("ASA_DEMO", "no").lower() == "yes":
    print("Demo data loaded:", ", ".join(load_demo()))

if os.environ.get("ASA_SERVE_ASGI", "no").lower() == "yes":
    port = os.environ.get("PORT", "8000")
    os.chdir(config.ROOT)
    os.execvp(sys.executable, [sys.executable, "-m", "uvicorn", "asgi:app", "--host", "0.0.0.0", "--port", port])
