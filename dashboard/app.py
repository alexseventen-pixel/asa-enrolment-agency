"""Boss Command Center for the ASA Enrolment Agency (AI + Chinese).

Run:  streamlit run dashboard/app.py
Login: ASA_BOSS_USER / ASA_BOSS_PASSWORD env vars (demo defaults: boss / change-me-demo).
Modules: A) Task assignment  B) Live task board  C) Reports  D) Chat  E) Employees
"""
from __future__ import annotations

import hmac
import io
import os
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from asa.agents.project_manager import plan_day, process_queue  # noqa: E402
from asa.chat import answer  # noqa: E402
from asa.config import AGENCY_NAME, EMPLOYEES, EMPLOYEE_NAMES, PROGRAMS, WORK, SYNTHETIC_LABEL, now  # noqa: E402
from asa.db import df  # noqa: E402
from asa.kpis import agency_kpis, attendance_rate, funnel, group_fill, per_employee  # noqa: E402
from asa.ledger import PRIORITIES, STATUSES, create_task  # noqa: E402

st.set_page_config(page_title=AGENCY_NAME, page_icon="🎓", layout="wide")
USER = os.environ.get("ASA_BOSS_USER", "boss")
PASSWORD = os.environ.get("ASA_BOSS_PASSWORD", "change-me-demo")
SHEET_URL = os.environ.get("ASA_SHEET_URL", "")


def login() -> bool:
    if st.session_state.get("auth"):
        return True
    st.title(f"🎓 {AGENCY_NAME}")
    st.caption("Boss Command Center. Only the Boss can sign in.")
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Sign in"):
            if hmac.compare_digest(u, USER) and hmac.compare_digest(p, PASSWORD):
                st.session_state.auth = True
                st.rerun()
            st.error("Wrong username or password")
    return False


if not login():
    st.stop()

with st.sidebar:
    st.header("🎓 ASA Agency")
    st.caption(f"{now():%d %b %Y %H:%M} Riga")
    st.warning(SYNTHETIC_LABEL)
    if SHEET_URL:
        st.link_button("Open Google Sheet ledger", SHEET_URL)
    if st.button("▶ Run agency day (PM plans 13 tasks)"):
        plan_day("Boss (dashboard)")
        log = []
        process_queue(log=log.append)
        st.success(f"Processed {len(log)} tasks")
    if st.button("⚙ Process queued tasks"):
        log = []
        process_queue(log=log.append)
        st.success(f"Processed {len(log)} tasks")
    if st.button("Sign out"):
        st.session_state.auth = False
        st.rerun()

k = agency_kpis()
st.title(AGENCY_NAME)
cols = st.columns(8)
for c, (label, v) in zip(cols, [("Requests", k["applications_total"]), ("AI Club", k["requests_ai"]),
                                ("Chinese", k["requests_chinese"]), ("Placed", k["placed"]), ("In both", k["children_in_both"]),
                                ("Waitlist", k["waitlist"]), ("Group fill", f"{k['group_fill_pct']}%"),
                                ("Attendance", f"{k['attendance_pct']}%")]):
    c.metric(label, v)

tab_a, tab_b, tab_c, tab_d, tab_e = st.tabs(["A · Assign task", "B · Task board", "C · Reports", "D · Chat", "E · Employees"])

with tab_a:
    st.subheader("Assign a task to the Project Manager or any employee")
    with st.form("assign", clear_on_submit=True):
        c1, c2 = st.columns(2)
        title = c1.text_input("Title")
        agent = c2.selectbox("Employee", EMPLOYEE_NAMES)
        desc = st.text_area("Description")
        c3, c4 = st.columns(2)
        prio = c3.selectbox("Priority", PRIORITIES, index=1)
        due = c4.date_input("Deadline")
        go = st.form_submit_button("Assign")
    if go and title:
        tid = create_task(agent, title, desc or title, "freeform", prio, "Boss (dashboard)", str(due))
        st.success(f"{tid} queued for {agent}. Logged to the ledger.")
        if st.checkbox("Let the employee pick it up now", value=True):
            process_queue(log=lambda m: st.code(m))

with tab_b:
    t = df("SELECT * FROM tasks ORDER BY task_id DESC")
    f1, f2, f3, f4 = st.columns(4)
    fe = f1.multiselect("Employee", EMPLOYEE_NAMES)
    fs = f2.multiselect("Status", STATUSES)
    fp = f3.multiselect("Priority", PRIORITIES)
    fd = f4.date_input("Date", value=None)
    v = t.copy()
    if fe: v = v[v.agent_name.isin(fe)]
    if fs: v = v[v.status.isin(fs)]
    if fp: v = v[v.priority.isin(fp)]
    if fd: v = v[v.timestamp.str[:10] == str(fd)]
    c = st.columns(4)
    for col, s in zip(c, STATUSES):
        col.metric(s, int((t.status == s).sum()))
    st.dataframe(v[["task_id", "timestamp", "assigned_by", "agent_name", "title", "priority", "status", "output_link",
                    "completion_time", "deadline"]], width="stretch", hide_index=True)
    pick = st.selectbox("Task details", v.task_id.tolist())
    if pick:
        r = t[t.task_id == pick].iloc[0]
        st.json({k_: r[k_] for k_ in ["task_id", "agent_name", "title", "task_description", "priority", "status",
                                       "blocked_reason", "output_link", "timestamp", "started_at", "completion_time", "deadline"]})
        st.dataframe(df("SELECT timestamp, status, note FROM task_events WHERE task_id = ? ORDER BY id", (pick,)),
                     hide_index=True, width="stretch")
        out = WORK / str(r["output_link"])
        if r["output_link"] and out.is_file():
            st.code(out.read_text(errors="ignore")[:3000])

with tab_c:
    prog = st.radio("Program", ["All", "AI Club", "Chinese"], horizontal=True)
    pcode = {"AI Club": "AI", "Chinese": "ZH"}.get(prog)
    c1, c2 = st.columns(2)
    fn = funnel(pcode)
    fdf = pd.DataFrame({"Stage": ["Applied", "Passed QA", "Placed in group", "Confirmation drafted"],
                        "Count": [fn["Applied"], fn["Passed QA"], fn["Placed in group"], fn["Confirmation drafted"]]})
    c1.plotly_chart(px.funnel(fdf, x="Count", y="Stage", title="Enrolment funnel"), width="stretch")
    g = group_fill()
    g["Program"] = g.program.map(PROGRAMS)
    if pcode: g = g[g.program == pcode]
    c2.plotly_chart(px.bar(g, x="group_id", y=["enrolled", "capacity"], barmode="group", title="Group fill vs capacity",
                           hover_data=["band", "day", "time"]), width="stretch")
    a = df("SELECT program, source, status, band, submitted_at FROM applications")
    if pcode: a = a[a.program == pcode]
    c3, c4 = st.columns(2)
    c3.plotly_chart(px.pie(a, names="source", title="Where requests come from"), width="stretch")
    a["day"] = a.submitted_at.str[:10]
    daily = a.groupby(["day", "program"]).size().reset_index(name="requests")
    daily["program"] = daily.program.map(PROGRAMS)
    c4.plotly_chart(px.bar(daily, x="day", y="requests", color="program", title="Requests per day"), width="stretch")
    att = attendance_rate()
    if len(att):
        if pcode: att = att[att.program == pcode]
        st.plotly_chart(px.line(att, x="lesson_no", y="rate", color="group_id", markers=True,
                                title="Attendance rate by lesson (sample registers)"), width="stretch")
    st.subheader("Per-employee report")
    pe = per_employee()
    st.dataframe(pe, hide_index=True, width="stretch")
    st.plotly_chart(px.bar(pe, x="Employee", y=["Completed", "In Progress", "Queued", "Blocked"], title="Tasks by employee"),
                    width="stretch")
    st.subheader("Agency summary")
    wk = per_employee(7)
    s1, s2 = st.columns(2)
    s1.write("**Today**"); s1.json(k)
    s2.write("**Last 7 days, completed tasks**"); s2.dataframe(wk[["Employee", "Completed", "Blocked"]], hide_index=True)
    m = df("SELECT program, category, priority, status FROM messages")
    st.plotly_chart(px.histogram(m, x="category", color="status", title="Parent inbox triage"), width="stretch")
    st.download_button("⬇ Download task ledger (CSV)", df("SELECT * FROM tasks").to_csv(index=False), "ledger.csv")
    st.download_button("⬇ Download enrolment requests (CSV)", a.to_csv(index=False), "requests.csv")
    briefs = sorted((WORK / "reports").glob("daily_brief_*.html"))
    if briefs:
        st.download_button("⬇ Download latest daily brief (HTML)", briefs[-1].read_bytes(), briefs[-1].name)

with tab_d:
    who = st.selectbox("Chat with", EMPLOYEE_NAMES)
    hist = df("SELECT role, content, timestamp FROM chat_history WHERE channel = ? ORDER BY id", (who,))
    for r in hist.itertuples():
        with st.chat_message("user" if r.role == "boss" else "assistant"):
            st.write(r.content)
    q = st.chat_input(f"Ask the {who}…")
    if q:
        answer(q, who)
        st.rerun()

with tab_e:
    t = df("SELECT * FROM tasks")
    today = now().strftime("%Y-%m-%d")
    cols = st.columns(4)
    for i, e in enumerate(EMPLOYEES):
        mine = t[t.agent_name == e["name"]].sort_values("task_id")
        active = mine[mine.status == "In Progress"]
        current = active.iloc[-1].title if len(active) else (mine.iloc[-1].title if len(mine) else "none")
        out_today = int(((mine.status == "Completed") & (mine.completion_time.str[:10] == today)).sum())
        with cols[i % 4].container(border=True):
            st.markdown(f"**{e['name']}**  \n{e['title']}")
            st.write(("🟢 active" if len(active) else "⚪ idle") + f" · today's output: **{out_today}**")
            st.caption(f"Current / last task: {current}")
