# Screen recording script (target 10 to 12 minutes)

Before recording: close other tabs, open a terminal in the project folder, open the Google Sheet
(https://docs.google.com/spreadsheets/d/1hIQ5si4Ya7gvfI1CHnbQ32s7eJNiYLCB-1XAuZwPBjA/edit) and have the dashboard URL ready. Say once at the start: "All children and parents in this demo are
synthetic sample data."

| Time | Show | Say / do |
|---|---|---|
| 0:00 | Title slide or README | "ASA Enrolment Agency: 8 AI employees run enrolment for two after-school programs, AI Club and Chinese." |
| 0:45 | docs/workflow.svg | Walk the flow: Boss, Project Manager, 7 employees, ledger, daily brief, approval gate. |
| 1:30 | `employees/` folder, `.installed.json` | Show one employee.json, ROLE.md and the receipt hashes (ai-employees style). |
| 2:30 | Terminal: `python scripts/run_pipeline.py --reset --delay 0.5` | Watch 13 tasks go Queued, In Progress, Completed. Point at T-0007 Blocked: emails wait for approval. |
| 4:00 | Terminal: `ls outbox/*`, open one confirmation .html and the daily brief | Show per-program templates (AI vs Chinese) and the brief sections. |
| 5:00 | Google Sheet: Ledger tab, then Dashboard tab | Same task IDs as the terminal. Dashboard formulas and 5 charts. |
| 6:00 | Dashboard: login page | Sign in with the test credentials. |
| 6:30 | Tab A: assign a task to the Project Manager ("Daily brief") and one to the Content Writer | Tick "pick up now". Show the new rows in the ledger. |
| 7:30 | Tab B: task board | Filter by employee and status, open a task, show its events (Queued, In Progress, Completed). |
| 8:30 | Tab C: reports | Switch program filter All / AI Club / Chinese. Download the CSV. |
| 9:30 | Tab D: chat with Project Manager | Ask the 6 required questions (below). Show that the chat created a task. |
| 11:00 | Tab E: employee cards | Active or idle, current task, today's output. |
| 11:30 | Wrap up | What is real (pipeline, ledger, dashboard, chat), what is next (real form, approved sending). |

Chat questions to type:
1. How many tasks are currently running?
2. What is the status of the sales team? How many leads were generated today? Give me the details.
   (In this agency "sales" means enrolment requests.)
3. How many posts were published today, and on which platforms?
4. Which tasks are blocked, and why?
5. Which employee completed the most tasks this week?
6. Assign a new task to the Content Writer: write 3 LinkedIn posts about our new service, due tomorrow.
