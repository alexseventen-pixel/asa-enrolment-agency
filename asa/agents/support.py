"""Agent 2. Support: answers parents' questions, enrols a child step by step in the chat, and
changes or cancels an enrolment after checking the email + application ID. Rule based, so it
works the same every time without any API key. Every change updates the database."""
from __future__ import annotations

import json
import re

from ..config import (DAY_NAMES, DAYS, GROUPS, LESSONS, LEVELS, PRICE_NOTE, PRICES, PROGRAMS, SCHOOL,
                      TIMETABLE_NOTE, ts)
from ..db import log, session
from ..mailer import draft
from . import applications as apps

AGENT = "Support"
ID_RE = re.compile(r"\bASA-?\s?(\d{1,4})\b", re.I)
EMAIL_RE = re.compile(r"[^@\s,;]+@[^@\s,;]+\.[A-Za-z]{2,}")
DAY_WORDS = {"mon": "Mon", "tue": "Tue", "wed": "Wed", "thu": "Thu", "fri": "Fri",
             "пон": "Mon", "втор": "Tue", "сред": "Wed", "чет": "Thu", "пят": "Fri"}
MENU = ("I can help with:\n"
        "1. Questions: prices, timetable, levels, ages, what children learn\n"
        "2. Enrol a child (type **enrol**)\n"
        "3. Check, change or cancel an enrolment (type **change** or **cancel** with your email and application ID)\n"
        "Type **menu** any time to start again.")


# ---------- parsing helpers ----------
def parse_days(t: str) -> list[str]:
    t = t.lower()
    if re.search(r"\b(any|all|every ?day)\b", t):
        return DAYS[:]
    return [d for d in DAYS if any(w in t for w, v in DAY_WORDS.items() if v == d)]


def parse_program(t: str) -> str:
    t = t.lower()
    ai = bool(re.search(r"\bai\b|artificial|robot|ии", t))
    zh = bool(re.search(r"chinese|mandarin|китай|中文", t))
    if "both" in t or (ai and zh) or "оба" in t:
        return "both"
    return "AI" if ai else "Chinese" if zh else ""


def parse_level(t: str) -> str:
    t = t.lower().replace(" ", "")
    if "hsk2" in t or "hsk3" in t:
        return "HSK2-3"
    if "hsk1" in t:
        return "HSK1"
    if re.search(r"beginn|start|none|zero|new|начина", t):
        return "Beginner"
    return ""


def parse_id(t: str) -> str:
    m = ID_RE.search(t)
    return f"ASA-{int(m.group(1)):04d}" if m else ""


def yes(t: str) -> bool:
    return bool(re.search(r"^\s*(y|yes|yeah|ok|sure|agree|i agree|да|confirm)\b", t.lower()))


# ---------- FAQ ----------
def timetable(program: str | None = None) -> str:
    out = []
    for p in ([program] if program else PROGRAMS):
        out.append(f"\n**{PROGRAMS[p]}**\n")
        out += [f"- {g['group_id']} ({g['band']}): {DAY_NAMES[g['day']]} {g['time']}" for g in GROUPS if g["program"] == p]
    return "\n".join(out) + f"\n\n{TIMETABLE_NOTE}"


def faq(t: str) -> str | None:
    t = t.lower()
    if re.search(r"price|fee|cost|how much|pay|invoice|цен|стоим|сколько", t):
        return (f"Monthly fee: AI Club {PRICES['AI']:.0f} EUR, Chinese {PRICES['ZH']:.0f} EUR{PRICE_NOTE}. "
                "Our Accountant agent emails an invoice at the start of each month.")
    if re.search(r"time|timetable|schedule|when|which day|days|распис|время|когда", t):
        return timetable()
    if re.search(r"hsk|level|уров", t):
        return ("Chinese groups are by level: Beginner (ages 7 to 10, and 11 to 15), HSK1, and HSK2 to 3. "
                "Not sure? Choose Beginner; the teacher does a short friendly check in the first lesson.")
    if re.search(r"\bage|old|years|возраст|лет\b", t):
        return "Both programmes are for children aged 7 to 15. AI groups: 7 to 9, 10 to 12, 13 to 15."
    if re.search(r"where|room|address|location|где", t):
        return f"Lessons take place at {SCHOOL}. The room is to be confirmed."
    if re.search(r"learn|topic|lesson|programme|program|curriculum|what do|чему|урок", t):
        return ("**AI Club, 10 lessons:** " + ", ".join(LESSONS["AI"]) + ".\n\n**Chinese (draft topics):** "
                + ", ".join(LESSONS["ZH"]) + ".")
    if re.search(r"laptop|tablet|device|bring|ноут", t):
        return "No device is needed: the AI Club uses school computers. For Chinese, a notebook and pencil are enough."
    if re.search(r"miss|absent|sick|пропуст|болеет", t):
        return "No problem. Let us know by replying to the reminder email; the teacher helps your child catch up next lesson."
    if re.search(r"teacher|human|person|call|contact|manager|учител|человек", t):
        log(AGENT, "Escalated to teacher", t[:120])
        return f"I have passed your message to the teacher, who will reply by email. You can also write to the school office at {SCHOOL}."
    return None


# ---------- state ----------
def load(sid: str) -> dict:
    with session() as con:
        r = con.execute("SELECT state FROM chats WHERE session_id = ?", (sid,)).fetchone()
    return json.loads(r["state"]) if r else {}


def save(sid: str, st: dict) -> None:
    with session() as con:
        con.execute("INSERT OR REPLACE INTO chats VALUES (?,?,?)", (sid, json.dumps(st), ts()))


def record(sid: str, role: str, text: str) -> None:
    with session() as con:
        con.execute("INSERT INTO chat_messages (session_id, time, role, text) VALUES (?,?,?,?)", (sid, ts(), role, text))


def history(sid: str) -> list[dict]:
    with session() as con:
        return [dict(r) for r in con.execute("SELECT role, text FROM chat_messages WHERE session_id = ? ORDER BY id", (sid,))]


# ---------- enrolment flow ----------
ENROL_STEPS = [
    ("child_name", "What is your child's name?"),
    ("age", "How old is the child? (7 to 15)"),
    ("program", "Which programme: **AI Club**, **Chinese** or **both**?"),
    ("level", "Chinese level: **Beginner**, **HSK1** or **HSK2-3**?"),
    ("days", "Which days suit you? (for example: Tuesday and Thursday, or 'any day')"),
    ("parent_name", "Your name (parent)?"),
    ("parent_email", "Your email for the confirmation?"),
    ("consent", "Do you agree that the school processes this data to organise the activity? (yes / no)"),
]


def next_step(form: dict) -> tuple[str, str] | None:
    for key, q in ENROL_STEPS:
        if key == "level" and form.get("program") not in ("Chinese", "both"):
            continue
        if key not in form:
            return key, q
    return None


def enrol_turn(st: dict, msg: str) -> str:
    form = st.setdefault("form", {})
    step = next_step(form)
    if step and st.get("asked") == step[0]:
        key, val, err = step[0], msg.strip(), ""
        if key == "age":
            m = re.search(r"\d+", val)
            if m and 7 <= int(m.group()) <= 15:
                val = int(m.group())
            else:
                err = "Please type an age between 7 and 15."
        elif key == "program":
            val = parse_program(val) or ("AI" if "club" in val.lower() else "")
            err = "" if val else "Please answer AI Club, Chinese or both."
        elif key == "level":
            val = parse_level(val)
            err = "" if val else "Please answer Beginner, HSK1 or HSK2-3."
        elif key == "days":
            val = parse_days(val)
            err = "" if val else "Please name at least one weekday (Monday to Friday)."
        elif key == "parent_email":
            m = EMAIL_RE.search(val)
            val = m.group() if m else ""
            err = "" if val else "That does not look like an email address. Please try again."
        elif key == "consent":
            if not yes(val):
                st.clear()
                return "Without consent we cannot process the application. Nothing was saved. " + MENU
            val = True
        if err:
            return err
        form[key] = val
    step = next_step(form)
    if step:
        st["asked"] = step[0]
        return step[1]
    data = dict(form, level=form.get("level", ""), consent=True)
    res = apps.submit(data, source="Support chat")
    st.clear()
    lines = "\n".join(f"- {r['program']}: " + (f"group {r['group']} ({DAY_NAMES[r['day']]})" if r["group"] else "waiting list")
                      for r in res["enrolments"])
    log(AGENT, "Enrolled a child via chat", f"{res['application_id']} created, handed to Applications")
    return (f"Done! Application **{res['application_id']}** is saved.\n{lines}\n\n"
            f"A confirmation email was prepared for {data['parent_email']}. Keep your application ID to change the enrolment later.")


# ---------- manage flow ----------
def verify(app_id: str, email: str) -> bool:
    with session() as con:
        r = con.execute("SELECT 1 FROM students WHERE application_id = ? AND lower(parent_email) = lower(?)", (app_id, email)).fetchone()
    return bool(r)


def describe(app_id: str) -> str:
    with session() as con:
        s = con.execute("SELECT * FROM students WHERE application_id = ?", (app_id,)).fetchone()
        es = con.execute("SELECT * FROM enrolments WHERE application_id = ? ORDER BY program", (app_id,)).fetchall()
    lines = [f"**{app_id}**: {s['child_name']}, age {s['age']}, preferred days {s['days'].replace(';', ', ')}"]
    for e in es:
        name = PROGRAMS[e["program"]] + (f" ({e['level']})" if e["level"] else "")
        if e["status"] == "Active":
            g = apps.group(e["group_id"])
            lines.append(f"- {name}: group {g['group_id']}, {DAY_NAMES[g['day']]} {g['time']}")
        else:
            lines.append(f"- {name}: {e['status'].lower()}")
    if any(e["status"] == "Waitlist" for e in es):
        lines.append("\nWaitlist means no group with a free place on your preferred days. "
                     "Adding a day usually helps, for example **change days Mon Wed Fri**.")
    return "\n".join(lines)


def notify_change(app_id: str, what: str) -> str:
    with session() as con:
        s = con.execute("SELECT * FROM students WHERE application_id = ?", (app_id,)).fetchone()
        lines = apps.enrolment_lines(con, app_id)
    body = f"<p>Dear {s['parent_name']},</p><p>{what}</p><p>Current enrolment for <b>{s['child_name']}</b>:</p>{lines}<p>ASA team</p>"
    return draft(AGENT, "Change confirmation", app_id, s["parent_email"], f"Enrolment {app_id} updated", body)


def promote_waitlist(program: str, band_: str) -> None:
    """A place opened: move the first waitlisted child in that band into a group."""
    with session() as con:
        rows = con.execute("SELECT e.*, s.days FROM enrolments e JOIN students s USING (application_id)"
                           " WHERE e.status = 'Waitlist' AND e.program = ? AND e.band = ? ORDER BY s.created_at", (program, band_)).fetchall()
        for e in rows:
            gid = apps.place(con, e["application_id"], program, band_, e["days"].split(";"), e["enrolment_id"])
            if gid:
                con.execute("UPDATE enrolments SET status = 'Active', group_id = ?, updated_at = ? WHERE enrolment_id = ?",
                            (gid, ts(), e["enrolment_id"]))
                con.commit()
                notify_change(e["application_id"], f"Good news: a place opened in {PROGRAMS[program]}, group {gid}.")
                log(AGENT, f"Waitlist place offered to {e['application_id']}", f"{PROGRAMS[program]} group {gid}")
                return


def change_days(app_id: str, days: list[str]) -> str:
    freed = []
    with session() as con:
        con.execute("UPDATE students SET days = ? WHERE application_id = ?", (";".join(days), app_id))
        for e in con.execute("SELECT * FROM enrolments WHERE application_id = ? AND status != 'Cancelled' ORDER BY program", (app_id,)).fetchall():
            if e["group_id"]:
                freed.append((e["program"], e["band"]))
            con.execute("UPDATE enrolments SET group_id = '', status = 'Waitlist' WHERE enrolment_id = ?", (e["enrolment_id"],))
            gid = apps.place(con, app_id, e["program"], e["band"], days, e["enrolment_id"])
            con.execute("UPDATE enrolments SET group_id = ?, status = ?, updated_at = ? WHERE enrolment_id = ?",
                        (gid, "Active" if gid else "Waitlist", ts(), e["enrolment_id"]))
    eid = notify_change(app_id, "Your preferred days were updated: " + ", ".join(DAY_NAMES[d] for d in days) + ".")
    log(AGENT, f"Changed days for {app_id}", f"New days {', '.join(days)}. Email {eid} drafted")
    for p, b in freed:
        promote_waitlist(p, b)
    return eid


def change_level(app_id: str, level: str) -> str:
    with session() as con:
        e = con.execute("SELECT e.*, s.age, s.days FROM enrolments e JOIN students s USING (application_id)"
                        " WHERE application_id = ? AND program = 'ZH' AND status != 'Cancelled'", (app_id,)).fetchone()
        if not e:
            return ""
        b = apps.band("ZH", e["age"], level)
        con.execute("UPDATE enrolments SET group_id = '', status = 'Waitlist' WHERE enrolment_id = ?", (e["enrolment_id"],))
        gid = apps.place(con, app_id, "ZH", b, e["days"].split(";"), e["enrolment_id"])
        con.execute("UPDATE enrolments SET level = ?, band = ?, group_id = ?, status = ?, updated_at = ? WHERE enrolment_id = ?",
                    (level, b, gid, "Active" if gid else "Waitlist", ts(), e["enrolment_id"]))
    eid = notify_change(app_id, f"The Chinese level was changed to {level}.")
    log(AGENT, f"Changed Chinese level for {app_id}", f"Level {level}, group {gid or 'waitlist'}. Email {eid} drafted")
    if e["group_id"]:
        promote_waitlist("ZH", e["band"])
    return eid


def cancel(app_id: str, program: str) -> str:
    progs = ["AI", "ZH"] if program == "both" else ["AI" if program == "AI" else "ZH"]
    freed = []
    with session() as con:
        for p in progs:
            e = con.execute("SELECT * FROM enrolments WHERE application_id = ? AND program = ? AND status != 'Cancelled'", (app_id, p)).fetchone()
            if not e:
                continue
            if e["group_id"]:
                freed.append((p, e["band"]))
            con.execute("UPDATE enrolments SET status = 'Cancelled', group_id = '', updated_at = ? WHERE enrolment_id = ?", (ts(), e["enrolment_id"]))
            con.execute("UPDATE invoices SET status = 'Void' WHERE enrolment_id = ? AND status = 'Unpaid'", (e["enrolment_id"],))
    names = " and ".join(PROGRAMS[p] for p in progs)
    eid = notify_change(app_id, f"As requested, the enrolment in {names} was cancelled. Any unpaid invoice for it is void.")
    log(AGENT, f"Cancelled {names} for {app_id}", f"Email {eid} drafted, unpaid invoices voided")
    for p, b in freed:
        promote_waitlist(p, b)
    return eid


def manage_turn(st: dict, msg: str) -> str:
    t = msg.lower()
    app_id = st["app_id"]
    pend = st.get("pending")
    if pend == "days":
        days = parse_days(msg)
        if not days:
            return "Please name at least one weekday, for example 'Monday and Wednesday'."
        st.pop("pending")
        change_days(app_id, days)
        return "Updated. " + describe(app_id) + "\n\nA confirmation email was prepared. Anything else? (change days, change level, cancel, menu)"
    if pend == "level":
        level = parse_level(msg)
        if not level:
            return "Please answer Beginner, HSK1 or HSK2-3."
        st.pop("pending")
        if not change_level(app_id, level):
            return "This application has no active Chinese enrolment."
        return "Updated. " + describe(app_id) + "\n\nA confirmation email was prepared."
    if pend and pend.startswith("cancel:"):
        prog = pend.split(":")[1]
        st.pop("pending")
        if yes(msg):
            cancel(app_id, prog)
            return "Cancelled. " + describe(app_id) + "\n\nA confirmation email was prepared."
        return "OK, nothing was cancelled."
    if re.search(r"cancel|отмен|remove|stop", t):
        prog = parse_program(msg) or "both"
        prog = {"Chinese": "ZH", "AI": "AI"}.get(prog, prog)
        st["pending"] = f"cancel:{prog}"
        label = "both programmes" if prog == "both" else PROGRAMS[prog]
        return f"Please confirm: cancel **{label}** for {app_id}? (yes / no)"
    if re.search(r"day|time|reschedul|move|switch|день|перенес", t):
        days = parse_days(msg)
        if days:
            change_days(app_id, days)
            return "Updated. " + describe(app_id) + "\n\nA confirmation email was prepared."
        st["pending"] = "days"
        return "Which days suit you now?"
    if re.search(r"level|hsk|уров", t):
        level = parse_level(msg)
        if level:
            if not change_level(app_id, level):
                return "This application has no active Chinese enrolment."
            return "Updated. " + describe(app_id)
        st["pending"] = "level"
        return "Which Chinese level: Beginner, HSK1 or HSK2-3?"
    if re.search(r"status|show|current|статус", t):
        return describe(app_id)
    return f"You are managing {app_id}. You can say: **change days**, **change level**, **cancel AI Club**, **cancel Chinese**, **cancel all**, or **menu**."


# ---------- main ----------
def reply(sid: str, msg: str) -> str:
    msg = (msg or "").strip()[:500]
    record(sid, "parent", msg)
    st = load(sid)
    t = msg.lower()
    if re.search(r"^(menu|start over|restart|hi|hello|hey|привет|здравствуйте)\b", t) or not msg:
        st = {}
        out = "Hello! I am the ASA support assistant for the AI Club and Chinese classes. " + MENU
    elif st.get("mode") == "enrol":
        out = enrol_turn(st, msg)
    elif st.get("mode") == "manage":
        out = manage_turn(st, msg)
    else:
        app_id, em = parse_id(msg), EMAIL_RE.search(msg)
        if st.get("mode") == "verify" and app_id and em:
            out = start_manage(st, app_id, em.group(), st.get("intent", ""))
        elif re.search(r"change|cancel|reschedul|status|my application|modify|update|move|изменить|отмен", t) or (app_id and em):
            st = {"mode": "verify", "intent": msg}
            if app_id and em:
                out = start_manage(st, app_id, em.group(), msg)
            else:
                out = "Sure. Please send your **application ID** (for example ASA-0003) and the **email** you used, in one message."
        elif st.get("mode") == "verify":
            if True:
                out = "I need both: the application ID (ASA-0000) and the parent email. Or type **menu**."
        elif re.search(r"enrol|enroll|register|sign ?up|apply|join|записат|запись", t):
            st = {"mode": "enrol"}
            out = "Great, let us enrol your child. " + enrol_turn(st, msg)
        else:
            out = faq(msg) or ("I am not sure I understood. " + MENU)
    save(sid, st)
    record(sid, "agent", out)
    return out


def start_manage(st: dict, app_id: str, email: str, intent: str) -> str:
    if not verify(app_id, email):
        log(AGENT, "Failed verification", f"{app_id} / email did not match")
        return "I could not find an application with that ID and email. Please check both and try again."
    st.clear()
    st.update(mode="manage", app_id=app_id)
    log(AGENT, f"Verified parent for {app_id}", "Opened enrolment management")
    first = describe(app_id)
    follow = manage_turn(st, intent) if re.search(r"cancel|day|level|hsk|reschedul|move|отмен", intent.lower()) else ""
    return (first + "\n\n" + follow) if follow else (first + "\n\nWhat would you like to do? (change days, change level, cancel, menu)")
