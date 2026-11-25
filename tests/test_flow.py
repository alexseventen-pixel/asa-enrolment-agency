"""End to end test of the 4 agents on a temporary database. Run: python -m pytest -q  (or python tests/test_flow.py)"""
import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

os.environ["ASA_WORKDIR"] = tempfile.mkdtemp()
os.environ.pop("ASA_DB", None)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from asa import db  # noqa: E402
from asa.agents import accountant, applications, reminders, support  # noqa: E402
from asa.demo import load_demo  # noqa: E402


def test_flow():
    db.reset()
    ids = load_demo()
    assert len(ids) == 6
    r = applications.submit({"child_name": "Test Child", "age": 9, "program": "both", "level": "Beginner",
                             "days": ["Mon", "Tue"], "parent_name": "Test Parent", "parent_email": "t@example.com",
                             "consent": True, "test": True})
    aid = r["application_id"]
    days = [e["day"] for e in r["enrolments"]]
    assert all(days) and len(set(days)) == 2, r  # placed, no same-day clash
    assert db.df("SELECT * FROM emails WHERE application_id = ? AND kind = 'Auto-reply'", (aid,)).shape[0] == 1

    sid = "test"
    assert "placeholder" in support.reply(sid, "how much does it cost?")
    out = support.reply(sid, f"I want to cancel Chinese, {aid} t@example.com")
    assert "confirm" in out.lower(), out
    support.reply(sid, "yes")
    e = db.df("SELECT status FROM enrolments WHERE enrolment_id = ?", (aid + "-ZH",))
    assert e.status[0] == "Cancelled"
    support.reply(sid, "change days to Thursday")
    g = db.df("SELECT group_id FROM enrolments WHERE enrolment_id = ?", (aid + "-AI",)).group_id[0]
    assert g == "AI-2" or g == "", g  # 9 year old: AI 7-9 is Mon/Wed only, so Thursday means waitlist
    support.reply(sid, "change days to Wednesday")
    assert db.df("SELECT group_id FROM enrolments WHERE enrolment_id = ?", (aid + "-AI",)).group_id[0] == "AI-2"
    assert support.reply("x", "change ASA-0001 wrong@example.com").startswith("I could not find")

    # enrol via chat
    for m in ["enrol", "Chat Kid", "8", "AI", "Monday", "Chat Parent", "chat@example.com", "yes"]:
        out = support.reply("enrol", m)
    assert "is saved" in out, out

    # reminders: find a date whose weekday is Wednesday
    d = date.today() + timedelta(days=1)
    while d.strftime("%a") != "Wed":
        d += timedelta(days=1)
    rem = reminders.run(d)
    assert any(x["application_id"] == aid for x in rem["created"])
    assert reminders.run(d)["created"] == []  # no duplicates

    inv = accountant.issue("2026-12")
    assert inv["created"] and accountant.issue("2026-12")["created"] == []
    no = inv["created"][0]["invoice_no"]
    before = accountant.summary()["total"]["paid"]
    assert accountant.mark_paid(no)
    assert accountant.summary()["total"]["paid"] > before
    assert "Paid" in accountant.invoice_html(no)


if __name__ == "__main__":
    test_flow()
    print("ok")
