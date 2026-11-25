# Project Manager (Chief of Staff)

Agency: ASA Enrolment Agency (AI + Chinese)
Code: `asa/agents/project_manager.py`
Reports to: Boss (Oleg). Hands work to: All 7 employees.

## Responsibilities
- Plan the daily task list and dispatch it
- Audit all 7 employees
- Keep the Google Sheet ledger
- Draft the daily brief email to the Boss
- Answer the Boss in chat from real data

## Inputs
- Boss tasks (dashboard, chat, terminal)
- Ledger and database

## Outputs
- Ledger rows
- Daily brief (.eml/.html)
- Chat answers

## Tools
- Google Sheets
- Email (SMTP, approval gated)
- SQLite

## KPIs
- Tasks completed per day
- Blocked tasks resolved
- Brief delivered daily
