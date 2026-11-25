# ASA Enrolment Agency

A simple AI agency for the after-school **AI Club** and **Chinese classes** at International School Premjers, Riga.
It has exactly **4 agents**, a public application page with a support chat, and one dashboard.

Live demo: https://asa-enrolment-agency.onrender.com (dashboard) and https://asa-enrolment-agency.onrender.com/apply (public page).

| # | Agent | What it does | Where to use it |
|---|-------|--------------|-----------------|
| 1 | **Applications** | Saves each application (child, parent, programme, level, days), places the child in a group by age or level and preferred days (never two activities on one day, waiting list when full), and immediately prepares the auto-reply confirmation email with the application ID. | Form on `/apply`, the chat, or "Add an application by hand" in tab 1 |
| 2 | **Support** | Chat for parents: answers questions (prices, timetable, levels, ages, lessons, location), enrols a child step by step, and after checking **email + application ID** changes days, changes the Chinese level, or cancels. Every change updates the database, drafts a confirmation email, and offers freed places to the waiting list. | Chat bubble on `/apply`, tab 2 in the dashboard |
| 3 | **Reminders** | For every child with a lesson tomorrow, prepares a reminder email with day, time, group and lesson topic. No duplicates. | Button "Generate tomorrow's reminders" in tab 3 |
| 4 | **Accountant** | Issues one monthly invoice per active enrolment (number, amount, Unpaid/Paid), emails it as a draft, marks paid, gives a printable invoice, and shows the summary: enrolments, invoiced, paid, outstanding per programme. | Tab 4 |

Plus an **Outbox** tab (every email, with preview) and a **Ledger** tab (time, agent, action, result).

## Important

* **No email is sent.** `ASA_ALLOW_SEND=no`: all emails are drafts in the Outbox and `.eml` files.
* **Placeholders, to be confirmed:** prices (AI Club 45 EUR, Chinese 40 EUR per month, set in `asa/config.py` or env), the timetable, the room, payment details, Chinese lesson topics.
* **Demo data is synthetic** ("Demo Child ...", `@example.com`). Load it with the sidebar button or `ASA_DEMO=yes`.
* The support chat is rule based (no API key needed), so it gives the same reliable answer every time.

## Run locally

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python scripts/run_pipeline.py --reset --demo      # optional: fresh DB with demo data
uvicorn asgi:app --port 8000                       # dashboard at /, landing page at /apply
python tests/test_flow.py                          # end to end test of the 4 agents
```

On Render the start command is `python scripts/run_pipeline.py --reset && ...` with `ASA_SERVE_ASGI=yes`, which makes the script start uvicorn.

## HTTP API (used for testing)

| Method | Path | |
|---|---|---|
| POST | `/apply` | application form (`Accept: application/json` returns JSON) |
| POST | `/api/support` | `{"session_id": "...", "message": "..."}` returns `{"reply": "..."}` |
| POST | `/api/reminders/run` | Reminders agent for tomorrow |
| POST | `/api/invoices/run` | Accountant: invoices for this month |
| POST | `/api/invoices/{no}/paid` | mark paid |
| GET | `/api/summary`, `/api/outbox`, `/api/ledger`, `/api/enrolment/{id}`, `/invoice/{no}` | read data |

If `ASA_ADMIN_TOKEN` is set, all of these except `/apply` and `/api/support` need the header `X-Admin-Token`.

## Files

```
asa/config.py            all settings: programmes, groups, prices (placeholders), lessons
asa/db.py                SQLite: students, enrolments, emails, invoices, ledger, chats
asa/mailer.py            outbox (drafts, sending off)
asa/agents/applications.py, support.py, reminders.py, accountant.py
asa/demo.py              6 synthetic demo students
asgi.py                  web service: dashboard + /apply + APIs
dashboard/app.py         Streamlit dashboard (4 agent tabs, Outbox, Ledger)
web/landing.html         public page with form and chat
```

## Limits

* Render free plan: the SQLite database resets on every restart or deploy, and the service sleeps after about 15 minutes idle (first open takes 30 to 60 seconds).
* Reminders run by the button (a Render cron job is not free and could not share the database).
* Payment is marked by hand; there is no bank or card integration.
