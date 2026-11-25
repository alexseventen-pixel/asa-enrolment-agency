"""Small, clearly labelled SYNTHETIC demo set (invented names, example.com emails)."""
from __future__ import annotations

from .agents import applications

DEMO = [
    ("Demo Child Anna", 8, "AI", "", ["Mon", "Wed"], "Demo Parent Laura"),
    ("Demo Child Marks", 11, "both", "Beginner", ["Mon", "Tue", "Thu"], "Demo Parent Janis"),
    ("Demo Child Elza", 9, "Chinese", "Beginner", ["Tue", "Thu"], "Demo Parent Ilze"),
    ("Demo Child Oskars", 14, "AI", "", ["Fri"], "Demo Parent Peteris"),
    ("Demo Child Sofia", 12, "Chinese", "HSK1", ["Wed"], "Demo Parent Olga"),
    ("Demo Child Daniels", 10, "both", "HSK2-3", ["Tue", "Fri"], "Demo Parent Rita"),
]


def load_demo() -> list[str]:
    ids = []
    for i, (child, age, prog, level, days, parent) in enumerate(DEMO, 1):
        r = applications.submit({"child_name": child, "age": age, "program": prog, "level": level, "days": days,
                                 "parent_name": parent, "parent_email": f"demo.parent{i}@example.com",
                                 "consent": True, "notes": "SYNTHETIC DEMO DATA"}, source="Demo data")
        ids.append(r["application_id"])
    return ids
