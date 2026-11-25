# Intake Officer (Applications Intake (AI + Chinese))

Agency: ASA Enrolment Agency (AI + Chinese)
Code: `asa/agents/intake.py`
Reports to: Project Manager. Hands work to: QA Auditor.

## Responsibilities
- Read the ASA registration form export
- Split 'both' into one AI and one Chinese request
- Compute age band (AI) or level band (Chinese)
- Import lesson registers

## Inputs
- Form CSV (Google Form export)
- Teacher registers

## Outputs
- Enrolment requests
- reports/intake_latest.json

## Tools
- Google Forms/Sheets CSV
- SQLite

## KPIs
- New requests per day
- Parse error rate
