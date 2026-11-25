"""ASA Enrolment Agency dashboard: 4 agents, one tab each, plus Outbox and Ledger.
Login only if ASA_REQUIRE_LOGIN=yes (ASA_BOSS_USER / ASA_BOSS_PASSWORD)."""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from asa import db  # noqa: E402
from asa.agents import accountant, applications, reminders, support  # noqa: E402
from asa.config import AGENCY_NAME, CURRENCY, DAY_NAMES, DAYS, GROUPS, LEVELS, PRICE_NOTE, PRICES, PROGRAMS, TIMETABLE_NOTE  # noqa: E402
from asa.demo import load_demo  # noqa: E402

st.set_page_config(page_title=AGENCY_NAME, page_icon="🎓", layout="wide")

REQUIRE_LOGIN = os.environ.get("ASA_REQUIRE_LOGIN", "no").lower() in ("1", "yes", "true")
if REQUIRE_LOGIN and not st.session_state.get("auth"):
    with st.form("login"):
        st.subheader("Sign in")
        u, p = st.text_input("Username"), st.text_input("Password", type="password")
        if st.form_submit_button("Sign in"):
            if u == os.environ.get("ASA_BOSS_USER", "boss") and p == os.environ.get("ASA_BOSS_PASSWORD", "change-me-demo"):
                st.session_state.auth = True
                st.rerun()
            st.error("Wrong username or password")
    st.stop()

# ---------- sidebar ----------
with st.sidebar:
    st.header("🎓 " + AGENCY_NAME)
    st.caption("AI Club and Chinese classes, International School Premjers")
    st.markdown("**4 agents**\n1. Applications\n2. Support\n3. Reminders\n4. Accountant")
    st.link_button("Open the public application page", "/apply")
    st.divider()
    if st.button("Load demo data (6 synthetic students)"):
        ids = load_demo()
        db.log("System", "Loaded demo data", f"{len(ids)} synthetic applications: {', '.join(ids)}")
        st.success("Demo data loaded.")
    if st.button("Reset everything"):
        db.reset()
        st.success("Database cleared.")
    st.caption("Emails are drafts only: sending is switched off. Prices and timetable are placeholders, to be confirmed.")

students = db.df("SELECT * FROM students")
enr = db.df("SELECT e.*, s.child_name, s.parent_email FROM enrolments e JOIN students s USING (application_id)")
s = accountant.summary()
c = st.columns(5)
c[0].metric("Students", s["students"])
c[1].metric("Active enrolments", s["total"]["active"])
c[2].metric("Waiting list", s["total"]["waitlist"])
c[3].metric(f"Invoiced, {CURRENCY}", f"{s['total']['invoiced']:.0f}")
c[4].metric(f"Outstanding, {CURRENCY}", f"{s['total']['outstanding']:.0f}")


def agent_log(agent: str, kind: str | None = None):
    st.markdown("**Agent log**")
    st.dataframe(db.df("SELECT time, action, result FROM ledger WHERE agent = ? ORDER BY id DESC LIMIT 30", (agent,)),
                 hide_index=True, width="stretch")
    if kind:
        st.markdown(f"**{kind} emails (drafts)**")
        em = db.df("SELECT email_id, created_at, to_addr, subject, status, html FROM emails WHERE kind = ? ORDER BY email_id DESC", (kind,))
        st.dataframe(em.drop(columns="html"), hide_index=True, width="stretch")
        if len(em):
            pick = st.selectbox("Preview an email", em["email_id"], key=f"pv-{agent}")
            st.html(em.set_index("email_id").loc[pick, "html"])


tabs = st.tabs(["1. Applications", "2. Support", "3. Reminders", "4. Accountant", "Outbox", "Ledger"])

# ---------- 1. Applications ----------
with tabs[0]:
    st.subheader("Applications agent")
    st.caption("Saves every application (web form, chat or this form), places the child in a group by age or level and preferred days "
               "(no two activities on one day), and immediately prepares the auto-reply confirmation email.")
    with st.expander("Add an application by hand (for example from a phone call)"):
        with st.form("manual"):
            a, b, c3 = st.columns(3)
            child, age = a.text_input("Child name"), b.number_input("Age", 7, 15, 9)
            prog = c3.selectbox("Programme", ["AI", "Chinese", "both"])
            level = a.selectbox("Chinese level (if Chinese)", LEVELS)
            days = b.multiselect("Preferred days", DAYS, format_func=DAY_NAMES.get)
            parent, email = c3.text_input("Parent name"), a.text_input("Parent email")
            if st.form_submit_button("Save application"):
                d = {"child_name": child, "age": age, "program": prog, "level": level, "days": days,
                     "parent_name": parent, "parent_email": email, "consent": True}
                err = applications.validate(d)
                if err:
                    st.error(" ".join(err))
                else:
                    r = applications.submit(d, source="Dashboard")
                    st.success(f"Saved {r['application_id']}. Auto-reply {r['email_id']} prepared.")
    if len(enr):
        view = enr.copy()
        view["programme"] = view["program"].map(PROGRAMS)
        g = {x["group_id"]: f"{x['group_id']} {x['day']} {x['time']}" for x in GROUPS}
        view["group"] = view["group_id"].map(g).fillna("")
        view = view.merge(students[["application_id", "created_at", "source", "label"]], on="application_id")
        st.dataframe(view[["application_id", "created_at", "child_name", "programme", "level", "band", "group", "status",
                           "parent_email", "source", "label"]].sort_values("application_id", ascending=False),
                     hide_index=True, width="stretch")
        fill = enr[enr.status == "Active"].groupby("group_id").size()
        st.markdown("**Group fill** (" + TIMETABLE_NOTE + ")")
        st.dataframe([{"group": x["group_id"], "programme": PROGRAMS[x["program"]], "band": x["band"], "day": DAY_NAMES[x["day"]],
                       "time": x["time"], "students": int(fill.get(x["group_id"], 0)), "capacity": x["capacity"]} for x in GROUPS],
                     hide_index=True, width="stretch")
    else:
        st.info("No applications yet. Submit one on the public page (/apply) or click 'Load demo data' in the sidebar.")
    agent_log("Applications", "Auto-reply")

# ---------- 2. Support ----------
with tabs[1]:
    st.subheader("Support agent")
    st.caption("Answers questions (prices, timetable, levels, ages, lessons), enrols a child step by step, and changes days, level "
               "or cancels after checking email + application ID. The same assistant is on the public page.")
    sid = st.session_state.setdefault("sid", "dash-" + uuid.uuid4().hex[:8])
    for m in support.history(sid):
        with st.chat_message("user" if m["role"] == "parent" else "assistant"):
            st.markdown(m["text"])
    if not support.history(sid):
        st.caption("Try: 'how much does it cost?', 'enrol', or 'change days ASA-0002 demo.parent2@example.com'.")
    msg = st.chat_input("Write as a parent...")
    if msg:
        support.reply(sid, msg)
        st.rerun()
    if st.button("New conversation"):
        st.session_state.sid = "dash-" + uuid.uuid4().hex[:8]
        st.rerun()
    agent_log("Support", "Change confirmation")

# ---------- 3. Reminders ----------
with tabs[2]:
    st.subheader("Reminders agent")
    st.caption("Prepares a reminder email for every child with a lesson tomorrow: day, time, group and lesson topic. "
               "Running it twice for the same day does not create duplicates.")
    if st.button("Generate tomorrow's reminders", type="primary"):
        r = reminders.run()
        st.success(f"{r['day']} {r['date']}: {len(r['created'])} reminder(s) prepared, {r['skipped']} already done.")
        if r["created"]:
            st.dataframe(r["created"], hide_index=True, width="stretch")
    agent_log("Reminders", "Reminder")

# ---------- 4. Accountant ----------
with tabs[3]:
    st.subheader("Accountant agent")
    st.caption(f"Issues one monthly invoice per active enrolment and emails it (draft). Fees: AI Club {PRICES['AI']:.0f} {CURRENCY}, "
               f"Chinese {PRICES['ZH']:.0f} {CURRENCY}{PRICE_NOTE}.")
    if st.button("Issue invoices for this month", type="primary"):
        r = accountant.issue()
        st.success(f"{r['period']}: {len(r['created'])} new invoice(s), {r['total']:.2f} {CURRENCY}.")
        st.rerun()
    st.markdown("**Summary by programme**")
    st.dataframe(s["by_programme"] + [dict(programme="Total", **s["total"])], hide_index=True, width="stretch")
    inv = accountant.invoices()
    if len(inv):
        inv["program"] = inv["program"].map(PROGRAMS)
        st.dataframe(inv, hide_index=True, width="stretch")
        a, b, c3 = st.columns(3)
        pick = a.selectbox("Invoice", inv["invoice_no"])
        row = inv.set_index("invoice_no").loc[pick]
        if row["status"] == "Unpaid" and b.button("Mark paid"):
            accountant.mark_paid(pick)
            st.rerun()
        if row["status"] == "Paid" and b.button("Mark unpaid"):
            accountant.mark_paid(pick, False)
            st.rerun()
        c3.download_button("Download invoice (HTML, print to PDF)", accountant.invoice_html(pick), file_name=f"{pick}.html", mime="text/html")
    else:
        st.info("No invoices yet. Click 'Issue invoices for this month'.")
    agent_log("Accountant", "Invoice")

# ---------- Outbox ----------
with tabs[4]:
    st.subheader("Outbox: every email the agents prepared")
    st.caption("Sending is switched off (ASA_ALLOW_SEND=no), so all emails stay as drafts here and as .eml files.")
    em = db.df("SELECT email_id, created_at, agent, kind, application_id, to_addr, subject, status, html FROM emails ORDER BY email_id DESC")
    if len(em):
        st.dataframe(em.drop(columns="html"), hide_index=True, width="stretch")
        pick = st.selectbox("Preview", em["email_id"], key="pv-outbox")
        st.html(em.set_index("email_id").loc[pick, "html"])
    else:
        st.info("No emails yet.")

# ---------- Ledger ----------
with tabs[5]:
    st.subheader("Ledger: what each agent did")
    st.dataframe(db.df("SELECT time, agent, action, result FROM ledger ORDER BY id DESC"), hide_index=True, width="stretch")
