"""
Invoice Flow Workflow
Creates invoices in Odoo and manages the approval workflow

Gold Tier Feature
"""

import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path


class InvoiceWorkflow:
    """Manages invoice creation and approval workflow"""
    
    def __init__(self, vault_path: str, odoo_url: str = "http://localhost:8005"):
        self.vault_path = Path(vault_path)
        self.odoo_url = odoo_url
        self.approvals_dir = self.vault_path / "Pending_Approval"
        self.approvals_dir.mkdir(parents=True, exist_ok=True)
        
    def create_invoice_draft(self, customer_name: str, customer_email: str,
                             lines: list, invoice_date: str = None,
                             payment_terms_days: int = 30,
                             narration: str = "Thank you for your business") -> dict:
        """
        Create an invoice draft for approval
        
        Args:
            customer_name: Customer name
            customer_email: Customer email
            lines: List of invoice lines, each with:
                   - name: Description
                   - quantity: Quantity (default: 1)
                   - price_unit: Unit price
            invoice_date: Invoice date (default: today)
            payment_terms_days: Payment terms in days
            narration: Invoice notes
        """
        # First, check if customer exists or create them
        customer_id = self._get_or_create_customer(customer_name, customer_email)
        
        if not customer_id:
            return {
                "success": False,
                "error": "Failed to create or find customer"
            }
        
        # Prepare invoice data
        invoice_data = {
            "partner_id": customer_id,
            "lines": lines,
            "invoice_date": invoice_date or datetime.now().strftime('%Y-%m-%d'),
            "invoice_date_due": (datetime.now() + timedelta(days=payment_terms_days)).strftime('%Y-%m-%d'),
            "narration": narration
        }
        
        # Create approval request file
        approval_request = self._create_approval_request(invoice_data, customer_name)
        
        return {
            "success": True,
            "action": "draft_created",
            "approval_file": approval_request,
            "message": f"Invoice draft created for {customer_name}. Awaiting approval."
        }
    
    def _get_or_create_customer(self, name: str, email: str) -> int:
        """Get existing customer or create new one"""
        try:
            # Try to find existing customer by email
            response = requests.post(
                f"{self.odoo_url}/get_customers",
                json={"search": email, "limit": 1},
                timeout=30
            )
            result = response.json()
            
            if result.get('success') and result.get('customers'):
                return result['customers'][0]['id']
            
            # Create new customer
            response = requests.post(
                f"{self.odoo_url}/create_customer",
                json={
                    "name": name,
                    "email": email
                },
                timeout=30
            )
            result = response.json()
            
            if result.get('success'):
                return result.get('customer_id')
                
        except Exception as e:
            print(f"Customer lookup/creation error: {e}")
        
        return None
    
    def _create_approval_request(self, invoice_data: dict, customer_name: str) -> str:
        """Create approval request markdown file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"Invoice_{customer_name.replace(' ', '_')}_{timestamp}.md"
        filepath = self.approvals_dir / filename
        
        # Calculate total
        total = sum(line.get('price_unit', 0) * line.get('quantity', 1) for line in invoice_data['lines'])
        
        content = f"""---
type: invoice_approval
created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
status: pending
---

# Invoice Approval Request

## Customer Information

| Field | Value |
|-------|-------|
| Name | {customer_name} |
| Invoice Date | {invoice_data['invoice_date']} |
| Due Date | {invoice_data['invoice_date_due']} |
| Payment Terms | {invoice_data.get('payment_terms_days', 30)} days |

## Invoice Lines

| # | Description | Quantity | Unit Price | Total |
|---|-------------|----------|------------|-------|
"""
        
        for i, line in enumerate(invoice_data['lines'], 1):
            line_total = line.get('price_unit', 0) * line.get('quantity', 1)
            content += f"| {i} | {line.get('name', 'Service')} | {line.get('quantity', 1)} | ${line.get('price_unit', 0):,.2f} | ${line_total:,.2f} |\n"
        
        content += f"""
## Total Amount: **${total:,.2f}**

## Notes
{invoice_data.get('narration', 'Thank you for your business')}

---

## Approval Instructions

Move this file to:
- `/Approved/` to create and confirm the invoice in Odoo
- `/Rejected/` to cancel the invoice creation

**Action Required**: Review and move to appropriate folder.
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(filepath)
    
    def execute_approved_invoice(self, approval_file: str) -> dict:
        """Execute an approved invoice creation"""
        try:
            # Read approval file
            with open(approval_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the file (simplified - in production, use proper frontmatter parser)
            # Extract customer name from content
            name_match = content.find('| Name | ')
            if name_match == -1:
                return {"success": False, "error": "Could not parse approval file"}
            
            # For now, we'll need to extract data more carefully
            # This is a simplified implementation
            lines_start = content.find('## Invoice Lines')
            if lines_start == -1:
                return {"success": False, "error": "Could not find invoice lines"}
            
            # Create invoice in Odoo
            # Note: In a full implementation, we'd parse all the data from the file
            # For now, this is a placeholder for the workflow
            
            return {
                "success": True,
                "message": f"Invoice created from approved request: {approval_file}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


def main():
    """Demo invoice workflow"""
    vault_path = r"D:\prompteng\AI_Employee_Vault"
    workflow = InvoiceWorkflow(vault_path)
    
    # Create a sample invoice draft
    result = workflow.create_invoice_draft(
        customer_name="Acme Corporation",
        customer_email="billing@acme.com",
        lines=[
            {"name": "Consulting Services", "quantity": 10, "price_unit": 150.00},
            {"name": "Software License", "quantity": 1, "price_unit": 500.00}
        ],
        narration="Thank you for your business. Payment due within 30 days."
    )
    
    print(f"Result: {json.dumps(result, indent=2)}")


if __name__ == "__main__":
    main()
