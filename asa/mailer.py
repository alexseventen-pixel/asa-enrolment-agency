"""Outbox. Every email is saved as a draft (DB + .eml file). Sending only if ASA_ALLOW_SEND=yes
and SMTP settings exist (ASA_SMTP_HOST, ASA_SMTP_PORT, ASA_SMTP_USER, ASA_SMTP_PASSWORD)."""
from __future__ import annotations

import os
import re
import smtplib
from email.message import EmailMessage
from email.utils import format_datetime

from .config import AGENCY_NAME, CLUB_EMAIL, OUTBOX, now, ts
from .db import next_id, session

WRAP = ('<div style="font-family:Arial,sans-serif;color:#1d2433;max-width:620px">{body}'
        '<p style="color:#888;font-size:11px">Sent by the {agent} agent of {agency}.</p></div>')


def draft(agent: str, kind: str, application_id: str, to_addr: str, subject: str, body_html: str) -> str:
    html = WRAP.format(body=body_html, agent=agent, agency=AGENCY_NAME)
    with session() as con:
        email_id = next_id(con, "emails", "email_id", "E-")
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"], msg["Date"] = CLUB_EMAIL, to_addr, subject, format_datetime(now())
        text = re.sub(r"<[^>]+>", "", re.sub(r"<(br|/p|/li|/tr)[^>]*>", "\n", html))
        msg.set_content(text.strip())
        msg.add_alternative(html, subtype="html")
        OUTBOX.mkdir(parents=True, exist_ok=True)
        path = OUTBOX / f"{email_id}.eml"
        path.write_bytes(bytes(msg))
        status = _maybe_send(msg)
        con.execute("INSERT INTO emails VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (email_id, ts(), agent, kind, application_id, to_addr, subject, html, path.name, status))
    return email_id


def _maybe_send(msg: EmailMessage) -> str:
    if os.environ.get("ASA_ALLOW_SEND", "no").lower() != "yes" or not os.environ.get("ASA_SMTP_HOST"):
        return "Draft (sending off)"
    try:
        with smtplib.SMTP(os.environ["ASA_SMTP_HOST"], int(os.environ.get("ASA_SMTP_PORT", "587"))) as s:
            s.starttls()
            s.login(os.environ["ASA_SMTP_USER"], os.environ["ASA_SMTP_PASSWORD"])
            s.send_message(msg)
        return "Sent"
    except Exception as exc:  # keep the draft, report the error
        return f"Send failed: {exc}"[:120]
