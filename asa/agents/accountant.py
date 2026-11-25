"""Agent 4. Accountant: issues a monthly invoice per active enrolment, emails it as a draft,
marks invoices paid, and produces the summary (enrolments, invoiced, paid, outstanding)."""
from __future__ import annotations

import html

from ..config import AGENCY_NAME, CLUB_EMAIL, CURRENCY, PRICE_NOTE, PRICES, PROGRAMS, SCHOOL, now, ts
from ..db import df, log, next_id, session
from ..mailer import draft

AGENT = "Accountant"


def issue(period: str | None = None) -> dict:
    """One invoice per active enrolment per month. Running twice does not duplicate."""
    period = period or now().strftime("%Y-%m")
    created = []
    with session() as con:
        rows = con.execute("SELECT e.*, s.child_name, s.parent_name, s.parent_email FROM enrolments e JOIN students s USING (application_id)"
                           " WHERE e.status = 'Active' AND e.enrolment_id NOT IN (SELECT enrolment_id FROM invoices WHERE period = ?)"
                           " ORDER BY e.enrolment_id", (period,)).fetchall()
    for e in rows:
        with session() as con:
            no = next_id(con, "invoices", "invoice_no", f"INV-{period.replace('-', '')}-", 3)
            amount = PRICES[e["program"]]
            con.execute("INSERT INTO invoices VALUES (?,?,?,?,?,?,?,?,?)",
                        (no, ts(), e["application_id"], e["enrolment_id"], e["program"], period, amount, "Unpaid", ""))
        body = (f"<p>Dear {e['parent_name']},</p><p>Please find invoice <b>{no}</b> for <b>{e['child_name']}</b>, "
                f"{PROGRAMS[e['program']]}, {period}: <b>{amount:.2f} {CURRENCY}</b>{PRICE_NOTE}.</p>"
                "<p>Payment details are to be confirmed by the school office.</p><p>ASA team</p>")
        draft(AGENT, "Invoice", e["application_id"], e["parent_email"], f"Invoice {no}: {PROGRAMS[e['program']]} {period}", body)
        created.append({"invoice_no": no, "application_id": e["application_id"], "child": e["child_name"],
                        "program": PROGRAMS[e["program"]], "amount": amount})
    total = sum(c["amount"] for c in created)
    log(AGENT, f"Issued invoices for {period}", f"{len(created)} invoice(s), {total:.2f} {CURRENCY}, emailed as drafts")
    return {"period": period, "created": created, "total": total}


def mark_paid(invoice_no: str, paid: bool = True) -> bool:
    with session() as con:
        cur = con.execute("UPDATE invoices SET status = ?, paid_at = ? WHERE invoice_no = ? AND status IN ('Unpaid', 'Paid')",
                          ("Paid" if paid else "Unpaid", ts() if paid else "", invoice_no))
        ok = cur.rowcount == 1
    if ok:
        log(AGENT, f"Marked {invoice_no} {'paid' if paid else 'unpaid'}", "Summary updated")
    return ok


def invoices():
    return df("SELECT i.invoice_no, i.issued_at, i.application_id, s.child_name, s.parent_email, i.program, i.period,"
              " i.amount, i.status, i.paid_at FROM invoices i JOIN students s USING (application_id) ORDER BY i.invoice_no")


def summary() -> dict:
    with session() as con:
        rows = []
        for p, name in PROGRAMS.items():
            q = lambda sql: con.execute(sql, (p,)).fetchone()[0] or 0  # noqa: E731
            rows.append({
                "programme": name,
                "active": q("SELECT COUNT(*) FROM enrolments WHERE program = ? AND status = 'Active'"),
                "waitlist": q("SELECT COUNT(*) FROM enrolments WHERE program = ? AND status = 'Waitlist'"),
                "cancelled": q("SELECT COUNT(*) FROM enrolments WHERE program = ? AND status = 'Cancelled'"),
                "invoiced": float(q("SELECT SUM(amount) FROM invoices WHERE program = ? AND status != 'Void'")),
                "paid": float(q("SELECT SUM(amount) FROM invoices WHERE program = ? AND status = 'Paid'")),
            })
        students = con.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    for r in rows:
        r["outstanding"] = r["invoiced"] - r["paid"]
    tot = {k: sum(r[k] for r in rows) for k in ("active", "waitlist", "cancelled", "invoiced", "paid", "outstanding")}
    return {"students": students, "by_programme": rows, "total": tot, "currency": CURRENCY, "price_note": PRICE_NOTE.strip()}


def invoice_html(invoice_no: str) -> str | None:
    with session() as con:
        r = con.execute("SELECT i.*, s.child_name, s.parent_name, s.parent_email FROM invoices i JOIN students s USING (application_id)"
                        " WHERE invoice_no = ?", (invoice_no,)).fetchone()
    if not r:
        return None
    e = {k: html.escape(str(r[k])) for k in r.keys()}
    colour = {"Paid": "#1a7f37", "Unpaid": "#b54708", "Void": "#888"}.get(r["status"], "#333")
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Invoice {e['invoice_no']}</title>
<style>body{{font-family:Arial,sans-serif;max-width:720px;margin:40px auto;color:#1d2433;padding:0 16px}}
table{{width:100%;border-collapse:collapse;margin:24px 0}}td,th{{border-bottom:1px solid #ddd;padding:10px;text-align:left}}
.st{{color:{colour};font-weight:bold;border:2px solid {colour};padding:4px 10px;border-radius:6px}}
.note{{color:#777;font-size:12px}}@media print{{.np{{display:none}}}}</style></head><body>
<h1>Invoice {e['invoice_no']} <span class="st">{e['status']}</span></h1>
<p><b>{AGENCY_NAME}</b><br>{SCHOOL}<br>{CLUB_EMAIL}</p>
<p><b>Bill to:</b> {e['parent_name']} ({e['parent_email']})<br><b>Student:</b> {e['child_name']} ({e['application_id']})<br>
<b>Issued:</b> {e['issued_at'][:10]} &nbsp; <b>Period:</b> {e['period']}</p>
<table><tr><th>Description</th><th>Amount</th></tr>
<tr><td>{PROGRAMS[r['program']]}, monthly fee, {e['period']}</td><td>{r['amount']:.2f} {CURRENCY}</td></tr>
<tr><th>Total</th><th>{r['amount']:.2f} {CURRENCY}</th></tr></table>
<p>{'Paid on ' + e['paid_at'][:10] if r['status'] == 'Paid' else 'Payment details: to be confirmed by the school office.'}</p>
<p class="note">Prices{PRICE_NOTE}. Generated by the Accountant agent.</p>
<button class="np" onclick="window.print()">Print / Save as PDF</button></body></html>"""
