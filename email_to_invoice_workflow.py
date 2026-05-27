"""
Email to Invoice Workflow
Parses incoming emails for invoice/deal confirmations and creates Odoo invoices

Workflow:
1. Gmail watcher detects new important emails
2. Email parser extracts invoice/deal details
3. Creates customer in Odoo (if new)
4. Creates invoice in Odoo
5. Sends for approval (if over threshold)
6. Executes approved invoices
"""

import os
import re
import json
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Configuration
VAULT_PATH = r"D:\prompteng\AI_Employee_Vault"
INCOMING_EMAILS_DIR = os.path.join(VAULT_PATH, "Incoming_Emails")
PENDING_APPROVAL_DIR = os.path.join(VAULT_PATH, "Pending_Approval")
PROCESSED_EMAILS_DIR = os.path.join(VAULT_PATH, "Processed_Emails")

ODOO_MCP_URL = "http://localhost:8005"
APPROVAL_MCP_URL = "http://localhost:8003"
EMAIL_MCP_URL = "http://localhost:8001"

# Invoice approval threshold
INVOICE_APPROVAL_THRESHOLD = 1000.00  # Require approval for invoices over $1000

# Email configuration - who receives invoice notifications
INVOICE_EMAIL_FROM = "emaxis.newsletter@gmail.com"  # Your Gmail address from .env
INVOICE_EMAIL_SUBJECT_TEMPLATE = "Invoice #{invoice_id} from AI Employee"


class EmailToInvoiceWorkflow:
    """
    Workflow for converting emails to Odoo invoices
    """

    def __init__(self):
        self.odoo_mcp_url = ODOO_MCP_URL
        self.approval_mcp_url = APPROVAL_MCP_URL
        self.invoice_threshold = INVOICE_APPROVAL_THRESHOLD

        # Create directories
        Path(INCOMING_EMAILS_DIR).mkdir(parents=True, exist_ok=True)
        Path(PENDING_APPROVAL_DIR).mkdir(parents=True, exist_ok=True)
        Path(PROCESSED_EMAILS_DIR).mkdir(parents=True, exist_ok=True)

    def parse_invoice_email(self, email_content: str, email_headers: Dict) -> Optional[Dict]:
        """
        Parse email content to extract invoice/deal details

        Returns dict with:
        - customer_name, customer_email, customer_phone
        - invoice_lines (list of {name, quantity, price_unit})
        - amount, currency
        - description, reference
        """
        data = {
            'customer_name': None,
            'customer_email': None,
            'customer_phone': None,
            'invoice_lines': [],
            'amount': None,
            'currency': 'USD',
            'description': '',
            'reference': email_headers.get('subject', ''),
            'email_from': email_headers.get('from', ''),
            'email_subject': email_headers.get('subject', ''),
            'email_date': email_headers.get('date', datetime.now().isoformat())
        }

        # Extract customer email from From header
        from_email = email_headers.get('from', '')
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_email)
        if email_match:
            data['customer_email'] = email_match.group()

        # Try to extract customer name from email
        name_match = re.search(r'^([^<]+)', from_email)
        if name_match:
            data['customer_name'] = name_match.group(1).strip()

        # Look for amounts in email content
        amount_patterns = [
            r'(?:amount|total|invoice amount|sum)[:\s]*\$?([\d,]+\.?\d*)',
            r'\$([\d,]+\.?\d*)',
            r'USD\s*([\d,]+\.?\d*)',
            r'EUR\s*([\d,]+\.?\d*)',
            r'(\d+\.?\d*)\s*(?:USD|EUR|GBP)',
        ]

        for pattern in amount_patterns:
            amount_match = re.search(pattern, email_content, re.IGNORECASE)
            if amount_match:
                amount_str = amount_match.group(1).replace(',', '')
                try:
                    data['amount'] = float(amount_str)
                    break
                except ValueError:
                    pass

        # Detect currency
        if 'EUR' in email_content.upper():
            data['currency'] = 'EUR'
        elif 'GBP' in email_content.upper():
            data['currency'] = 'GBP'

        # Extract description/invoice details
        description_patterns = [
            r'(?:description|details|for)[:\s]*(.+?)(?:\n\n|$)',
            r'(?:regarding|re|about)[:\s]*(.+?)(?:\n\n|$)',
        ]

        for pattern in description_patterns:
            desc_match = re.search(pattern, email_content, re.IGNORECASE | re.DOTALL)
            if desc_match:
                data['description'] = desc_match.group(1).strip()
                break

        # If no description found, use email snippet
        if not data['description']:
            data['description'] = email_content[:500] if len(email_content) > 500 else email_content

        # Create invoice line from extracted data
        if data['amount']:
            data['invoice_lines'].append({
                'name': data['description'] or 'Service',
                'quantity': 1,
                'price_unit': data['amount']
            })

        return data

    def get_or_create_customer(self, email_data: Dict) -> Optional[int]:
        """
        Get existing customer or create new one in Odoo

        Returns customer_id or None
        """
        try:
            # First, try to find existing customer by email
            if email_data.get('customer_email'):
                response = requests.post(
                    f"{self.odoo_mcp_url}/get_customers",
                    json={'search': email_data['customer_email'], 'limit': 10},
                    timeout=30
                )
                result = response.json()

                if result.get('success') and result.get('customers'):
                    # Check if any customer matches the email
                    for customer in result.get('customers', []):
                        if customer.get('email', '').lower() == email_data['customer_email'].lower():
                            print(f"[INFO] Found existing customer: {customer.get('name')}")
                            return customer.get('id')

            # Create new customer if not found
            customer_data = {
                'name': email_data.get('customer_name') or email_data.get('customer_email') or 'Unknown Customer',
                'email': email_data.get('customer_email'),
            }

            # Add phone if available
            if email_data.get('customer_phone'):
                customer_data['phone'] = email_data['customer_phone']

            print(f"[INFO] Creating new customer: {customer_data['name']}")

            response = requests.post(
                f"{self.odoo_mcp_url}/create_customer",
                json=customer_data,
                timeout=30
            )
            result = response.json()

            if result.get('success'):
                print(f"[OK] Customer created with ID: {result.get('customer_id')}")
                return result.get('customer_id')
            else:
                print(f"[ERROR] Failed to create customer: {result.get('error')}")
                return None

        except Exception as e:
            print(f"[ERROR] Error in get_or_create_customer: {e}")
            return None

    def create_invoice(self, customer_id: int, email_data: Dict) -> Optional[int]:
        """
        Create invoice in Odoo

        Returns invoice_id or None
        """
        try:
            invoice_data = {
                'partner_id': customer_id,
                'lines': email_data.get('invoice_lines', []),
                'narration': email_data.get('description', '')
            }

            # Add invoice date if available
            if email_data.get('invoice_date'):
                invoice_data['invoice_date'] = email_data['invoice_date']

            print(f"[INFO] Creating invoice for customer {customer_id}")
            print(f"[INFO] Invoice lines: {len(invoice_data['lines'])}")

            response = requests.post(
                f"{self.odoo_mcp_url}/create_invoice",
                json=invoice_data,
                timeout=30
            )
            result = response.json()

            if result.get('success'):
                invoice_id = result.get('invoice_id')
                print(f"[OK] Invoice created with ID: {invoice_id}")
                return invoice_id
            else:
                print(f"[ERROR] Failed to create invoice: {result.get('error')}")
                return None

        except Exception as e:
            print(f"[ERROR] Error in create_invoice: {e}")
            return None

    def request_invoice_approval(self, invoice_id: int, email_data: Dict, amount: float) -> str:
        """
        Create approval request for invoice

        Returns approval request ID
        """
        try:
            approval_data = {
                'action': 'confirm_invoice',
                'amount': amount,
                'recipient': email_data.get('customer_email', 'N/A'),
                'reason': f"Invoice #{invoice_id} for {email_data.get('customer_name', 'Unknown')}",
                'invoice_id': invoice_id,
                'email_subject': email_data.get('email_subject', ''),
                'email_from': email_data.get('email_from', ''),
            }

            response = requests.post(
                f"{self.approval_mcp_url}/request_approval",
                json=approval_data,
                timeout=30
            )
            result = response.json()

            if result.get('success'):
                request_id = result.get('request_id')
                print(f"[OK] Approval request created: {request_id}")
                return request_id
            else:
                print(f"[ERROR] Failed to create approval request: {result.get('error')}")
                return None

        except Exception as e:
            print(f"[ERROR] Error in request_invoice_approval: {e}")
            return None

    def send_invoice_email(self, invoice_id: int, customer_email: str, customer_name: str, amount: float, description: str) -> bool:
        """
        Send invoice email to customer after confirmation

        Returns True if email sent successfully
        """
        try:
            # Create email body
            email_body = f"""Dear {customer_name or 'Valued Customer'},

Thank you for your business!

Please find below your invoice details:

Invoice Number: {invoice_id}
Amount: ${amount:,.2f}
Description: {description or 'Services rendered'}

Payment is due upon receipt. If you have any questions regarding this invoice, please don't hesitate to contact us.

Thank you for your business!

Best regards,
AI Employee System
"""

            # Send via Email MCP
            email_data = {
                "to": customer_email,
                "subject": f"Invoice #{invoice_id} from AI Employee",
                "body": email_body
            }

            print(f"[EMAIL] Sending invoice email to: {customer_email}")
            print(f"[EMAIL] Subject: Invoice #{invoice_id} from AI Employee")

            response = requests.post(
                f"{EMAIL_MCP_URL}/send_email",
                json=email_data,
                timeout=30
            )
            result = response.json()

            if result.get("success"):
                print(f"[OK] Invoice email sent successfully to {customer_email}")
                return True
            else:
                print(f"[WARN] Email send failed: {result.get('error')}")
                return False

        except requests.exceptions.ConnectionError:
            print(f"[WARN] Email MCP server not running - skipping invoice email")
            return False
        except Exception as e:
            print(f"[ERROR] Error sending invoice email: {e}")
            return False

    def process_email(self, email_content: str, email_headers: Dict) -> Dict:
        """
        Process a single email and create invoice if applicable

        Returns dict with processing results
        """
        result = {
            'success': False,
            'customer_id': None,
            'invoice_id': None,
            'approval_request_id': None,
            'requires_approval': False,
            'error': None
        }

        print("\n" + "=" * 60)
        print("[EMAIL TO INVOICE] Processing email")
        print("=" * 60)
        print(f"From: {email_headers.get('from', 'N/A')}")
        print(f"Subject: {email_headers.get('subject', 'N/A')}")

        # Step 1: Parse email content
        print("\n[STEP 1] Parsing email content...")
        parsed_data = self.parse_invoice_email(email_content, email_headers)

        if not parsed_data:
            result['error'] = "Failed to parse email content"
            return result

        print(f"[OK] Parsed data:")
        print(f"   Customer: {parsed_data.get('customer_name', 'N/A')}")
        print(f"   Email: {parsed_data.get('customer_email', 'N/A')}")
        print(f"   Amount: ${parsed_data.get('amount', 'N/A')}")

        # Step 2: Get or create customer
        print("\n[STEP 2] Getting/creating customer...")
        customer_id = self.get_or_create_customer(parsed_data)

        if not customer_id:
            result['error'] = "Failed to get/create customer"
            return result

        result['customer_id'] = customer_id

        # Step 3: Create invoice
        print("\n[STEP 3] Creating invoice...")
        invoice_id = self.create_invoice(customer_id, parsed_data)

        if not invoice_id:
            result['error'] = "Failed to create invoice"
            return result

        result['invoice_id'] = invoice_id

        # Step 4: Check if approval required
        amount = parsed_data.get('amount', 0)
        requires_approval = amount >= self.invoice_threshold

        if requires_approval:
            print(f"\n[STEP 4] Amount ${amount} >= ${self.invoice_threshold}, requesting approval...")
            approval_id = self.request_invoice_approval(invoice_id, parsed_data, amount)
            result['approval_request_id'] = approval_id
            result['requires_approval'] = True
            print(f"[INFO] Invoice will be emailed to customer AFTER approval")
        else:
            print(f"\n[STEP 4] Amount ${amount} < ${self.invoice_threshold}, auto-confirming...")
            # Auto-confirm invoice (below threshold)
            try:
                response = requests.post(
                    f"{self.odoo_mcp_url}/confirm_invoice",
                    json={'invoice_id': invoice_id},
                    timeout=30
                )
                if response.json().get('success'):
                    print(f"[OK] Invoice auto-confirmed")
                    
                    # Send invoice email to customer
                    self.send_invoice_email(
                        invoice_id=invoice_id,
                        customer_email=parsed_data.get('customer_email', ''),
                        customer_name=parsed_data.get('customer_name', ''),
                        amount=amount,
                        description=parsed_data.get('description', '')
                    )
            except Exception as e:
                print(f"[WARN] Auto-confirm failed: {e}")

        result['success'] = True
        print("\n" + "=" * 60)
        print("[EMAIL TO INVOICE] Processing complete")
        print("=" * 60)

        return result

    def save_email_for_processing(self, message_id: str, email_content: str, email_headers: Dict):
        """Save email to incoming directory for processing"""
        filename = f"EMAIL_{message_id}.json"
        filepath = os.path.join(INCOMING_EMAILS_DIR, filename)

        data = {
            'message_id': message_id,
            'content': email_content,
            'headers': email_headers,
            'received': datetime.now().isoformat()
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        return filepath

    def mark_email_processed(self, message_id: str):
        """Move email to processed directory"""
        src_file = os.path.join(INCOMING_EMAILS_DIR, f"EMAIL_{message_id}.json")
        dst_file = os.path.join(PROCESSED_EMAILS_DIR, f"EMAIL_{message_id}.json")

        if os.path.exists(src_file):
            if os.path.exists(dst_file):
                # Already processed, remove source
                try:
                    os.remove(src_file)
                except:
                    pass
            else:
                os.rename(src_file, dst_file)


# Global workflow instance
_workflow = None


def get_workflow() -> EmailToInvoiceWorkflow:
    """Get or create workflow instance"""
    global _workflow
    if _workflow is None:
        _workflow = EmailToInvoiceWorkflow()
    return _workflow


def process_email_message(message_id: str, email_content: str, email_headers: Dict) -> Dict:
    """
    Process an email message and create invoice

    Args:
        message_id: Gmail message ID
        email_content: Email body content
        email_headers: Dict with from, to, subject, date

    Returns:
        Processing result dict
    """
    workflow = get_workflow()

    # Save email for tracking
    workflow.save_email_for_processing(message_id, email_content, email_headers)

    # Process the email
    result = workflow.process_email(email_content, email_headers)

    # Mark as processed
    if result.get('success'):
        workflow.mark_email_processed(message_id)

    return result


if __name__ == "__main__":
    # Test with sample email
    test_email_content = """
    Dear Team,

    Please find the invoice details below:

    Amount: $2,500.00
    Description: Consulting services for February 2026

    Thank you for your business!

    Best regards,
    John Doe
    Acme Corporation
    john@acme.com
    """

    test_headers = {
        'from': 'John Doe <john@acme.com>',
        'subject': 'Invoice - February 2026',
        'date': datetime.now().isoformat()
    }

    result = process_email_message('test_123', test_email_content, test_headers)
    print(f"\nResult: {json.dumps(result, indent=2)}")
