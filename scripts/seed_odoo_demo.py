"""
Seed Odoo with demo data for AI Employee sales demos.

Creates 3 customers, 2 service products, 5 invoices (mixed states), and a
bank statement with deposits matching some invoices. Idempotent: re-running
skips records that already exist (matched by name for customers/products and
by a [DEMO_SEED] narration tag for invoices).

Usage:
    python scripts/seed_odoo_demo.py

Reads ODOO_URL/DB/USERNAME/PASSWORD from .env (defaults match the Docker
compose: http://localhost:8069, db=odoo, admin/admin).

The OdooClient class is copied from mcp_servers/odoo_mcp.py rather than
imported because that module starts a Flask app at import time.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

# Force UTF-8 stdout on Windows so the print summary doesn't crash on $/£/€
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

load_dotenv()

ODOO_URL = os.getenv("ODOO_URL", "http://localhost:8069").rstrip("/")
ODOO_DB = os.getenv("ODOO_DB", "odoo")
ODOO_USER = os.getenv("ODOO_USERNAME", "admin")
ODOO_PASS = os.getenv("ODOO_PASSWORD", "admin")

DEMO_TAG = "[DEMO_SEED]"


class OdooClient:
    """Minimal Odoo JSON-RPC client. Mirrors mcp_servers/odoo_mcp.py:OdooClient."""

    def __init__(self, url, db, username, password):
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.session = requests.Session()

    def authenticate(self):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {"db": self.db, "login": self.username, "password": self.password},
            "id": 1,
        }
        r = self.session.post(f"{self.url}/web/session/authenticate", json=payload, timeout=30)
        result = r.json().get("result") or {}
        if result.get("uid"):
            self.uid = result["uid"]
            return True
        # Fallback: API-key style auth
        payload["params"] = {"db": self.db, "login": self.username, "key": self.password}
        r = self.session.post(f"{self.url}/jsonrpc", json=payload, timeout=30)
        result = r.json().get("result")
        if result:
            self.uid = result
            return True
        return False

    def execute(self, model, method, *args, **kwargs):
        if not self.uid and not self.authenticate():
            raise RuntimeError("Odoo authentication failed")
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [self.db, self.uid, self.password, model, method, list(args), kwargs],
            },
            "id": 2,
        }
        r = self.session.post(f"{self.url}/jsonrpc", json=payload, timeout=60)
        body = r.json()
        if "error" in body:
            raise RuntimeError(f"Odoo error on {model}.{method}: {body['error'].get('data', body['error'])}")
        return body.get("result")

    def search_read(self, model, domain=None, fields=None, limit=80):
        return self.execute(model, "search_read", domain or [], fields=fields or [], limit=limit)

    def create(self, model, values):
        return self.execute(model, "create", values)

    def write(self, model, ids, values):
        if isinstance(ids, int):
            ids = [ids]
        return self.execute(model, "write", ids, values)

    def search(self, model, domain):
        return self.execute(model, "search", domain or [])


# ============================================================================
# Idempotent upserts
# ============================================================================

def upsert_customer(c, name, email):
    existing = c.search_read("res.partner", [["name", "=", name], ["customer_rank", ">", 0]], fields=["id"], limit=1)
    if existing:
        return existing[0]["id"], False
    cid = c.create("res.partner", {"name": name, "email": email, "customer_rank": 1})
    return cid, True


def upsert_product(c, name, price):
    existing = c.search_read("product.template", [["name", "=", name]], fields=["id"], limit=1)
    if existing:
        return existing[0]["id"], False
    pid = c.create(
        "product.template",
        {
            "name": name,
            "type": "service",
            "list_price": price,
            "sale_ok": True,
            "purchase_ok": False,
        },
    )
    return pid, True


def upsert_invoice(c, ref_tag, partner_id, product_template_id, qty, unit_price, invoice_date, due_date):
    """
    Idempotent on (partner, ref). ref_tag is 'INV-001' etc. — written to Odoo's
    `ref` field (Customer Reference) so the brain can look up invoices by their
    internal demo reference rather than Odoo's auto-generated sequence name
    (which is INV/YYYY/00XXX).

    Also writes [DEMO_SEED] INV-XXX to narration for legacy cleanup matching.
    """
    existing = c.search_read(
        "account.move",
        [
            ["partner_id", "=", partner_id],
            ["ref", "=", ref_tag],
            ["move_type", "=", "out_invoice"],
        ],
        fields=["id", "state", "name"],
        limit=1,
    )
    if existing:
        return existing[0]["id"], existing[0]["state"], False

    # Legacy: invoices created before we started writing ref. Match on narration.
    legacy_marker = f"{DEMO_TAG} {ref_tag}"
    legacy = c.search_read(
        "account.move",
        [
            ["partner_id", "=", partner_id],
            ["narration", "ilike", legacy_marker],
            ["move_type", "=", "out_invoice"],
            ["ref", "=", False],
        ],
        fields=["id", "state"],
        limit=1,
    )
    if legacy:
        # Backfill ref so future lookups work
        c.write("account.move", legacy[0]["id"], {"ref": ref_tag})
        return legacy[0]["id"], legacy[0]["state"], False

    # product.template.id != product.product.id — we need the product variant id
    product_product = c.search_read(
        "product.product", [["product_tmpl_id", "=", product_template_id]], fields=["id"], limit=1
    )
    if not product_product:
        raise RuntimeError(f"No product.product variant found for template {product_template_id}")
    product_id = product_product[0]["id"]

    invoice_values = {
        "move_type": "out_invoice",
        "partner_id": partner_id,
        "ref": ref_tag,
        "invoice_date": invoice_date,
        "invoice_date_due": due_date,
        "narration": f"{legacy_marker} — demo invoice seeded by scripts/seed_odoo_demo.py",
        "invoice_line_ids": [
            (
                0,
                0,
                {
                    "product_id": product_id,
                    "quantity": qty,
                    "price_unit": unit_price,
                    "name": ref_tag,
                },
            )
        ],
    }
    inv_id = c.create("account.move", invoice_values)
    return inv_id, "draft", True


def post_invoice(c, invoice_id):
    """Confirm/post an invoice (draft -> posted). No-op if already posted."""
    inv = c.search_read("account.move", [["id", "=", invoice_id]], fields=["state"], limit=1)
    if inv and inv[0]["state"] == "posted":
        return False
    c.execute("account.move", "action_post", [invoice_id])
    return True


# ============================================================================
# Bank journal + statement
# ============================================================================

def get_or_create_bank_journal(c, name="Bank Demo"):
    existing = c.search_read("account.journal", [["name", "=", name], ["type", "=", "bank"]], fields=["id"], limit=1)
    if existing:
        return existing[0]["id"], False
    # Minimum required: name, type, code. Code must be unique and <= 5 chars.
    jid = c.create("account.journal", {"name": name, "type": "bank", "code": "DEMO"})
    return jid, True


def recreate_demo_bank_statement(c, journal_id, statement_date, lines):
    """
    lines = [{"date": "YYYY-MM-DD", "payment_ref": "...", "amount": 500.0}, ...]

    Always deletes any existing [DEMO_SEED]-tagged statement on this journal and
    recreates it. This is seed data — recreation lets the script self-correct if
    invoice totals shift (e.g. due to tax-rate changes between runs).
    """
    statement_name = f"{DEMO_TAG} Bank Demo {statement_date}"

    # Delete any prior demo statements on this journal (and their lines via cascade)
    existing = c.search_read(
        "account.bank.statement",
        [["name", "ilike", DEMO_TAG], ["journal_id", "=", journal_id]],
        fields=["id"],
        limit=10,
    )
    if existing:
        old_ids = [s["id"] for s in existing]
        # Statement lines must be removed first if statement is "posted" — but on
        # newly-created statements they're draft. Try direct unlink; if blocked,
        # cancel first.
        try:
            c.execute("account.bank.statement", "unlink", old_ids)
        except Exception:
            # Best-effort: reset state and retry
            try:
                c.execute("account.bank.statement", "button_draft", old_ids)
            except Exception:
                pass
            c.execute("account.bank.statement", "unlink", old_ids)

    stmt_values = {
        "name": statement_name,
        "journal_id": journal_id,
        "date": statement_date,
        "line_ids": [
            (
                0,
                0,
                {
                    "date": line["date"],
                    "payment_ref": line["payment_ref"],
                    "amount": line["amount"],
                    "journal_id": journal_id,
                },
            )
            for line in lines
        ],
    }
    sid = c.create("account.bank.statement", stmt_values)
    return sid, True


def get_invoice_total(c, invoice_id):
    """Return amount_total of an invoice (tax-inclusive)."""
    rec = c.search_read("account.move", [["id", "=", invoice_id]], fields=["amount_total"], limit=1)
    return rec[0]["amount_total"] if rec else 0.0


# ============================================================================
# Main
# ============================================================================

def ensure_accounting_groups(c):
    """
    Bank statements need 'Show Full Accounting Features' (account.group_account_manager).
    Grant it to the current user if missing. Idempotent.
    """
    target_xmlids = [
        ("account", "group_account_manager"),   # Show Full Accounting Features
        ("account", "group_account_user"),      # Billing
    ]
    user_groups = c.search_read("res.users", [["id", "=", c.uid]], fields=["groups_id"], limit=1)
    current_group_ids = set(user_groups[0]["groups_id"]) if user_groups else set()

    to_add = []
    for module, name in target_xmlids:
        rec = c.search_read(
            "ir.model.data",
            [["module", "=", module], ["name", "=", name]],
            fields=["res_id"],
            limit=1,
        )
        if not rec:
            continue
        gid = rec[0]["res_id"]
        if gid not in current_group_ids:
            to_add.append((4, gid))

    if to_add:
        c.write("res.users", c.uid, {"groups_id": to_add})
        print(f"  Granted {len(to_add)} accounting group(s) to uid={c.uid}")
    else:
        print(f"  Accounting groups already in place for uid={c.uid}")


def main():
    print(f"Connecting to Odoo at {ODOO_URL} db={ODOO_DB} as {ODOO_USER}...")
    c = OdooClient(ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS)
    if not c.authenticate():
        print("ERROR: Could not authenticate with Odoo")
        sys.exit(1)
    print(f"  Authenticated. uid={c.uid}")
    ensure_accounting_groups(c)
    print()

    today = datetime.now().date()
    iso = lambda d: d.isoformat()

    # ---------- Customers ----------
    print("Customers:")
    customers = {}
    for name, email in [
        ("Acme Corp", "billing@acmecorp.com"),
        ("BlueSky Consulting LLC", "accounts@blueskyllc.com"),
        ("Verdant Health", "ap@verdanthealth.com"),
    ]:
        cid, created = upsert_customer(c, name, email)
        customers[name] = cid
        print(f"  {'+ created' if created else '= existing'}  {name:30}  id={cid}")

    # ---------- Products ----------
    print("\nProducts:")
    products = {}
    for name, price in [("Consulting Services", 150.00), ("Monthly Bookkeeping", 500.00)]:
        pid, created = upsert_product(c, name, price)
        products[name] = pid
        print(f"  {'+ created' if created else '= existing'}  {name:30}  template_id={pid}")

    # ---------- Invoices ----------
    print("\nInvoices:")
    invoice_specs = [
        # (ref_tag, customer, product, qty, unit_price, invoice_date, due_date, post?)
        ("INV-001", "Acme Corp",              "Consulting Services", 5,  150.00, iso(today - timedelta(days=45)), iso(today - timedelta(days=15)), True),
        ("INV-002", "BlueSky Consulting LLC", "Monthly Bookkeeping", 1,  500.00, iso(today - timedelta(days=10)), iso(today + timedelta(days=20)), True),
        ("INV-003", "Verdant Health",         "Consulting Services", 10, 150.00, iso(today - timedelta(days=60)), iso(today - timedelta(days=30)), True),
        ("INV-004", "Acme Corp",              "Monthly Bookkeeping", 1,  500.00, iso(today),                       iso(today + timedelta(days=30)), False),  # keep draft
        ("INV-005", "BlueSky Consulting LLC", "Consulting Services", 3,  150.00, iso(today - timedelta(days=5)),  iso(today + timedelta(days=25)), True),
    ]
    invoices = {}
    for ref, cust_name, prod_name, qty, price, inv_date, due_date, should_post in invoice_specs:
        inv_id, state, created = upsert_invoice(
            c, ref, customers[cust_name], products[prod_name], qty, price, inv_date, due_date
        )
        invoices[ref] = inv_id
        if created and should_post:
            posted = post_invoice(c, inv_id)
            state = "posted" if posted else state
        flag = "+ created" if created else "= existing"
        print(f"  {flag}  {ref}  cust={cust_name:25} ${qty*price:>8.2f}  state={state}  id={inv_id}")

    # ---------- Bank journal + statement ----------
    print("\nBank journal:")
    journal_id, created = get_or_create_bank_journal(c, name="Bank Demo")
    print(f"  {'+ created' if created else '= existing'}  Bank Demo  journal_id={journal_id}")

    # Pull actual invoice totals so deposit amounts match exactly (handles
    # Odoo's auto-applied sales tax — without this, AI can't reconcile).
    inv001_total = get_invoice_total(c, invoices["INV-001"])
    inv002_total = get_invoice_total(c, invoices["INV-002"])
    inv005_total = get_invoice_total(c, invoices["INV-005"])

    print("\nBank statement:")
    stmt_date = iso(today - timedelta(days=2))
    # Include invoice references in payment_ref so LLMs can disambiguate
    # cleanly when multiple deposits exist for the same customer. Realistic:
    # actual wire transfers commonly carry the originator's invoice number.
    line_specs = [
        {"date": stmt_date, "payment_ref": "WIRE BlueSky Consulting LLC re INV-002",  "amount": inv002_total},
        {"date": stmt_date, "payment_ref": "ACH Acme Corp re INV-001",                "amount": inv001_total},
        {"date": stmt_date, "payment_ref": "WIRE BlueSky Consulting LLC re INV-005",  "amount": inv005_total},
    ]
    sid, created = recreate_demo_bank_statement(c, journal_id, stmt_date, line_specs)
    print(f"  + recreated  statement_id={sid}  lines:")
    for spec in line_specs:
        print(f"               ${spec['amount']:>8.2f}  {spec['payment_ref']}")

    # ---------- Summary ----------
    print("\n" + "=" * 70)
    print("DEMO READY")
    print("=" * 70)
    print(f"\nOdoo URL:  {ODOO_URL}  (admin / admin)")
    inv002_total = get_invoice_total(c, invoices["INV-002"])
    inv003_total = get_invoice_total(c, invoices["INV-003"])
    print(f"\nDemo scenarios you can run with the brain:")
    print(f"\n  Scenario A — INBOUND payment reconciliation (the 'wow' demo)")
    print(f"    Task body: 'BlueSky Consulting emailed saying they paid invoice")
    print(f"               INV-002 by wire transfer. Check the bank statement")
    print(f"               and register the payment if you can confirm receipt.'")
    print(f"    Expected:  brain finds INV-002 (id={invoices['INV-002']}, total ${inv002_total:.2f}),")
    print(f"               finds matching deposit on bank statement, requests approval,")
    print(f"               you approve, INV-002 flips to paid.")
    print(f"\n  Scenario B — OVERDUE invoice with NO matching deposit (the safety demo)")
    print(f"    Task body: 'Verdant Health emailed claiming they paid invoice")
    print(f"               INV-003. Check the bank statement and register if confirmed.'")
    print(f"    Expected:  brain finds INV-003 (id={invoices['INV-003']}, total ${inv003_total:.2f}),")
    print(f"               finds NO matching deposit, declines to register, drafts a")
    print(f"               follow-up asking for wire reference / proof of payment.")
    print(f"\n  Scenario C — OUTBOUND invoice + Stripe (after Stripe is wired)")
    print(f"    Task body: 'Send invoice INV-004 to Acme Corp.'")
    print(f"    Expected:  brain confirms invoice INV-004 (id={invoices['INV-004']}) and")
    print(f"               sends via email with Stripe payment link; customer pays via")
    print(f"               4242 4242 4242 4242 test card; Odoo auto-reconciles as paid.")
    print(f"\nReset:  delete records via Odoo UI or re-run this script (idempotent).")
    print(f"Stripe: see scripts/README_demo.md for the manual UI walkthrough.\n")


if __name__ == "__main__":
    main()
