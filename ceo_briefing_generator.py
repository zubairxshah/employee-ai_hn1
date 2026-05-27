"""
CEO Briefing Generator - Enhanced for Gold Tier
Generates the Monday Morning CEO Briefing with Odoo integration

Gold Tier Feature
"""

import os
import re
import requests
from datetime import datetime, timedelta
from pathlib import Path
from audit_logic import analyze_transactions, generate_subscription_report, identify_potential_cancellations


class CEOBriefingGenerator:
    """Enhanced CEO Briefing Generator with Odoo integration"""
    
    def __init__(self, vault_path: str, odoo_enabled: bool = True):
        self.vault_path = Path(vault_path)
        self.briefings_dir = self.vault_path / "Briefings"
        self.odoo_enabled = odoo_enabled
        self.odoo_url = os.getenv('ODOO_URL', 'http://localhost:8005')
        
        # Ensure briefings directory exists
        self.briefings_dir.mkdir(parents=True, exist_ok=True)

    def get_odoo_financial_summary(self, date_from: str = None, date_to: str = None) -> dict:
        """Get financial summary from Odoo"""
        if not self.odoo_enabled:
            return None
            
        try:
            url = f"{self.odoo_url}/get_financial_summary"
            data = {}
            if date_from:
                data['date_from'] = date_from
            if date_to:
                data['date_to'] = date_to
                
            response = requests.post(url, json=data, timeout=30)
            result = response.json()
            
            if result.get('success'):
                return result.get('summary')
        except Exception as e:
            print(f"Odoo financial summary error: {e}")
        return None

    def get_odoo_invoices(self, state: str = 'posted', limit: int = 50) -> list:
        """Get invoices from Odoo"""
        if not self.odoo_enabled:
            return []
            
        try:
            url = f"{self.odoo_url}/get_invoices"
            data = {'state': state, 'limit': limit}
            
            response = requests.post(url, json=data, timeout=30)
            result = response.json()
            
            if result.get('success'):
                return result.get('invoices', [])
        except Exception as e:
            print(f"Odoo invoices error: {e}")
        return []

    def get_odoo_payments(self, state: str = 'posted', limit: int = 50) -> list:
        """Get payments from Odoo"""
        if not self.odoo_enabled:
            return []
            
        try:
            url = f"{self.odoo_url}/get_payments"
            data = {'state': state, 'limit': limit}
            
            response = requests.post(url, json=data, timeout=30)
            result = response.json()
            
            if result.get('success'):
                return result.get('payments', [])
        except Exception as e:
            print(f"Odoo payments error: {e}")
        return []

    def load_business_goals(self):
        """Load business goals from Business_Goals.md"""
        goals_file = self.vault_path / "Business_Goals.md"
        if not goals_file.exists():
            return {}

        with open(goals_file, 'r', encoding='utf-8') as f:
            content = f.read()

        goals_data = {
            'revenue_target': self._extract_value(content, r'Monthly goal: \$(\d+,?\d*)'),
            'current_mtd': self._extract_value(content, r'Current MTD: \$(\d+,?\d*)'),
            'metrics': self._parse_metrics_table(content),
            'projects': self._parse_projects(content)
        }

        return goals_data

    def _extract_value(self, text, pattern):
        """Extract a value using regex pattern"""
        match = re.search(pattern, text)
        if match:
            return match.group(1).replace(',', '')
        return None

    def _parse_metrics_table(self, content):
        """Parse the metrics table from Business_Goals.md"""
        metrics = []
        table_match = re.search(r'\| Metric \| Target \| Alert Threshold \|(.*?)(?:\n\n|\Z)', content, re.DOTALL)
        if table_match:
            table_content = table_match.group(1)
            lines = table_content.strip().split('\n')[1:]
            for line in lines:
                parts = [part.strip() for part in line.split('|') if part.strip()]
                if len(parts) >= 3:
                    metrics.append({
                        'metric': parts[0],
                        'target': parts[1],
                        'alert_threshold': parts[2]
                    })
        return metrics

    def _parse_projects(self, content):
        """Parse active projects from Business_Goals.md"""
        projects = []
        projects_match = re.search(r'### Active Projects(.*?)(?:\n\n|\Z)', content, re.DOTALL)
        if projects_match:
            projects_content = projects_match.group(1)
            lines = projects_content.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('- ') or line.startswith('1. ') or line.startswith('2. '):
                    project_match = re.match(r'[0-9\-]*\s*(.*?)\s*-\s*Due\s+(\w+\s+\d+)\s*-\s*Budget\s*\$(\d+)', line)
                    if project_match:
                        projects.append({
                            'name': project_match.group(1),
                            'due_date': project_match.group(2),
                            'budget': project_match.group(3)
                        })
        return projects

    def load_bank_transactions(self):
        """Load bank transactions from Bank_Transactions.md"""
        transactions_file = self.vault_path / "Bank_Transactions.md"
        if not transactions_file.exists():
            return []

        with open(transactions_file, 'r', encoding='utf-8') as f:
            content = f.read()

        transactions = []
        week_sections = re.findall(r'## Week of (.*?)\n((?:(?!## Week of)[\s\S])*?)\n(?=## Week of|$)', content)

        for week_header, week_content in week_sections:
            transaction_matches = re.findall(r'- \*\*(.*?)\*\* \| \*?([\$\-][\d,]+\.?\d*)\*? \| (.*?) \| (.*?)(?=\n- |\n##|$)', week_content)

            for desc, amount, category, details in transaction_matches:
                transactions.append({
                    'description': desc,
                    'amount': amount,
                    'category': category,
                    'details': details,
                    'week': week_header,
                    'date': self._guess_date_from_week(week_header, desc)
                })

        return transactions

    def _guess_date_from_week(self, week_header, description):
        """Guess a date from week header"""
        return "2026-02-15"

    def load_completed_tasks(self):
        """Load completed tasks from Done folder"""
        done_dir = self.vault_path / "Done"
        if not done_dir.exists():
            return []

        completed_tasks = []
        for file_path in done_dir.glob("*.md"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                title_match = re.search(r'^# (.*)', content, re.MULTILINE)
                title = title_match.group(1) if title_match else file_path.stem

                completed_tasks.append({
                    'title': title,
                    'file': file_path.name,
                    'completed_date': datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d')
                })
            except:
                continue

        return completed_tasks

    def calculate_weekly_revenue(self, transactions):
        """Calculate revenue for the week"""
        revenue = 0
        for trans in transactions:
            amount_str = trans['amount']
            if amount_str.startswith('$'):
                amount = float(amount_str[1:].replace(',', ''))
                revenue += amount
        return revenue

    def calculate_weekly_expenses(self, transactions):
        """Calculate expenses for the week"""
        expenses = 0
        for trans in transactions:
            amount_str = trans['amount']
            if amount_str.startswith('-$'):
                amount = float(amount_str[2:].replace(',', ''))
                expenses += amount
        return expenses

    def identify_bottlenecks(self, completed_tasks, odoo_invoices=None):
        """Identify potential bottlenecks"""
        bottlenecks = []
        
        # Check for overdue invoices
        if odoo_invoices:
            today = datetime.now()
            for invoice in odoo_invoices[:20]:  # Check last 20 invoices
                due_date_str = invoice.get('invoice_date_due')
                if due_date_str:
                    try:
                        due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
                        if due_date < today and invoice.get('payment_state') != 'paid':
                            bottlenecks.append({
                                'task': f"Invoice {invoice.get('name', 'N/A')} - {invoice.get('partner_id', ['Unknown'])[1] if isinstance(invoice.get('partner_id'), list) else 'Unknown'}",
                                'expected': due_date_str,
                                'actual': 'Outstanding',
                                'delay': f"{(today - due_date).days} days overdue",
                                'amount': invoice.get('amount_residual', 0)
                            })
                    except:
                        pass
        
        # Sort by amount (highest first)
        bottlenecks.sort(key=lambda x: x.get('amount', 0), reverse=True)
        
        return bottlenecks[:5]  # Return top 5 bottlenecks

    def generate_revenue_summary(self, odoo_summary=None, transactions=None):
        """Generate revenue summary with Odoo data"""
        summary = {
            'this_week': 0,
            'mtd': 0,
            'outstanding': 0,
            'overdue': 0
        }
        
        if odoo_summary:
            summary['this_week'] = odoo_summary.get('receivables', {}).get('total_invoiced', 0)
            summary['outstanding'] = odoo_summary.get('receivables', {}).get('total_outstanding', 0)
            summary['invoice_count'] = odoo_summary.get('receivables', {}).get('invoice_count', 0)
        elif transactions:
            summary['this_week'] = self.calculate_weekly_revenue(transactions)
            
        return summary

    def generate_briefing(self):
        """Generate the complete CEO briefing with Odoo integration"""
        # Load all data
        goals = self.load_business_goals()
        transactions = self.load_bank_transactions()
        completed_tasks = self.load_completed_tasks()
        
        # Get Odoo data
        odoo_summary = self.get_odoo_financial_summary()
        odoo_invoices = self.get_odoo_invoices(state='posted', limit=20)
        odoo_payments = self.get_odoo_payments(state='posted', limit=20)
        
        # Calculate key metrics
        weekly_revenue = self.calculate_weekly_revenue(transactions)
        weekly_expenses = self.calculate_weekly_expenses(transactions)
        
        # Get revenue summary
        revenue_summary = self.generate_revenue_summary(odoo_summary, transactions)
        
        # Analyze subscriptions
        subscriptions = analyze_transactions(transactions)
        subscription_report = generate_subscription_report(subscriptions)
        potential_cancellations = identify_potential_cancellations(subscriptions)
        
        # Identify bottlenecks
        bottlenecks = self.identify_bottlenecks(completed_tasks, odoo_invoices)
        
        # Format the briefing
        briefing_date = datetime.now().strftime('%Y-%m-%d')
        prev_monday = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime('%Y-%m-%d')
        next_sunday = (datetime.now() + timedelta(days=6-datetime.now().weekday())).strftime('%Y-%m-%d')
        
        # Determine data source
        data_source = "Odoo ERP" if odoo_summary else "Bank Transactions"
        
        briefing_content = f"""# /Vault/Briefings/{briefing_date}_Monday_Briefing.md
---
generated: {datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')}
period: {prev_monday} to {next_sunday}
data_source: {data_source}
---


# Monday Morning CEO Briefing


## Executive Summary
"""
        # Executive summary
        if odoo_summary:
            net_position = odoo_summary.get('net_position', 0)
            briefing_content += f"Strong week with ${revenue_summary['this_week']:,.2f} invoiced. "
            briefing_content += f"Outstanding receivables: ${revenue_summary['outstanding']:,.2f}. "
            if bottlenecks:
                briefing_content += f"⚠️ {len(bottlenecks)} overdue invoice(s) require attention."
            else:
                briefing_content += "Operations running smoothly."
        else:
            briefing_content += f"Weekly revenue: ${weekly_revenue:,.2f}. "
            briefing_content += f"Expenses: ${weekly_expenses:,.2f}. "
            briefing_content += "Operations running smoothly." if not bottlenecks else f"⚠️ {len(bottlenecks)} issue(s) identified."

        # Revenue section
        briefing_content += f"""


## Revenue

"""
        if odoo_summary:
            target = float(goals.get('revenue_target', 0) or 0)
            mtd = revenue_summary.get('this_week', 0)  # Using week as proxy for MTD
            pace = "On track" if mtd >= (target / 4) else "Behind pace"
            
            briefing_content += f"""| Metric | Amount | Status |
|--------|--------|--------|
| This Week | ${revenue_summary['this_week']:,.2f} | {'✅' if revenue_summary['this_week'] > 0 else '⚠️'} |
| MTD (Est.) | ${mtd:,.2f} | {pace} |
| Outstanding | ${revenue_summary['outstanding']:,.2f} | {revenue_summary.get('invoice_count', 0)} invoices |
| Monthly Target | ${target:,.2f} | {mtd/target*100:.1f}% if MTD accurate |

"""
        else:
            briefing_content += f"""- **This Week**: ${weekly_revenue:,.2f}
- **MTD**: {goals.get('current_mtd', '$0')} (of ${goals.get('revenue_target', '0')} target)
- **Trend**: {'On track' if float(goals.get('current_mtd', '0') or 0) >= (float(goals.get('revenue_target', '0') or 0) / 4) else 'Behind pace'}

"""

        # Completed tasks
        briefing_content += """
## Completed Tasks
"""
        for i, task in enumerate(completed_tasks[-5:]):
            briefing_content += f"- [x] {task['title']} (completed {task['completed_date']})\n"

        if not completed_tasks:
            briefing_content += "- [x] No tasks marked as completed this week\n"

        # Bottlenecks section
        briefing_content += """

## Bottlenecks
"""
        if bottlenecks:
            briefing_content += "| Invoice/Customer | Due Date | Status | Delay | Amount |\n"
            briefing_content += "|-------------------|----------|--------|-------|--------|\n"
            for bottleneck in bottlenecks:
                amount = bottleneck.get('amount', 0)
                briefing_content += f"| {bottleneck['task']} | {bottleneck['expected']} | {bottleneck['actual']} | {bottleneck['delay']} | ${amount:,.2f} |\n"
            briefing_content += f"\n**Action Required**: Contact customers with overdue invoices. Total outstanding: ${sum(b.get('amount', 0) for b in bottlenecks):,.2f}\n"
        else:
            briefing_content += "✅ No significant bottlenecks identified.\n"

        # Proactive suggestions
        briefing_content += """

## Proactive Suggestions


### Cost Optimization
"""
        if potential_cancellations:
            for cancel in potential_cancellations:
                briefing_content += f"- **{cancel['service']}**: {cancel['reason']}. Cost: {cancel['amount']}.\n"
                briefing_content += f"  - [ACTION] {cancel['action']}? Move to /Pending_Approval\n\n"
        else:
            briefing_content += "✅ No cost optimization opportunities identified.\n\n"

        # Upcoming deadlines
        briefing_content += """### Upcoming Deadlines
"""
        for project in goals.get('projects', [])[:3]:
            briefing_content += f"- {project['name']}: Due {project['due_date']} (Budget: ${project['budget']})\n"

        if not goals.get('projects'):
            briefing_content += "- No active projects listed in Business_Goals.md\n"

        # Subscription report
        briefing_content += f"""

### Subscription Report
- Total subscriptions tracked: {len(subscription_report['unique_services'])}
- Estimated monthly cost: ${subscription_report['monthly_cost']:.2f}
- Services: {', '.join(list(subscription_report['unique_services'])[:5])}{'...' if len(subscription_report['unique_services']) > 5 else ''}

"""

        # Odoo-specific section (if enabled)
        if odoo_summary:
            briefing_content += f"""
## Odoo Financial Summary

### Receivables (Customer Invoices)
- Total Invoiced (Period): ${odoo_summary['receivables']['total_invoiced']:,.2f}
- Total Outstanding: ${odoo_summary['receivables']['total_outstanding']:,.2f}
- Invoice Count: {odoo_summary['receivables']['invoice_count']}

### Payables (Vendor Bills)
- Total Billed (Period): ${odoo_summary['payables']['total_billed']:,.2f}
- Total Outstanding: ${odoo_summary['payables']['total_outstanding']:,.2f}
- Bill Count: {odoo_summary['payables']['bill_count']}

### Net Position
- **Net Cash Flow**: ${odoo_summary['net_position']:,.2f} (Receivables - Payables)

"""

        # Recent payments
        if odoo_payments:
            briefing_content += """### Recent Payments Received
"""
            for payment in odoo_payments[:5]:
                partner = payment.get('partner_id', ['Unknown'])[1] if isinstance(payment.get('partner_id'), list) else 'Unknown'
                briefing_content += f"- {payment.get('name', 'N/A')}: ${payment.get('amount', 0):,.2f} from {partner} on {payment.get('payment_date', 'N/A')}\n"
            briefing_content += "\n"

        briefing_content += """---
*Generated by AI Employee v1.0 (Gold Tier)*
"""

        # Write the briefing to a file
        briefing_filename = f"{briefing_date}_Monday_Briefing.md"
        briefing_path = self.briefings_dir / briefing_filename

        with open(briefing_path, 'w', encoding='utf-8') as f:
            f.write(briefing_content)

        print(f"CEO Briefing generated: {briefing_path}")
        return briefing_path


def main():
    """Generate the CEO briefing"""
    vault_path = r"D:\prompteng\AI_Employee_Vault"
    
    # Check if Odoo is available
    odoo_enabled = True
    try:
        response = requests.get('http://localhost:8005/health', timeout=5)
        if response.status_code != 200:
            odoo_enabled = False
            print("Odoo MCP server not available, using bank transactions only")
    except:
        odoo_enabled = False
        print("Odoo MCP server not available, using bank transactions only")
    
    generator = CEOBriefingGenerator(vault_path, odoo_enabled=odoo_enabled)
    generator.generate_briefing()


if __name__ == "__main__":
    main()
