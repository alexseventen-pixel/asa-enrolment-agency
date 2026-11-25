"""End to end tests on a temporary database. Run: python -m unittest discover tests"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class AgencyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        os.environ["ASA_WORKDIR"] = cls.tmp
        os.environ["ASA_DB"] = str(Path(cls.tmp) / "test.db")
        for d in ("outbox", "reports", "exports", "state"):
            (Path(cls.tmp) / d).mkdir()
        sys.path.insert(0, str(ROOT))
        from asa.agents.project_manager import plan_day, process_queue
        plan_day()
        process_queue(log=lambda m: None)

    def test_ledger_statuses(self):
        from asa.db import df
        t = df("SELECT status FROM tasks")
        self.assertTrue(set(t.status) <= {"Queued", "In Progress", "Blocked", "Completed"})
        self.assertEqual((t.status == "Blocked").sum(), 1)  # sending waits for approval

    def test_no_clash_for_children_in_both(self):
        from asa.db import df
        rows = df("SELECT a.child_ref, g.day FROM applications a JOIN groups g ON g.group_id = a.group_id")
        self.assertFalse(rows.duplicated().any())

    def test_groups_respect_program_band_capacity(self):
        from asa.db import df
        bad = df("SELECT a.* FROM applications a JOIN groups g ON g.group_id = a.group_id"
                 " WHERE a.program != g.program OR a.band != g.band")
        self.assertEqual(len(bad), 0)
        over = df("SELECT g.group_id FROM groups g WHERE (SELECT COUNT(*) FROM applications a WHERE a.group_id = g.group_id) > g.capacity")
        self.assertEqual(len(over), 0)

    def test_chat_answers_from_data(self):
        from asa.chat import answer
        self.assertIn("blocked", answer("Which tasks are blocked, and why?").lower())
        self.assertIn("Created T-", answer("Assign a new task to the Content Writer: write 3 LinkedIn posts about AI, due tomorrow."))

    def test_no_long_dashes(self):
        out = subprocess.run(["grep", "-rIl", "--exclude-dir=.venv", "--exclude-dir=.git", "\u2014\\|\u2013", str(ROOT)],
                             capture_output=True, text=True)
        self.assertEqual(out.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
