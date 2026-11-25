"""The 7 specialist employees plus the Project Manager.

Every handler takes a task row (dict) and returns a dict:
  {"status": "Completed" | "Blocked", "output": "<relative path or link>", "note": "<one line>"}
"""
from . import analyst, communications, content_writer, intake, parent_support, qa_auditor, scheduler

HANDLERS = {
    "Intake Officer": intake.handle,
    "QA Auditor": qa_auditor.handle,
    "Scheduler": scheduler.handle,
    "Communications Officer": communications.handle,
    "Parent Support": parent_support.handle,
    "Content Writer": content_writer.handle,
    "Analyst": analyst.handle,
}
