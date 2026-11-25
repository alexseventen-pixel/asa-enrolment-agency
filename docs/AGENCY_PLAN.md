# ASA Enrolment Agency: plan

**Client:** International School Premjers, Riga. After-school activities (ASA): AI Club and Chinese classes.
**Problem:** parents apply by email and phone, questions repeat, lesson days are forgotten, invoices are made by hand.
**Solution:** a small agency of 4 AI agents that share one database and one dashboard.

## The 4 agents

### 1. Applications: collect and process applications
* Input: the form on the public page `/apply`, the support chat, or a manual entry in the dashboard.
* Saves student, parent, programme, Chinese level and preferred days.
* Places the child: AI Club by age (7 to 9, 10 to 12, 13 to 15), Chinese by level and age. It picks the least full group on a preferred day and never puts two activities on the same day. If no place: waiting list.
* Immediately prepares the auto-reply email with the application ID, group, day and time.

### 2. Support: questions, enrolment, changes
* Chat on the public page and in the dashboard.
* Answers: prices, timetable, levels, ages, lesson topics, location, devices, missed lessons. Escalates to the teacher if asked.
* Enrols a child step by step (name, age, programme, level, days, parent, email, consent).
* With **email + application ID**: shows the enrolment, changes days, changes the Chinese level, cancels one programme or all (with a yes/no confirmation).
* Each change updates the database, drafts a confirmation email, voids unpaid invoices of cancelled enrolments, and offers the freed place to the first child on the waiting list.

### 3. Reminders: lesson reminders
* Button "Generate tomorrow's reminders" (or `POST /api/reminders/run`).
* For each active enrolment with a lesson tomorrow: email with day, time, group, lesson number and topic. Safe to run twice.

### 4. Accountant: invoices and summaries
* "Issue an invoice for a number of lessons": pick the student and programme, enter lessons and price per lesson (default placeholder, to be confirmed), optional period and note; total = lessons x price.
* "Issue monthly invoices": one invoice per active enrolment, number `INV-YYYYMM-001`, amount from the price list, status Unpaid, emailed as a draft.
* "Mark paid" / "Mark unpaid", printable invoice (HTML, print to PDF).
* Summary per programme: active, waiting list, cancelled, invoiced, paid, outstanding.

## Shared parts
* **Outbox:** every email from every agent, with preview. Sending is OFF (`ASA_ALLOW_SEND=no`) until the owner approves.
* **Ledger:** time, agent, action, result, for every step.
* **Data:** SQLite. Demo set: 6 synthetic students, clearly labelled.

## To be confirmed by the school
Prices (placeholders: AI Club 45 EUR, Chinese 40 EUR per month), timetable, room, payment details, Chinese syllabus.

## Flow
Parent applies on /apply or in the chat > Applications saves, places, auto-replies > Support handles questions and changes > Reminders emails the day before each lesson > Accountant invoices monthly and tracks payments > the dashboard shows it all.
