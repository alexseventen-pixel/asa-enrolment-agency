"""Email bridge.

Default mode is DRAFT ONLY: every email is written to outbox/ as .eml and .html
and recorded in the emails table with status "Draft (not sent)".

Real sending happens only when ALL of these are true:
  * the caller passes send=True (scripts/send_approved.py does this),
  * ASA_ALLOW_SEND=yes is set in the environment,
  * SMTP settings are present (ASA_SMTP_HOST, ASA_SMTP_PORT, ASA_SMTP_USER, ASA_SMTP_PASSWORD).
For a Gmail account use an App Password, never the main password.
"""
from __future__ import annotations

import os
import re
import smtplib
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid

from ..config import CLUB_EMAIL, OUTBOX, now, ts
from ..db import next_id, session


def _html_to_text(html: str) -> str:
    text = re.sub(r"</(td|th)>", " | ", html)
    text = re.sub(r"<(br|/p|/li|/h\d|/tr|/div)[^>]*>", "\n", text)
    text = re.sub(r"<li[^>]*>", "- ", text)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def draft_email(kind: str, to_addr: str, subject: str, html: str, sender: str = CLUB_EMAIL, program: str = "") -> dict:
    with session() as con:
        email_id = next_id(con, "emails", "email_id", "E-")
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg["Date"] = format_datetime(now())
    msg["Message-ID"] = make_msgid(domain="asa-agency.local")
    msg["X-ASA-Status"] = "DRAFT - not sent, waiting for Boss approval"
    msg.set_content(_html_to_text(html))
    msg.add_alternative(html, subtype="html")
    folder = OUTBOX / kind
    folder.mkdir(parents=True, exist_ok=True)
    eml = folder / f"{email_id}.eml"
    eml.write_bytes(bytes(msg))
    (folder / f"{email_id}.html").write_text(html, encoding="utf-8")
    rel = str(eml.relative_to(OUTBOX.parent))
    with session() as con:
        con.execute("INSERT INTO emails (email_id, created_at, program, kind, to_addr, subject, file, status)"
                    " VALUES (?,?,?,?,?,?,?, 'Draft (not sent)')", (email_id, ts(), program, kind, to_addr, subject, rel))
    return {"email_id": email_id, "file": rel}


def send_file(eml_path: str, send: bool = False) -> str:
    """Send one drafted .eml. Refuses unless explicitly allowed."""
    if not send or os.environ.get("ASA_ALLOW_SEND") != "yes":
        return "skipped: sending not approved (set ASA_ALLOW_SEND=yes and pass --send)"
    host = os.environ["ASA_SMTP_HOST"]
    port = int(os.environ.get("ASA_SMTP_PORT", "587"))
    user = os.environ["ASA_SMTP_USER"]
    password = os.environ["ASA_SMTP_PASSWORD"]
    from email import policy
    from email.parser import BytesParser
    with open(eml_path, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)
    del msg["X-ASA-Status"]
    with smtplib.SMTP(host, port) as s:
        s.starttls()
        s.login(user, password)
        s.send_message(msg)
    return "sent"
