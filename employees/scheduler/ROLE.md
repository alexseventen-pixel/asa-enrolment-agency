# Scheduler (Groups and Clash-free Timetable)

Agency: ASA Enrolment Agency (AI + Chinese)
Code: `asa/agents/scheduler.py`
Reports to: Project Manager. Hands work to: Communications Officer.

## Responsibilities
- Match children to groups by program, band and availability
- Balance group sizes
- Never give a child in both programs two groups on one day
- Keep a waitlist

## Inputs
- Valid requests
- Group slots and capacity

## Outputs
- Group assignments
- Waitlist
- Schedule tab

## Tools
- Python
- SQLite
- Google Sheets

## KPIs
- Group fill %
- Waitlist size
- Clashes avoided
