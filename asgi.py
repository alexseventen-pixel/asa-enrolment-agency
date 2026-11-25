"""One web service: the Streamlit Boss dashboard at / and the public landing page at /apply.

Run: uvicorn asgi:app --host 0.0.0.0 --port $PORT
"""
from __future__ import annotations

import html
from pathlib import Path
from urllib.parse import parse_qs

import streamlit as st
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.routing import Route

from asa.config import LESSONS, PROGRAMS
from asa.webform import DAYS, submit, validate

ROOT = Path(__file__).resolve().parent
TEMPLATE = (ROOT / "web" / "landing.html").read_text(encoding="utf-8")
DAY_NAMES = {"Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday", "Thu": "Thursday", "Fri": "Friday"}


def render(values: dict | None = None, errors: list[str] | None = None, result: str = "") -> str:
    v = values or {}
    chosen = set((v.get("availability") or "").split(";"))
    out = TEMPLATE
    out = out.replace("{{AI_LESSONS}}", "".join(f"<li>{html.escape(t)}</li>" for _, t, _ in LESSONS["AI"]))
    out = out.replace("{{DAYS}}", "".join(
        f'<label><input type="checkbox" name="days" value="{d}"{" checked" if d in chosen else ""}> {DAY_NAMES[d]}</label>' for d in DAYS))
    out = out.replace("{{ERRORS}}", ('<div class="err"><b>Please check:</b><ul>' + "".join(
        f"<li>{html.escape(e)}</li>" for e in errors) + "</ul></div>") if errors else "")
    out = out.replace("{{RESULT}}", result)
    prog_back = {"AI": "ai", "Chinese": "chinese", "both": "both"}.get(v.get("program", ""), "")
    for k in ("parent_name", "parent_email", "parent_phone", "child_name", "age", "grade", "notes", "chinese_level"):
        out = out.replace("{{" + k + "}}", html.escape(str(v.get(k, "") or "")))
    return out.replace("{{program}}", prog_back)


def thank_you(res: dict) -> str:
    lines = []
    for r in res["requests"]:
        name = PROGRAMS.get(r["program"], r["program"])
        if r["group_id"]:
            lines.append(f"<li><b>{name}</b>: a place is reserved in group {r['group_id']} ({r['day']}). Time to be confirmed.</li>")
        elif r["status"] == "Waitlist":
            lines.append(f"<li><b>{name}</b>: groups on your days are full right now, so your child is on the waiting list. We will write when a place opens.</li>")
        else:
            lines.append(f"<li><b>{name}</b>: our team will check a detail with you ({html.escape(r['qa_flags'] or 'review')}).</li>")
    return (f'<div class="ok" id="apply"><h2>Thank you! Application {res["application_id"]} received.</h2>'
            f"<ul>{''.join(lines)}</ul><p><b>What happens next:</b> you will receive a confirmation email within 1 school day "
            "with the group, day and first lesson. Reply to that email if anything changes.</p></div>")


async def apply_get(request: Request):
    return HTMLResponse(render())


async def apply_post(request: Request):
    form = parse_qs((await request.body()).decode("utf-8", "replace"), keep_blank_values=True)
    data, errors = validate(form)
    if errors:
        return HTMLResponse(render(data, errors), status_code=422)
    res = await run_in_threadpool(submit, data)
    if request.headers.get("accept", "").startswith("application/json"):
        return JSONResponse(res)
    return HTMLResponse(render(result=thank_you(res)))


app = st.App(str(ROOT / "dashboard" / "app.py"), routes=[
    Route("/apply", apply_get, methods=["GET"]),
    Route("/apply", apply_post, methods=["POST"]),
    Route("/landing", lambda r: RedirectResponse("/apply"), methods=["GET"]),
])
