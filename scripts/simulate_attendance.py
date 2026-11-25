"""Simulate attendance for lessons already held in the demo timeline.
SYNTHETIC: the club has not run real lessons yet. Replace with a real register later."""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from asa.config import SYNTHETIC_LABEL, now  # noqa: E402
from asa.db import session  # noqa: E402
from asa.schedule_utils import lesson_date  # noqa: E402


def main(seed: int = 7) -> int:
    rnd = random.Random(seed)
    today = now().date()
    n = 0
    with session() as con:
        for g in con.execute("SELECT * FROM groups").fetchall():
            enrolled = con.execute("SELECT COUNT(*) FROM applications WHERE group_id = ?", (g["group_id"],)).fetchone()[0]
            for lesson in range(1, 11):
                d = lesson_date(g["day"], lesson)
                if d >= today or enrolled == 0:
                    break
                present = max(0, enrolled - rnd.choice([0, 0, 1, 1, 2, 3]))
                con.execute("INSERT OR REPLACE INTO attendance VALUES (?,?,?,?,?,?,?)",
                            (g["group_id"], g["program"], lesson, d.isoformat(), enrolled, present, SYNTHETIC_LABEL))
                n += 1
    print(f"Simulated {n} lesson registers") if __name__ == "__main__" else None
    return n


if __name__ == "__main__":
    main()
