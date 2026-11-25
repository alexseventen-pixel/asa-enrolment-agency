"""Generate clearly labelled SYNTHETIC sample data for the demo (AI Club + Chinese).

No real children or parents. Names are invented, emails use the reserved
example.com domain, phones use the +371 2000 00xx test pattern.
Includes deliberate errors (duplicates, missing consent, bad ages) so the
QA Auditor has real work to do.
"""
from __future__ import annotations

import csv
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from asa.config import SAMPLE, SYNTHETIC_LABEL, TZ  # noqa: E402

FIRST = ["Anna", "Marta", "Liam", "Emils", "Sofia", "Daniel", "Eva", "Max", "Alise",
         "Roberts", "Mia", "Leo", "Kate", "Artur", "Nora", "Mark", "Zane", "Tom",
         "Lina", "Oskars", "Ella", "Ivo", "Paula", "Sam"]
LAST = ["Sample", "Testa", "Demo", "Placeholder", "Fiction", "Example"]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
SOURCES = ["School newsletter", "Poster", "Parent chat", "ManageBac notice", "Friend"]
QUESTIONS = [
    ("schedule", "Can my child switch from Monday to Wednesday group?"),
    ("price", "Is the club free or is there a fee per month?"),
    ("consent", "Where do I sign the photo and data consent form?"),
    ("tech", "Does my child need to bring a laptop or tablet?"),
    ("safety", "Which AI tools will children use and are they safe for kids?"),
    ("schedule", "What happens if we miss a lesson?"),
    ("other", "Can a younger sibling join as a guest for Demo Day?"),
    ("tech", "Do kids need their own accounts on AI websites?"),
    ("chinese", "My child already knows some Chinese characters, which level group is right?"),
    ("chinese", "Will the Chinese class prepare children for the HSK exam?"),
    ("chinese", "Is homework given in the Chinese class?"),
    ("schedule", "Can my child attend both AI Club and Chinese on different days?"),
    ("price", "Do we need to buy any materials?"),
    ("urgent", "My child has a medical condition, who should I tell before the first lesson?"),
]


def main(n: int = 80, seed: int = 25) -> None:
    rnd = random.Random(seed)
    SAMPLE.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 11, 9, 9, 0, tzinfo=TZ)
    rows = []
    for i in range(1, n + 1):
        age = rnd.choice([7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 14, 15])
        program = rnd.choice(["AI", "AI", "AI", "Chinese", "Chinese", "both"])
        level = rnd.choice(["Beginner", "Beginner", "Beginner", "HSK1", "HSK1", "HSK2", "HSK3"]) if program != "AI" else ""
        avail = sorted(rnd.sample(DAYS, rnd.choice([2, 3, 3, 4])), key=DAYS.index)
        submitted = start + timedelta(hours=rnd.randint(0, 16 * 24))
        rows.append({
            "application_id": f"APP-{i:03d}",
            "submitted_at": submitted.strftime("%Y-%m-%d %H:%M"),
            "program": program,
            "chinese_level": level,
            "child_name": f"{rnd.choice(FIRST)} {rnd.choice(LAST)}",
            "age": age,
            "grade": max(1, age - 6),
            "parent_name": f"Parent {rnd.choice(LAST)} {i:03d}",
            "parent_email": f"parent{i:03d}@example.com",
            "parent_phone": f"+371 2000 {i:04d}",
            "availability": ";".join(avail),
            "experience": rnd.choice(["none", "none", "Scratch", "Python basics", "robotics"]),
            "consent_data": rnd.choice(["yes"] * 9 + ["no"]),
            "consent_photo": rnd.choice(["yes", "yes", "no"]),
            "source": rnd.choice(SOURCES),
            "data_label": SYNTHETIC_LABEL,
        })
    # Deliberate data problems for QA
    dup = dict(rows[4]); dup["application_id"] = f"APP-{n + 1:03d}"; dup["submitted_at"] = "2026-11-21 18:05"
    rows.append(dup)
    rows[10]["age"] = 19          # out of range
    rows[17]["parent_email"] = "parent017-at-example.com"  # invalid email
    rows[23]["availability"] = ""  # no availability
    rows[30]["consent_data"] = ""  # missing consent
    rows[41]["program"] = "Chinese"; rows[41]["chinese_level"] = ""  # missing Chinese level
    with open(SAMPLE / "applications_sample.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    inbox = []
    for i in range(1, 25):
        cat, q = rnd.choice(QUESTIONS)
        inbox.append({
            "message_id": f"MSG-{i:03d}",
            "received_at": (start + timedelta(hours=rnd.randint(24, 16 * 24))).strftime("%Y-%m-%d %H:%M"),
            "from_email": f"parent{rnd.randint(1, n):03d}@example.com",
            "subject": q.split("?")[0][:60],
            "body": q,
            "data_label": SYNTHETIC_LABEL,
        })
    with open(SAMPLE / "parent_inbox_sample.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(inbox[0].keys()))
        w.writeheader(); w.writerows(inbox)
    print(f"Wrote {len(rows)} sample applications and {len(inbox)} sample parent messages to {SAMPLE}")


if __name__ == "__main__":
    main()
