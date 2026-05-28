# Sales Demo Setup

Scripts and walkthroughs for preparing the AI Employee for a live sales demo to accounting firms.

## Prerequisites

- Docker Odoo running: `docker start odoo-postgres odoo-app` (port 8069)
- Odoo MCP running: `python mcp_servers/odoo_mcp.py` (port 8005)
- `.env` populated with `ODOO_URL`, `ODOO_DB`, `ODOO_USERNAME`, `ODOO_PASSWORD` (defaults: `http://localhost:8069` / `odoo` / `admin` / `admin`)

## 1. Seed demo data

```powershell
python scripts/seed_odoo_demo.py
```

What it creates (all tagged `[DEMO_SEED]` so easy to find/delete):

| Object | Items |
|---|---|
| Customers | Acme Corp, BlueSky Consulting LLC, Verdant Health |
| Products | Consulting Services ($150/hr), Monthly Bookkeeping ($500/mo) |
| Invoices | INV-001 ($750, overdue), INV-002 ($500, current), INV-003 ($1,500, overdue), INV-004 ($500, draft), INV-005 ($450, current) |
| Bank journal | "Bank Demo" |
| Bank statement | 3 deposit lines matching INV-001, INV-002, INV-005 (intentionally NOT INV-003) |

Script is **idempotent** — re-run any time to verify or reset partially. To fully reset: delete the `[DEMO_SEED]`-tagged records via Odoo UI (filter by name/narration), then re-run.

## 2. Wire Stripe to Odoo (programmatic, ~10 sec)

Why programmatic: faster than clicking, and reproducible across Odoo installs.

### Get test keys

1. Sign in to [https://dashboard.stripe.com](https://dashboard.stripe.com).
2. Toggle **TEST mode** in the top-right.
3. Developers → **API keys** → copy:
   - **Publishable key** (`pk_test_...`)
   - **Secret key** (`sk_test_...`)

### Configure via Python

Run this one-liner with your keys (replace the two values):

```powershell
python -c "
from scripts.seed_odoo_demo import OdooClient, ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS
c = OdooClient(ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS)
c.authenticate()
PK = 'pk_test_REPLACE_ME'
SK = 'sk_test_REPLACE_ME'
# Install the payment_stripe module (no-op if already installed)
mod = c.search_read('ir.module.module', [['name','=','payment_stripe']], fields=['id','state'], limit=1)[0]
if mod['state'] != 'installed':
    c.execute('ir.module.module', 'button_immediate_install', [mod['id']])
# Find Stripe provider and set keys + enable test mode
sid = c.search_read('payment.provider', [['code','=','stripe']], fields=['id'], limit=1)
if not sid:
    sid = c.search_read('payment.provider', [['name','=','Stripe']], fields=['id'], limit=1)
c.write('payment.provider', sid[0]['id'], {
    'stripe_publishable_key': PK,
    'stripe_secret_key': SK,
    'state': 'test',
    'is_published': True,  # critical: customer portal hides unpublished providers
})
print('Stripe configured (test mode, published).')
"
```

### Generate a customer pay URL for INV-004

```powershell
python -c "
from scripts.seed_odoo_demo import OdooClient, ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS
import uuid
c = OdooClient(ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS)
c.authenticate()
# Find INV-004 by ref, ensure posted, set an access token, print URL
inv = c.search_read('account.move', [['ref','=','INV-004']], fields=['id','state','access_token'], limit=1)[0]
if inv['state'] == 'draft':
    c.execute('account.move', 'action_post', [inv['id']])
tok = inv['access_token'] or (uuid.uuid4().hex + uuid.uuid4().hex)
if not inv['access_token']:
    c.write('account.move', inv['id'], {'access_token': tok})
print(f'Customer pay URL: {ODOO_URL}/my/invoices/{inv[\"id\"]}?access_token={tok}')
"
```

### Test the pay flow

1. Open the printed URL in any browser (no login required — it's a public customer link).
2. Click **Pay Now**.
3. Choose Stripe → use test card:
   - Number: `4242 4242 4242 4242`
   - Expiry: any future date (e.g. `12/30`)
   - CVC: any 3 digits (e.g. `123`)
   - ZIP: any 5 digits
4. Submit. Within ~30 seconds, Odoo marks INV-004 as **Paid**.

> ⚠️ Test mode only: the `pk_test_` / `sk_test_` keys ensure no real charges. Rotate the keys via Stripe Dashboard → Developers → API keys → "Roll" after demo prep is done — they may have leaked into chat transcripts during setup.

## 3. Run the live demo

After seed + Stripe are done, here are the three scenarios to walk through:

### Scenario A — Inbound payment reconciliation (the "wow" moment)

Drop this in `Needs_Action/accounting/`:

```markdown
# Customer paid — reconcile

BlueSky Consulting emailed saying they paid invoice INV-002 by
wire transfer yesterday. Please check the bank statement and
register the payment if you can confirm receipt.
```

> Note: don't include the dollar amount in the task body. Odoo applies sales tax automatically, so the invoice total may not match the "headline" amount you'd remember (e.g. INV-002 displays at $575 incl tax, not $500). The brain reads the invoice total directly from Odoo, so leaving the amount unspecified lets it figure things out.

Run:
```powershell
$env:LLM_BRAIN_PROVIDER = "openrouter"
$env:LLM_BRAIN_OPENROUTER_MODEL = "openai/gpt-oss-120b:free"
python run_brain_local.py --once --domain accounting
```

Expect: brain calls `odoo__get_invoices` (finds INV-002), `odoo__get_bank_statement_lines` (finds matching $500 deposit), then `approval__request_approval` for the payment registration. Task parks.

Approve:
```powershell
$body = '{"request_id":"<id from log>"}'
Invoke-WebRequest -Uri "http://localhost:8003/approve_action" -Method Post -Body $body -ContentType "application/json"
```

Re-run brain — it picks up the approval marker and calls `odoo__register_payment`. INV-002 flips to Paid.

### Scenario B — Suspicious claim with no matching deposit (the safety story)

Drop:

```markdown
# Customer paid — reconcile

Verdant Health emailed claiming they paid invoice INV-003.
Check the bank statement and register the payment if confirmed.
```

Expect: brain finds INV-003 (overdue, $1,500), checks bank statement, finds NO matching $1,500 deposit. Should NOT register payment. Should either flag for human review or draft a follow-up email asking for wire reference / proof of payment.

This is the "you can trust AI with money because it knows what it doesn't know" demo.

### Scenario C — Outbound invoice via Stripe

Drop:

```markdown
# Send invoice to Acme Corp

Confirm invoice INV-004 (monthly bookkeeping) and send it to Acme Corp
via email with a Stripe payment link so they can pay online.
```

Expect: brain confirms INV-004 in Odoo, sends with Stripe link. You then pretend to be the customer — open the link, pay with the `4242` card, Odoo auto-reconciles.

## Reset between demo runs

### Re-seed (idempotent — quick check)

```powershell
python scripts/seed_odoo_demo.py
```

Won't duplicate records. Bank statement is recreated each run (so if you changed deposit amounts, they refresh). Paid invoices stay paid.

### Reset a paid invoice back to "not paid" (e.g. between practice demos)

Quickest — Python one-liner. Cancels the payment + unreconciles:

```powershell
python -c "from scripts.seed_odoo_demo import OdooClient, ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS; c=OdooClient(ODOO_URL,ODOO_DB,ODOO_USER,ODOO_PASS); c.authenticate(); pays=c.search_read('account.payment',[['partner_id','=',64],['state','=','posted']],fields=['id'],limit=10); [c.execute('account.payment','action_cancel',[p['id']]) or c.execute('account.payment','unlink',[p['id']]) for p in pays]; print('Cancelled', len(pays), 'payments')"
```

(Replace `64` with another partner ID to reset for a different customer. Find partner IDs via `odoo__get_customers`.)

### Full nuke

For a totally fresh demo (delete all `[DEMO_SEED]`-tagged records):
1. In Odoo UI → Accounting → Customer Invoices
2. Filter by `[DEMO_SEED]` in narration
3. Select all → Action → Reset to Draft → Cancel → Delete
4. Repeat for Bank Statements
5. Re-run `seed_odoo_demo.py`

## Tips for the live demo

- **Pre-warm everything** 10 min before the call. First brain invocation always takes longer (model cold-start).
- **Have your phone on the desk** with WhatsApp open — the approval ping is the highest-impact visual.
- **Don't show the brain's terminal output** — it's noisy. Demo the vault folder + Odoo UI side-by-side instead.
- **If the model hesitates**, narrate: "It's reading the bank statement now to check if the payment actually arrived" — turns waiting into trust-building.
- **Have Scenario B in reserve** as the killer answer to "what if the AI makes a mistake?" — it doesn't, because it checks.
