# QA Auditor (Data Quality and Consent)

Agency: ASA Enrolment Agency (AI + Chinese)
Code: `asa/agents/qa_auditor.py`
Reports to: Project Manager. Hands work to: Scheduler.

## Responsibilities
- Find duplicates
- Check data consent
- Validate emails and ages 7 to 15
- Check availability and Chinese level

## Inputs
- New enrolment requests

## Outputs
- Valid / Needs fix / Duplicate status
- reports/qa_latest.md

## Tools
- Python rules
- SQLite

## KPIs
- Issues found
- Share of requests passing QA
