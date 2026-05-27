"""
Odoo MCP Action Skill
Provides accounting operations via the Odoo MCP server

Gold Tier Feature
"""

import os
import requests
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from .. import AgentSkill


class OdooMCPActionSkill(AgentSkill):
    """
    Skill for accounting operations via Odoo MCP server.

    Capabilities:
    - Create and manage invoices
    - Register payments
    - Manage customers
    - Manage products/services
    - Financial reporting
    - Bank statement retrieval
    """

    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}
        config.setdefault('mcp_url', 'http://localhost:8005')
        config.setdefault('timeout', 60)
        super().__init__(config)

        self.mcp_url = self.config.get('mcp_url', 'http://localhost:8005')
        self.timeout = self.config.get('timeout', 60)

    def validate_inputs(self, parameters: Dict[str, Any]) -> tuple:
        """Validate input parameters"""
        action = parameters.get('action')
        if not action:
            return False, "Missing required parameter: action"

        # Invoice actions
        if action in ['create_invoice', 'update_invoice', 'confirm_invoice', 
                      'cancel_invoice', 'reset_invoice_draft', 'get_invoice']:
            if 'invoice_id' not in parameters and action != 'create_invoice':
                return False, f"{action} requires: invoice_id"
        
        if action == 'create_invoice':
            if 'partner_id' not in parameters:
                return False, "create_invoice requires: partner_id"
            if 'lines' not in parameters:
                return False, "create_invoice requires: lines array"
        
        # Payment actions
        if action == 'register_payment':
            required = ['invoice_id', 'amount']
            for param in required:
                if param not in parameters:
                    return False, f"register_payment requires: {', '.join(required)}"
        
        # Customer actions
        if action == 'create_customer':
            if 'name' not in parameters:
                return False, "create_customer requires: name"
        
        # Product actions
        if action == 'create_product':
            required = ['name', 'type', 'list_price']
            for param in required:
                if param not in parameters:
                    return False, f"create_product requires: {', '.join(required)}"

        return True, ""

    def get_capability_description(self) -> str:
        """Return skill description"""
        return (
            f"Odoo MCP Action Skill (v{self.version}): "
            f"Accounting operations via Odoo MCP server at {self.mcp_url}. "
            f"Actions: invoice management, payments, customers, products, reporting"
        )

    def _call_mcp(self, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make a request to the MCP server"""
        url = f"{self.mcp_url}/{endpoint}"
        try:
            response = requests.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"MCP request failed: {str(e)}",
                "endpoint": endpoint
            }

    # ==================== INVOICE OPERATIONS ====================

    def _create_invoice(self, partner_id: int, lines: List[Dict], 
                        invoice_date: Optional[str] = None,
                        invoice_date_due: Optional[str] = None,
                        narration: Optional[str] = None) -> Dict:
        """Create a customer invoice"""
        data = {
            "partner_id": partner_id,
            "lines": lines,
            "invoice_date": invoice_date or datetime.now().strftime('%Y-%m-%d'),
            "invoice_date_due": invoice_date_due,
            "narration": narration or "Thank you for your business"
        }

        result = self._call_mcp('create_invoice', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "create_invoice",
                "invoice_id": result.get("invoice_id"),
                "message": f"Invoice {result.get('invoice_id')} created successfully"
            }
        return result

    def _update_invoice(self, invoice_id: int, values: Dict) -> Dict:
        """Update an invoice"""
        data = {
            "invoice_id": invoice_id,
            "values": values
        }

        result = self._call_mcp('update_invoice', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "update_invoice",
                "invoice_id": invoice_id,
                "message": f"Invoice {invoice_id} updated successfully"
            }
        return result

    def _confirm_invoice(self, invoice_id: int) -> Dict:
        """Confirm/post an invoice (or create draft on cloud)"""
        from agent_config import is_cloud
        if is_cloud():
            return self._create_accounting_draft("confirm_invoice", {
                "invoice_id": str(invoice_id),
            })

        data = {"invoice_id": invoice_id}
        result = self._call_mcp('confirm_invoice', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "confirm_invoice",
                "invoice_id": invoice_id,
                "message": f"Invoice {invoice_id} confirmed successfully"
            }
        return result

    def _cancel_invoice(self, invoice_id: int) -> Dict:
        """Cancel an invoice"""
        data = {"invoice_id": invoice_id}
        result = self._call_mcp('cancel_invoice', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "cancel_invoice",
                "invoice_id": invoice_id,
                "message": f"Invoice {invoice_id} cancelled successfully"
            }
        return result

    def _reset_invoice_draft(self, invoice_id: int) -> Dict:
        """Reset an invoice to draft"""
        data = {"invoice_id": invoice_id}
        result = self._call_mcp('reset_invoice_draft', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "reset_invoice_draft",
                "invoice_id": invoice_id,
                "message": f"Invoice {invoice_id} reset to draft"
            }
        return result

    def _get_invoice(self, invoice_id: int) -> Dict:
        """Get a single invoice by ID"""
        data = {"invoice_id": invoice_id}
        result = self._call_mcp('get_invoice', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "get_invoice",
                "invoice": result.get("invoice")
            }
        return result

    def _get_invoices(self, partner_id: Optional[int] = None,
                      move_type: Optional[str] = None,
                      state: Optional[str] = None,
                      limit: int = 50) -> Dict:
        """Get invoices with optional filters"""
        data = {
            "partner_id": partner_id,
            "move_type": move_type,
            "state": state,
            "limit": limit
        }

        result = self._call_mcp('get_invoices', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "get_invoices",
                "invoices": result.get("invoices"),
                "count": result.get("count")
            }
        return result

    # ==================== PAYMENT OPERATIONS ====================

    def _register_payment(self, invoice_id: int, amount: float,
                          payment_date: Optional[str] = None,
                          payment_method: str = "manual",
                          journal_id: Optional[int] = None) -> Dict:
        """Register a payment for an invoice (or create draft on cloud)"""
        from agent_config import is_cloud
        if is_cloud():
            return self._create_accounting_draft("register_payment", {
                "invoice_id": str(invoice_id),
                "amount": str(amount),
            })

        data = {
            "invoice_id": invoice_id,
            "amount": amount,
            "payment_date": payment_date or datetime.now().strftime('%Y-%m-%d'),
            "payment_method": payment_method,
            "journal_id": journal_id
        }

        result = self._call_mcp('register_payment', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "register_payment",
                "invoice_id": invoice_id,
                "amount": amount,
                "message": f"Payment of {amount} registered successfully"
            }
        return result

    def _create_accounting_draft(self, action: str, data: Dict) -> Dict:
        """Create an accounting draft file in Pending_Approval/accounting/ (cloud agent)."""
        vault_path = os.getenv("VAULT_PATH", r"D:\prompteng\AI_Employee_Vault")
        draft_dir = Path(vault_path) / "Pending_Approval" / "accounting"
        draft_dir.mkdir(parents=True, exist_ok=True)

        from agent_config import AGENT_ID
        now = datetime.now()
        filename = f"ACCT_DRAFT_{action}_{now.strftime('%Y%m%d_%H%M%S')}.md"
        filepath = draft_dir / filename

        content = f"""---
type: accounting
action: {action}
invoice_id: {data.get('invoice_id', '')}
amount: {data.get('amount', '')}
created_by: {AGENT_ID}
created_at: {now.isoformat()}
status: pending_approval
---

## Accounting Draft

**Action:** {action}
**Invoice ID:** {data.get('invoice_id', '')}
**Amount:** {data.get('amount', '')}

---
*Draft created by Cloud Agent. Approve to execute.*
"""
        filepath.write_text(content, encoding="utf-8")
        return {
            "success": True,
            "action": "draft_file",
            "filepath": str(filepath),
            "filename": filename,
            "status": "pending_approval",
            "message": f"Accounting draft created for {action} (cloud mode)",
        }

    def _get_payments(self, partner_id: Optional[int] = None,
                      state: Optional[str] = None,
                      limit: int = 50) -> Dict:
        """Get payments with optional filters"""
        data = {
            "partner_id": partner_id,
            "state": state,
            "limit": limit
        }

        result = self._call_mcp('get_payments', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "get_payments",
                "payments": result.get("payments"),
                "count": result.get("count")
            }
        return result

    # ==================== CUSTOMER OPERATIONS ====================

    def _get_customers(self, search: Optional[str] = None, limit: int = 50) -> Dict:
        """Get customers"""
        data = {
            "search": search,
            "limit": limit
        }

        result = self._call_mcp('get_customers', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "get_customers",
                "customers": result.get("customers"),
                "count": result.get("count")
            }
        return result

    def _create_customer(self, name: str, email: Optional[str] = None,
                         phone: Optional[str] = None,
                         street: Optional[str] = None,
                         city: Optional[str] = None,
                         country_id: Optional[int] = None,
                         vat: Optional[str] = None) -> Dict:
        """Create a customer"""
        data = {
            "name": name,
            "email": email,
            "phone": phone,
            "street": street,
            "city": city,
            "country_id": country_id,
            "vat": vat
        }

        result = self._call_mcp('create_customer', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "create_customer",
                "customer_id": result.get("customer_id"),
                "message": f"Customer {name} created successfully"
            }
        return result

    # ==================== PRODUCT OPERATIONS ====================

    def _get_products(self, search: Optional[str] = None,
                      type: Optional[str] = None,
                      limit: int = 50) -> Dict:
        """Get products/services"""
        data = {
            "search": search,
            "type": type,
            "limit": limit
        }

        result = self._call_mcp('get_products', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "get_products",
                "products": result.get("products"),
                "count": result.get("count")
            }
        return result

    def _create_product(self, name: str, type: str, list_price: float,
                        description: Optional[str] = None,
                        default_code: Optional[str] = None) -> Dict:
        """Create a product/service"""
        data = {
            "name": name,
            "type": type,
            "list_price": list_price,
            "description": description,
            "default_code": default_code
        }

        result = self._call_mcp('create_product', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "create_product",
                "product_id": result.get("product_id"),
                "message": f"Product {name} created successfully"
            }
        return result

    # ==================== REPORTING OPERATIONS ====================

    def _get_financial_summary(self, date_from: Optional[str] = None,
                                date_to: Optional[str] = None) -> Dict:
        """Get financial summary"""
        data = {
            "date_from": date_from,
            "date_to": date_to
        }

        result = self._call_mcp('get_financial_summary', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "get_financial_summary",
                "summary": result.get("summary")
            }
        return result

    def _get_customer_statements(self, partner_id: int,
                                  date_from: Optional[str] = None,
                                  date_to: Optional[str] = None) -> Dict:
        """Get customer account statements"""
        data = {
            "partner_id": partner_id,
            "date_from": date_from,
            "date_to": date_to
        }

        result = self._call_mcp('get_customer_statements', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "get_customer_statements",
                "statement": result.get("statement")
            }
        return result

    def _get_bank_statements(self, journal_id: Optional[int] = None,
                              state: Optional[str] = None,
                              limit: int = 50) -> Dict:
        """Get bank statements"""
        data = {
            "journal_id": journal_id,
            "state": state,
            "limit": limit
        }

        result = self._call_mcp('get_bank_statements', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "get_bank_statements",
                "statements": result.get("statements"),
                "count": result.get("count")
            }
        return result

    def _get_bank_statement_lines(self, statement_id: Optional[int] = None,
                                   limit: int = 100) -> Dict:
        """Get bank statement lines"""
        data = {
            "statement_id": statement_id,
            "limit": limit
        }

        result = self._call_mcp('get_bank_statement_lines', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "get_bank_statement_lines",
                "lines": result.get("lines"),
                "count": result.get("count")
            }
        return result

    def _health_check(self) -> Dict:
        """Check Odoo MCP server health"""
        url = f"{self.mcp_url}/health"
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Health check failed: {str(e)}"
            }

    def execute(self, context: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the Odoo MCP action skill.

        Parameters:
        - action: The operation to perform
        - Additional parameters based on action (see individual methods)

        Returns:
        - Dictionary with operation results
        """
        action = parameters.get('action')

        # Health check
        if action == 'health':
            return self._health_check()

        # Invoice operations
        elif action == 'create_invoice':
            return self._create_invoice(
                partner_id=parameters['partner_id'],
                lines=parameters['lines'],
                invoice_date=parameters.get('invoice_date'),
                invoice_date_due=parameters.get('invoice_date_due'),
                narration=parameters.get('narration')
            )

        elif action == 'update_invoice':
            return self._update_invoice(
                invoice_id=parameters['invoice_id'],
                values=parameters['values']
            )

        elif action == 'confirm_invoice':
            return self._confirm_invoice(parameters['invoice_id'])

        elif action == 'cancel_invoice':
            return self._cancel_invoice(parameters['invoice_id'])

        elif action == 'reset_invoice_draft':
            return self._reset_invoice_draft(parameters['invoice_id'])

        elif action == 'get_invoice':
            return self._get_invoice(parameters['invoice_id'])

        elif action == 'get_invoices':
            return self._get_invoices(
                partner_id=parameters.get('partner_id'),
                move_type=parameters.get('move_type'),
                state=parameters.get('state'),
                limit=parameters.get('limit', 50)
            )

        # Payment operations
        elif action == 'register_payment':
            return self._register_payment(
                invoice_id=parameters['invoice_id'],
                amount=parameters['amount'],
                payment_date=parameters.get('payment_date'),
                payment_method=parameters.get('payment_method', 'manual'),
                journal_id=parameters.get('journal_id')
            )

        elif action == 'get_payments':
            return self._get_payments(
                partner_id=parameters.get('partner_id'),
                state=parameters.get('state'),
                limit=parameters.get('limit', 50)
            )

        # Customer operations
        elif action == 'get_customers':
            return self._get_customers(
                search=parameters.get('search'),
                limit=parameters.get('limit', 50)
            )

        elif action == 'create_customer':
            return self._create_customer(
                name=parameters['name'],
                email=parameters.get('email'),
                phone=parameters.get('phone'),
                street=parameters.get('street'),
                city=parameters.get('city'),
                country_id=parameters.get('country_id'),
                vat=parameters.get('vat')
            )

        # Product operations
        elif action == 'get_products':
            return self._get_products(
                search=parameters.get('search'),
                type=parameters.get('type'),
                limit=parameters.get('limit', 50)
            )

        elif action == 'create_product':
            return self._create_product(
                name=parameters['name'],
                type=parameters['type'],
                list_price=parameters['list_price'],
                description=parameters.get('description'),
                default_code=parameters.get('default_code')
            )

        # Reporting operations
        elif action == 'get_financial_summary':
            return self._get_financial_summary(
                date_from=parameters.get('date_from'),
                date_to=parameters.get('date_to')
            )

        elif action == 'get_customer_statements':
            return self._get_customer_statements(
                partner_id=parameters['partner_id'],
                date_from=parameters.get('date_from'),
                date_to=parameters.get('date_to')
            )

        elif action == 'get_bank_statements':
            return self._get_bank_statements(
                journal_id=parameters.get('journal_id'),
                state=parameters.get('state'),
                limit=parameters.get('limit', 50)
            )

        elif action == 'get_bank_statement_lines':
            return self._get_bank_statement_lines(
                statement_id=parameters.get('statement_id'),
                limit=parameters.get('limit', 100)
            )

        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }


# Auto-register the skill when module is imported
def _register():
    from ..registry import register_skill
    register_skill(OdooMCPActionSkill, "odoo_mcp_action")

_register()
