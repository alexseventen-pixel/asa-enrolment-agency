"""One web service: the Streamlit dashboard at / , the public landing page at /apply,
the support chat API and a few admin APIs (protected by ASA_ADMIN_TOKEN when it is set).

Run: uvicorn asgi:app --host 0.0.0.0 --port $PORT
"""
from __future__ import annotations

import html
import os
from pathlib import Path
from urllib.parse import parse_qs

import streamlit as st
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.routing import Route

from asa.agents import accountant, applications, reminders, support
from asa.config import DAY_NAMES, DAYS, LESSONS, PROGRAMS
from asa.db import df

ROOT = Path(__file__).resolve().parent
TEMPLATE = (ROOT / "web" / "landing.html").read_text(encoding="utf-8")
PROG_FORM = {"ai": "ai", "chinese": "chinese", "both": "both"}


def render(v: dict | None = None, errors: list[str] | None = None, result: str = "") -> str:
    v = v or {}
    chosen = set(v.get("days", []))
    out = TEMPLATE.replace("{{AI_LESSONS}}", "".join(f"<li>{html.escape(t)}</li>" for t in LESSONS["AI"]))
    out = out.replace("{{DAYS}}", "".join(
        f'<label><input type="checkbox" name="days" value="{d}"{" checked" if d in chosen else ""}> {DAY_NAMES[d]}</label>' for d in DAYS))
    out = out.replace("{{ERRORS}}", ('<div class="err"><b>Please check:</b><ul>' + "".join(
        f"<li>{html.escape(e)}</li>" for e in errors) + "</ul></div>") if errors else "")
    out = out.replace("{{RESULT}}", result)
    for k in ("parent_name", "parent_email", "parent_phone", "child_name", "age", "grade", "notes"):
        out = out.replace("{{" + k + "}}", html.escape(str(v.get(k, "") or "")))
    out = out.replace("{{chinese_level}}", html.escape(v.get("level", "")))
    return out.replace("{{program}}", PROG_FORM.get(str(v.get("program", "")).lower(), ""))


def thank_you(res: dict) -> str:
    lines = []
    for r in res["enrolments"]:
        if r["group"]:
            lines.append(f"<li><b>{r['program']}</b>: place reserved in group {r['group']} ({DAY_NAMES[r['day']]}).</li>")
        else:
            lines.append(f"<li><b>{r['program']}</b>: groups on your days are full, so your child is on the waiting list.</li>")
    return (f'<div class="ok" id="apply"><h2>Thank you! Application {res["application_id"]} received.</h2><ul>{"".join(lines)}</ul>'
            "<p>A confirmation email with these details has been prepared for you automatically. "
            f"Keep your application ID <b>{res['application_id']}</b>: with it and your email you can change days or cancel in the <a href="#ask">support chat</a>.</p></div>")


def form_data(form: dict) -> dict:
    g = lambda k: (form.get(k) or [""])[0].strip()  # noqa: E731
    return {"parent_name": g("parent_name"), "parent_email": g("parent_email"), "parent_phone": g("parent_phone"),
            "child_name": g("child_name"), "age": g("age"), "grade": g("grade"), "program": g("program"),
            "level": g("chinese_level"), "days": form.get("days", []), "notes": g("notes"),
            "consent": g("consent") == "yes", "consent_photo": g("consent_photo") == "yes", "test": g("test") == "yes"}


async def apply_get(request: Request):
    return HTMLResponse(render())


async def apply_post(request: Request):
    data = form_data(parse_qs((await request.body()).decode("utf-8", "replace"), keep_blank_values=True))
    errors = applications.validate(data)
    if errors:
        return HTMLResponse(render(data, errors), status_code=422)
    res = await run_in_threadpool(applications.submit, data)
    if request.headers.get("accept", "").startswith("application/json"):
        return JSONResponse(res)
    return HTMLResponse(render(result=thank_you(res)))


async def api_support(request: Request):
    body = await request.json()
    sid = str(body.get("session_id") or "anon")[:40]
    text = await run_in_threadpool(support.reply, sid, str(body.get("message", "")))
    return JSONResponse({"reply": text})


def admin(fn):
    async def wrapped(request: Request):
        token = os.environ.get("ASA_ADMIN_TOKEN", "")
        if token and request.headers.get("x-admin-token") != token and request.query_params.get("token") != token:
            return JSONResponse({"error": "admin token required"}, status_code=401)
        return await fn(request)
    return wrapped


@admin
async def api_reminders(request: Request):
    return JSONResponse(await run_in_threadpool(reminders.run))


@admin
async def api_invoices(request: Request):
    return JSONResponse(await run_in_threadpool(accountant.issue))


@admin
async def api_paid(request: Request):
    no = request.path_params["no"]
    return JSONResponse({"invoice_no": no, "paid": await run_in_threadpool(accountant.mark_paid, no)})


@admin
async def api_summary(request: Request):
    return JSONResponse(await run_in_threadpool(accountant.summary))


@admin
async def api_outbox(request: Request):
    d = await run_in_threadpool(df, "SELECT email_id, created_at, agent, kind, application_id, to_addr, subject, status FROM emails ORDER BY email_id DESC LIMIT 50")
    return JSONResponse(d.to_dict("records"))


@admin
async def api_enrolment(request: Request):
    aid = request.path_params["aid"]
    s = await run_in_threadpool(df, "SELECT * FROM students WHERE application_id = ?", (aid,))
    e = await run_in_threadpool(df, "SELECT * FROM enrolments WHERE application_id = ?", (aid,))
    return JSONResponse({"student": s.to_dict("records"), "enrolments": e.to_dict("records")})


@admin
async def api_ledger(request: Request):
    d = await run_in_threadpool(df, "SELECT * FROM ledger ORDER BY id DESC LIMIT 50")
    return JSONResponse(d.to_dict("records"))


@admin
async def invoice_page(request: Request):
    page = await run_in_threadpool(accountant.invoice_html, request.path_params["no"])
    return HTMLResponse(page) if page else HTMLResponse("Invoice not found", status_code=404)


app = st.App(str(ROOT / "dashboard" / "app.py"), routes=[
    Route("/apply", apply_get, methods=["GET"]),
    Route("/apply", apply_post, methods=["POST"]),
    Route("/landing", lambda r: RedirectResponse("/apply"), methods=["GET"]),
    Route("/api/support", api_support, methods=["POST"]),
    Route("/api/reminders/run", api_reminders, methods=["POST"]),
    Route("/api/invoices/run", api_invoices, methods=["POST"]),
    Route("/api/invoices/{no}/paid", api_paid, methods=["POST"]),
    Route("/api/summary", api_summary, methods=["GET"]),
    Route("/api/outbox", api_outbox, methods=["GET"]),
    Route("/api/ledger", api_ledger, methods=["GET"]),
    Route("/api/enrolment/{aid}", api_enrolment, methods=["GET"]),
    Route("/invoice/{no}", invoice_page, methods=["GET"]),
])
