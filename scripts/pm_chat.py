"""Terminal chat with the Project Manager (or an employee: --as "Content Writer")."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from asa.chat import answer  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("question", nargs="*")
ap.add_argument("--as", dest="channel", default="Project Manager")
a = ap.parse_args()
if a.question:
    print(answer(" ".join(a.question), a.channel))
else:
    print(f"Chat with {a.channel}. Empty line to quit.")
    while (q := input("Boss> ").strip()):
        print(answer(q, a.channel), "\n")
