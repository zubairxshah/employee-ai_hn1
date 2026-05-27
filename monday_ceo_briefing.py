"""
Monday Morning CEO Briefing Generator
Automated weekly revenue report with Odoo + Bank Transactions integration

Generates every Monday at 8 AM via email
"""

import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Configuration
VAULT_PATH = r"D:\prompteng\AI_Employee_Vault"
ODOO_MCP_URL = "http://localhost:8005"
EMAIL_MCP_URL = "http://localhost:8001"

# CEO email address (from .env or config)
CEO_EMAIL = os.getenv('GMAIL_ADDRESS', 'emaxis.newsletter@gmail.com')

# Business goals
MONTHLY_REVENUE_GOAL = 10000.00  # From Business_Goals.md


class MondayBriefingGenerator:
    """
    Generates Monday Morning CEO Briefing with:
    - Revenue summary (Odoo invoices + Bank transactions)
    - Outstanding payments
    - New customers acquired
    - Week-over-week comparison
    - Action items
    """

    def __init__(self):
        self.vault_path = Path(VAULT_PATH)
        self.briefings_dir = self.vault_path / "Briefings"
        self.briefings_dir.mkdir(parents=True, exist_ok=True)

    def get_odoo_revenue_summary(self, date_from: str = None, date_to: str = None) -> Dict:
        """
        Get revenue summary from Odoo

        Returns:
        - Total invoiced
        - Total paid
        - Outstanding
        - Invoice count
        """
        if date_from is None:
            # Default: Last 7 days
            date_from = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        if date_to is None:
            date_to = datetime.now().strftime('%Y-%m-%d')

        try:
            response = requests.post(
                f"{ODOO_MCP_URL}/get_financial_summary",
                json={'date_from': date_from, 'date_to': date_to},
                timeout=30
            )
            result = response.json()

            if result.get('success'):
                summary = result.get('summary', {})
                receivables = summary.get('receivables', {})

                return {
                    'total_invoiced': receivables.get('total_invoiced', 0),
                    'total_outstanding': receivables.get('total_outstanding', 0),
                    'invoice_count': receivables.get('invoice_count', 0),
                    'period': summary.get('period', {})
                }
        except Exception as e:
            print(f"[ERROR] Odoo revenue summary: {e}")

        return {'total_invoiced': 0, 'total_outstanding': 0, 'invoice_count': 0}

    def get_odoo_new_customers(self, days: int = 7) -> List[Dict]:
        """Get new customers created in last N days"""
        try:
            response = requests.post(
                f"{ODOO_MCP_URL}/get_customers",
                json={'limit': 100},
                timeout=30
            )
            result = response.json()

            if result.get('success'):
                customers = result.get('customers', [])
                cutoff_date = datetime.now() - timedelta(days=days)

                new_customers = []
                for customer in customers:
                    create_date = customer.get('create_date', '')
                    if create_date:
                        try:
                            created = datetime.fromisoformat(create_date.replace(' ', 'T'))
                            if created >= cutoff_date:
                                new_customers.append({
                                    'name': customer.get('name', 'Unknown'),
                                    'email': customer.get('email', ''),
                                    'company': customer.get('street', ''),
                                    'created': create_date
                                })
                        except:
                            pass

                return new_customers
        except Exception as e:
            print(f"[ERROR] Odoo new customers: {e}")

        return []

    def get_odoo_recent_invoices(self, limit: int = 10) -> List[Dict]:
        """Get recent invoices"""
        try:
            response = requests.post(
                f"{ODOO_MCP_URL}/get_invoices",
                json={'state': 'posted', 'limit': limit},
                timeout=30
            )
            result = response.json()

            if result.get('success'):
                invoices = result.get('invoices', [])
                return [
                    {
                        'name': inv.get('name', 'N/A'),
                        'customer': inv.get('partner_id', ['Unknown'])[1] if isinstance(inv.get('partner_id'), list) else 'Unknown',
                        'amount': inv.get('amount_total', 0),
                        'paid': inv.get('amount_residual', 0) == 0,
                        'state': inv.get('state', 'draft')
                    }
                    for inv in invoices
                ]
        except Exception as e:
            print(f"[ERROR] Odoo recent invoices: {e}")

        return []

    def parse_bank_transactions(self, days: int = 7) -> Dict:
        """
        Parse Bank_Transactions.md for revenue/expenses

        Returns:
        - Total revenue
        - Total expenses
        - Net cash flow
        - Transaction count
        """
        transactions_file = self.vault_path / "Bank_Transactions.md"

        if not transactions_file.exists():
            return {'revenue': 0, 'expenses': 0, 'net': 0, 'count': 0}

        try:
            with open(transactions_file, 'r', encoding='utf-8') as f:
                content = f.read()

            revenue = 0
            expenses = 0
            transaction_count = 0

            # Find positive amounts (revenue)
            revenue_pattern = r'\*\*[^*]+\*\*\s*\|\s*\$?([\d,]+\.?\d*)\s*\|\s*Revenue'
            for match in re.finditer(revenue_pattern, content):
                amount = float(match.group(1).replace(',', ''))
                revenue += amount
                transaction_count += 1

            # Find negative amounts (expenses)
            expense_pattern = r'\*\*[^*]+\*\*\s*\|\s*-\$?([\d,]+\.?\d*)\s*\|\s*Expense'
            for match in re.finditer(expense_pattern, content):
                amount = float(match.group(1).replace(',', ''))
                expenses += amount
                transaction_count += 1

            return {
                'revenue': revenue,
                'expenses': expenses,
                'net': revenue - expenses,
                'count': transaction_count
            }
        except Exception as e:
            print(f"[ERROR] Parse bank transactions: {e}")

        return {'revenue': 0, 'expenses': 0, 'net': 0, 'count': 0}

    def calculate_goal_progress(self, current_revenue: float) -> Dict:
        """Calculate progress toward monthly revenue goal"""
        progress = (current_revenue / MONTHLY_REVENUE_GOAL) * 100 if MONTHLY_REVENUE_GOAL > 0 else 0

        # Calculate daily rate needed
        today = datetime.now()
        days_in_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - today.replace(day=1)
        days_remaining = days_in_month.days - today.day

        remaining_goal = MONTHLY_REVENUE_GOAL - current_revenue
        daily_rate_needed = remaining_goal / days_remaining if days_remaining > 0 else 0

        return {
            'goal': MONTHLY_REVENUE_GOAL,
            'current': current_revenue,
            'remaining': remaining_goal,
            'progress_percent': round(progress, 1),
            'days_remaining': days_remaining,
            'daily_rate_needed': daily_rate_needed
        }

    def generate_briefing(self) -> Dict:
        """
        Generate complete Monday Morning CEO Briefing

        Returns dict with all briefing data
        """
        print("\n" + "=" * 70)
        print("  MONDAY MORNING CEO BRIEFING")
        print("=" * 70)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Get Odoo data
        print("\n[1/5] Fetching Odoo data...")
        odoo_summary = self.get_odoo_revenue_summary()
        new_customers = self.get_odoo_new_customers(days=7)
        recent_invoices = self.get_odoo_recent_invoices(limit=10)

        print(f"   - Total Invoiced: ${odoo_summary.get('total_invoiced', 0):,.2f}")
        print(f"   - Outstanding: ${odoo_summary.get('total_outstanding', 0):,.2f}")
        print(f"   - New Customers: {len(new_customers)}")

        # Get bank transactions
        print("\n[2/5] Analyzing bank transactions...")
        bank_data = self.parse_bank_transactions(days=7)
        print(f"   - Bank Revenue: ${bank_data.get('revenue', 0):,.2f}")
        print(f"   - Bank Expenses: ${bank_data.get('expenses', 0):,.2f}")
        print(f"   - Net Cash Flow: ${bank_data.get('net', 0):,.2f}")

        # Calculate goal progress
        print("\n[3/5] Calculating goal progress...")
        total_revenue = odoo_summary.get('total_invoiced', 0) + bank_data.get('revenue', 0)
        goal_progress = self.calculate_goal_progress(total_revenue)
        print(f"   - Monthly Goal: ${goal_progress['goal']:,.2f}")
        print(f"   - Progress: {goal_progress['progress_percent']}%")
        print(f"   - Days Remaining: {goal_progress['days_remaining']}")

        # Generate action items
        print("\n[4/5] Generating action items...")
        action_items = self._generate_action_items(odoo_summary, new_customers, goal_progress)
        print(f"   - Action Items: {len(action_items)}")

        # Create briefing document
        print("\n[5/5] Creating briefing document...")
        briefing_content = self._create_briefing_content(
            odoo_summary=odoo_summary,
            bank_data=bank_data,
            new_customers=new_customers,
            recent_invoices=recent_invoices,
            goal_progress=goal_progress,
            action_items=action_items
        )

        # Save briefing
        filename = f"CEO_Briefing_{datetime.now().strftime('%Y-%m-%d')}.md"
        filepath = self.briefings_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(briefing_content)

        print(f"\n[OK] Briefing saved to: {filepath}")

        return {
            'success': True,
            'filepath': str(filepath),
            'odoo_revenue': odoo_summary.get('total_invoiced', 0),
            'bank_revenue': bank_data.get('revenue', 0),
            'total_revenue': odoo_summary.get('total_invoiced', 0) + bank_data.get('revenue', 0),
            'goal_progress': goal_progress,
            'new_customers': len(new_customers),
            'action_items': action_items  # Return the list, not count
        }

    def _generate_action_items(self, odoo_summary: Dict, new_customers: List, goal_progress: Dict) -> List[str]:
        """Generate action items based on data"""
        actions = []

        # Outstanding payments
        outstanding = odoo_summary.get('total_outstanding', 0)
        if outstanding > 0:
            actions.append(f"🔴 Follow up on ${outstanding:,.2f} in outstanding invoices")

        # New customers to welcome
        if len(new_customers) > 0:
            actions.append(f"✅ Welcome {len(new_customers)} new customer(s) this week")

        # Goal progress warning
        if goal_progress['progress_percent'] < 50 and goal_progress['days_remaining'] > 15:
            actions.append(f"⚠️ Revenue at {goal_progress['progress_percent']}% of goal - increase outreach")

        # Daily rate check
        if goal_progress['daily_rate_needed'] > 500:
            actions.append(f"💰 Need ${goal_progress['daily_rate_needed']:,.2f}/day to meet goal")

        return actions if actions else ["✅ No critical action items - continue current momentum"]

    def _create_briefing_content(self, **kwargs) -> str:
        """Create formatted briefing markdown content"""
        odoo_summary = kwargs.get('odoo_summary', {})
        bank_data = kwargs.get('bank_data', {})
        new_customers = kwargs.get('new_customers', [])
        recent_invoices = kwargs.get('recent_invoices', [])
        goal_progress = kwargs.get('goal_progress', {})
        action_items = kwargs.get('action_items', [])

        today = datetime.now().strftime('%A, %B %d, %Y')

        content = f"""# 📊 Monday Morning CEO Briefing

**Generated:** {today}  
**Period:** Last 7 days  
**Next Briefing:** {datetime.now() + timedelta(days=7):%A, %B %d, %Y}

---

## 🎯 Revenue Summary

| Source | Amount |
|--------|--------|
| Odoo Invoices | ${odoo_summary.get('total_invoiced', 0):,.2f} |
| Bank Payments | ${bank_data.get('revenue', 0):,.2f} |
| **Total Revenue** | **${odoo_summary.get('total_invoiced', 0) + bank_data.get('revenue', 0):,.2f}** |

### Monthly Goal Progress

```
Goal: ${goal_progress.get('goal', 0):,.2f}
Current: ${goal_progress.get('current', 0):,.2f}
Remaining: ${goal_progress.get('remaining', 0):,.2f}
Progress: {goal_progress.get('progress_percent', 0)}%
Days Left: {goal_progress.get('days_remaining', 0)}
Daily Rate Needed: ${goal_progress.get('daily_rate_needed', 0):,.2f}/day
```

---

## 💰 Outstanding Payments

**Total Outstanding:** ${odoo_summary.get('total_outstanding', 0):,.2f}

### Recent Invoices
| Invoice | Customer | Amount | Status |
|---------|----------|--------|--------|
"""

        for inv in recent_invoices[:10]:
            status = "✅ Paid" if inv.get('paid') else "⏳ Pending"
            content += f"| {inv.get('name', 'N/A')} | {inv.get('customer', 'Unknown')} | ${inv.get('amount', 0):,.2f} | {status} |\n"

        content += f"""
---

## 👥 New Customers (Last 7 Days)

**Total New:** {len(new_customers)}

"""

        if new_customers:
            for customer in new_customers:
                content += f"- **{customer.get('name', 'Unknown')}**"
                if customer.get('email'):
                    content += f" - {customer.get('email')}"
                if customer.get('company'):
                    content += f" ({customer.get('company', '')})"
                content += "\n"
        else:
            content += "*No new customers this week*\n"

        content += f"""
---

## 💳 Cash Flow (Bank Transactions)

| Category | Amount |
|----------|--------|
| Revenue | ${bank_data.get('revenue', 0):,.2f} |
| Expenses | ${bank_data.get('expenses', 0):,.2f} |
| **Net Cash Flow** | **${bank_data.get('net', 0):,.2f}** |

---

## ✅ Action Items

"""

        for i, action in enumerate(action_items, 1):
            content += f"{i}. {action}\n"

        content += f"""
---

## 📈 Week-over-Week Comparison

*Note: Historical data will be populated after multiple weeks of briefings*

| Week | Revenue | Goal Progress | New Customers |
|------|---------|---------------|---------------|
| This Week | ${odoo_summary.get('total_invoiced', 0) + bank_data.get('revenue', 0):,.2f} | {goal_progress.get('progress_percent', 0)}% | {len(new_customers)} |
| Last Week | TBD | TBD | TBD |

---

## 📝 Notes

- Data sourced from Odoo ERP and Bank Transactions
- Odoo URL: http://localhost:8069
- Briefing generated automatically every Monday at 8:00 AM

---

*Generated by AI Employee System - Gold Tier*
"""

        return content

    def send_briefing_email(self, briefing_result: Dict) -> bool:
        """
        Send briefing via email to CEO

        Returns True if sent successfully
        """
        try:
            # Create email body (abbreviated version)
            goal_progress = briefing_result.get('goal_progress', {})
            action_items = briefing_result.get('action_items', [])
            
            # Format action items
            action_text = ""
            if action_items:
                for item in action_items[:5]:
                    action_text += f"• {item}\n"
            else:
                action_text = "• No critical action items"

            email_body = f"""
Good Morning,

Here's your Monday Morning CEO Briefing for {datetime.now().strftime('%B %d, %Y')}:

📊 REVENUE SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Revenue (7 days): ${briefing_result.get('total_revenue', 0):,.2f}
- Odoo Invoices: ${briefing_result.get('odoo_revenue', 0):,.2f}
- Bank Payments: ${briefing_result.get('bank_revenue', 0):,.2f}

🎯 GOAL PROGRESS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Monthly Goal: ${goal_progress.get('goal', 0):,.2f}
Current: ${goal_progress.get('current', 0):,.2f} ({goal_progress.get('progress_percent', 0)}%)
Remaining: ${goal_progress.get('remaining', 0):,.2f}
Days Left: {goal_progress.get('days_remaining', 0)}
Daily Rate Needed: ${goal_progress.get('daily_rate_needed', 0):,.2f}/day

👥 NEW CUSTOMERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{briefing_result.get('new_customers', 0)} new customer(s) this week

✅ ACTION ITEMS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{action_text}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Full briefing attached. View in: D:\\prompteng\\AI_Employee_Vault\\Briefings\\

Best regards,
AI Employee System
"""

            email_data = {
                "to": CEO_EMAIL,
                "subject": f"📊 Monday CEO Briefing - {datetime.now().strftime('%B %d, %Y')} - {briefing_result.get('total_revenue', 0):,.0f} Revenue",
                "body": email_body.strip()
            }

            print(f"\n[EMAIL] Sending briefing to: {CEO_EMAIL}")

            response = requests.post(
                f"{EMAIL_MCP_URL}/send_email",
                json=email_data,
                timeout=30
            )
            result = response.json()

            if result.get("success"):
                print(f"[OK] Briefing email sent successfully!")
                return True
            else:
                print(f"[WARN] Email send failed: {result.get('error')}")
                return False

        except requests.exceptions.ConnectionError:
            print(f"[WARN] Email MCP server not running - briefing saved locally only")
            return False
        except Exception as e:
            print(f"[ERROR] Error sending briefing email: {e}")
            return False


# Import re for regex
import re


def generate_monday_briefing(send_email: bool = True) -> Dict:
    """
    Generate Monday Morning CEO Briefing

    Args:
        send_email: Whether to email the briefing

    Returns:
        Briefing result dict
    """
    generator = MondayBriefingGenerator()

    # Generate briefing
    result = generator.generate_briefing()

    # Send email if requested
    if send_email and result.get('success'):
        email_sent = generator.send_briefing_email(result)
        result['email_sent'] = email_sent

    return result


if __name__ == "__main__":
    # Generate and send briefing
    result = generate_monday_briefing(send_email=True)

    print("\n" + "=" * 70)
    print("  BRIEFING RESULTS")
    print("=" * 70)
    print(f"Success: {result.get('success', False)}")
    print(f"Total Revenue: ${result.get('total_revenue', 0):,.2f}")
    print(f"Goal Progress: {result.get('goal_progress', {}).get('progress_percent', 0)}%")
    print(f"New Customers: {result.get('new_customers', 0)}")
    print(f"Email Sent: {result.get('email_sent', False)}")
    print("=" * 70)
