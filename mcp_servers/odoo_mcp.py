"""
Odoo MCP Server
Provides accounting operations via Odoo's JSON-RPC API

Port: 8005
"""

import json
import requests
from flask import Flask, request, jsonify
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv(override=True)

app = Flask(__name__)

# Odoo Configuration
ODOO_URL = os.getenv('ODOO_URL', 'http://localhost:8069')
ODOO_DB = os.getenv('ODOO_DB', 'odoo')
ODOO_USERNAME = os.getenv('ODOO_USERNAME', 'admin')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD', 'admin')

# Session cache
_odo_session = None


class OdooClient:
    """Odoo JSON-RPC Client"""
    
    def __init__(self, url, db, username, password):
        self.url = url.rstrip('/')
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.session = requests.Session()
        
    def authenticate(self):
        """Authenticate with Odoo and get session"""
        try:
            # Try common authentication first
            payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "db": self.db,
                    "login": self.username,
                    "password": self.password
                },
                "id": 1
            }
            
            response = self.session.post(
                f"{self.url}/web/session/authenticate",
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            result = response.json()
            
            if result.get('result', {}).get('uid'):
                self.uid = result['result']['uid']
                return True
            
            # Fallback: Try JSON-RPC API key authentication
            return self._authenticate_api_key()
            
        except Exception as e:
            print(f"Authentication error: {e}")
            return False
    
    def _authenticate_api_key(self):
        """Authenticate using API key"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "db": self.db,
                    "login": self.username,
                    "key": self.password  # Use password as API key
                },
                "id": 1
            }
            
            response = self.session.post(
                f"{self.url}/jsonrpc",
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            result = response.json()
            
            if result.get('result'):
                self.uid = result['result']
                return True
            
            return False
        except Exception as e:
            print(f"API key authentication error: {e}")
            return False
    
    def execute(self, model, method, *args, **kwargs):
        """Execute a method on a model"""
        if not self.uid:
            if not self.authenticate():
                raise Exception("Not authenticated with Odoo")

        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    self.db,
                    self.uid,
                    self.password,
                    model,
                    method,
                    list(args),
                    kwargs
                ]
            },
            "id": kwargs.get('id', 2)
        }

        response = self.session.post(
            f"{self.url}/jsonrpc",
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        result = response.json()

        if 'error' in result:
            raise Exception(f"Odoo error: {result['error'].get('message', 'Unknown error')}")

        return result.get('result')
    
    def search_read(self, model, domain=None, fields=None, limit=80, offset=0, order=None):
        """Search and read records"""
        args = [domain or []]
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
        if limit:
            kwargs['limit'] = limit
        if offset:
            kwargs['offset'] = offset
        if order:
            kwargs['order'] = order
        return self.execute(
            model,
            "search_read",
            *args,
            **kwargs
        )
    
    def create(self, model, values):
        """Create a record"""
        return self.execute(model, "create", values)
    
    def write(self, model, ids, values):
        """Update records"""
        if isinstance(ids, int):
            ids = [ids]
        return self.execute(model, "write", ids, values)
    
    def unlink(self, model, ids):
        """Delete records"""
        if isinstance(ids, int):
            ids = [ids]
        return self.execute(model, "unlink", ids)
    
    def search(self, model, domain=None):
        """Search for record IDs"""
        return self.execute(model, "search", domain or [])


# Global Odoo client
odoo_client = None


def get_odoo_client():
    """Get or create Odoo client"""
    global odoo_client
    if odoo_client is None:
        odoo_client = OdooClient(ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD)
        odoo_client.authenticate()
    return odoo_client


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    client = get_odoo_client()
    connected = client.uid is not None
    return jsonify({
        'status': 'healthy' if connected else 'degraded',
        'odoo_connected': connected,
        'odoo_url': ODOO_URL,
        'database': ODOO_DB,
        'user_id': client.uid,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/authenticate', methods=['POST'])
def authenticate():
    """Re-authenticate with Odoo"""
    global odoo_client
    odoo_client = None  # Reset client
    client = get_odoo_client()
    
    if client.uid:
        return jsonify({
            'success': True,
            'user_id': client.uid,
            'message': 'Authenticated successfully'
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Authentication failed'
        }), 401


# ==================== INVOICE OPERATIONS ====================

@app.route('/create_invoice', methods=['POST'])
def create_invoice():
    """
    Create a customer invoice
    
    Body:
    {
        "partner_id": 123,           # Customer ID (required)
        "invoice_date": "2026-02-25", # Invoice date
        "invoice_date_due": "2026-03-25", # Due date
        "lines": [                    # Invoice lines (required)
            {
                "product_id": 456,    # Product ID (optional)
                "name": "Service",    # Description
                "quantity": 1,
                "price_unit": 1000.00,
                "tax_ids": [[6, 0, [1]]]  # Tax IDs (optional)
            }
        ],
        "narration": "Thank you"     # Optional notes
    }
    """
    try:
        data = request.json
        client = get_odoo_client()
        
        if not data.get('partner_id'):
            return jsonify({'error': 'partner_id is required'}), 400
        
        if not data.get('lines'):
            return jsonify({'error': 'lines array is required'}), 400
        
        # Prepare invoice values
        invoice_values = {
            'move_type': 'out_invoice',
            'partner_id': data['partner_id'],
            'invoice_date': data.get('invoice_date', datetime.now().strftime('%Y-%m-%d')),
            'invoice_date_due': data.get('invoice_date_due'),
            'narration': data.get('narration', ''),
            'invoice_line_ids': []
        }
        
        # Prepare invoice lines
        for line in data['lines']:
            line_values = [0, 0, {
                'name': line.get('name', 'Service'),
                'quantity': line.get('quantity', 1),
                'price_unit': line.get('price_unit', 0)
            }]
            
            if line.get('product_id'):
                line_values[2]['product_id'] = line['product_id']
            
            if line.get('tax_ids'):
                line_values[2]['tax_ids'] = line['tax_ids']
            
            invoice_values['invoice_line_ids'].append(line_values)
        
        # Create invoice
        invoice_id = client.create('account.move', invoice_values)
        
        return jsonify({
            'success': True,
            'invoice_id': invoice_id,
            'message': f'Invoice {invoice_id} created successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/update_invoice', methods=['POST'])
def update_invoice():
    """
    Update an invoice
    
    Body:
    {
        "invoice_id": 123,
        "values": {
            "narration": "Updated notes",
            "invoice_date_due": "2026-04-01"
        }
    }
    """
    try:
        data = request.json
        client = get_odoo_client()
        
        if not data.get('invoice_id'):
            return jsonify({'error': 'invoice_id is required'}), 400
        
        if not data.get('values'):
            return jsonify({'error': 'values dict is required'}), 400
        
        client.write('account.move', data['invoice_id'], data['values'])
        
        return jsonify({
            'success': True,
            'message': f'Invoice {data["invoice_id"]} updated successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/confirm_invoice', methods=['POST'])
def confirm_invoice():
    """
    Confirm/post an invoice
    
    Body:
    {
        "invoice_id": 123
    }
    """
    try:
        data = request.json
        client = get_odoo_client()
        
        if not data.get('invoice_id'):
            return jsonify({'error': 'invoice_id is required'}), 400
        
        client.execute('account.move', 'action_post', [data['invoice_id']])
        
        return jsonify({
            'success': True,
            'message': f'Invoice {data["invoice_id"]} confirmed successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/cancel_invoice', methods=['POST'])
def cancel_invoice():
    """
    Cancel an invoice
    
    Body:
    {
        "invoice_id": 123
    }
    """
    try:
        data = request.json
        client = get_odoo_client()
        
        if not data.get('invoice_id'):
            return jsonify({'error': 'invoice_id is required'}), 400
        
        client.execute('account.move', 'action_cancel', [data['invoice_id']])
        
        return jsonify({
            'success': True,
            'message': f'Invoice {data["invoice_id"]} cancelled successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/reset_invoice_draft', methods=['POST'])
def reset_invoice_draft():
    """
    Reset an invoice to draft
    
    Body:
    {
        "invoice_id": 123
    }
    """
    try:
        data = request.json
        client = get_odoo_client()
        
        if not data.get('invoice_id'):
            return jsonify({'error': 'invoice_id is required'}), 400
        
        client.execute('account.move', 'action_draft', [data['invoice_id']])
        
        return jsonify({
            'success': True,
            'message': f'Invoice {data["invoice_id"]} reset to draft'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/get_invoices', methods=['POST'])
def get_invoices():
    """
    Get invoices with optional filters

    Body:
    {
        "partner_id": 123,           # Filter by customer (optional)
        "move_type": "out_invoice",  # Invoice type (optional)
        "state": "posted",           # Status: draft, posted, cancel (optional)
        "ref": "INV-002",            # Filter by Customer Reference (optional)
        "limit": 50                  # Limit results (optional)
    }
    """
    try:
        data = request.json or {}
        client = get_odoo_client()

        domain = []

        if data.get('partner_id'):
            domain.append(['partner_id', '=', data['partner_id']])

        if data.get('move_type'):
            domain.append(['move_type', '=', data['move_type']])

        if data.get('state'):
            domain.append(['state', '=', data['state']])

        if data.get('ref'):
            domain.append(['ref', '=', data['ref']])

        invoices = client.search_read(
            'account.move',
            domain=domain,
            fields=[
                'name', 'ref', 'partner_id', 'invoice_date', 'invoice_date_due',
                'amount_total', 'amount_residual', 'payment_state', 'state',
                'currency_id', 'create_date'
            ],
            limit=data.get('limit', 50)
        )
        
        return jsonify({
            'success': True,
            'invoices': invoices,
            'count': len(invoices)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/get_invoice', methods=['POST'])
def get_invoice():
    """
    Get a single invoice by ID
    
    Body:
    {
        "invoice_id": 123
    }
    """
    try:
        data = request.json
        client = get_odoo_client()
        
        if not data.get('invoice_id'):
            return jsonify({'error': 'invoice_id is required'}), 400
        
        invoices = client.search_read(
            'account.move',
            domain=[['id', '=', data['invoice_id']]],
            fields=[
                'name', 'partner_id', 'invoice_date', 'invoice_date_due',
                'amount_total', 'amount_residual', 'payment_state', 'state',
                'currency_id', 'narration', 'invoice_line_ids', 'create_date'
            ]
        )
        
        if not invoices:
            return jsonify({'error': 'Invoice not found'}), 404
        
        return jsonify({
            'success': True,
            'invoice': invoices[0]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== PAYMENT OPERATIONS ====================

@app.route('/register_payment', methods=['POST'])
def register_payment():
    """
    Register a payment for an invoice.

    Body:
    {
        "invoice_id": 123,            # Invoice to pay (required)
        "amount": 1000.00,            # Payment amount (required)
        "payment_date": "2026-02-25", # Payment date (optional, defaults to today)
        "journal_id": 1               # Journal ID (optional, Odoo picks the default bank journal)
    }

    Implementation: uses Odoo's account.payment.register wizard, which requires
    active_model='account.move' + active_ids=[invoice_id] in the call context.
    Lets Odoo pick the payment method line automatically based on the journal.
    """
    try:
        data = request.json
        client = get_odoo_client()

        if not data.get('invoice_id'):
            return jsonify({'error': 'invoice_id is required'}), 400

        if not data.get('amount'):
            return jsonify({'error': 'amount is required'}), 400

        invoice_id = data['invoice_id']

        wizard_values = {
            'amount': data['amount'],
            'payment_date': data.get('payment_date', datetime.now().strftime('%Y-%m-%d')),
        }
        if data.get('journal_id'):
            wizard_values['journal_id'] = data['journal_id']

        # The wizard's default-get reads active_model/active_ids from context to
        # find which invoices are being paid. Without these, the wizard errors
        # out with cryptic 500s.
        ctx = {
            'active_model': 'account.move',
            'active_ids': [invoice_id],
            'active_id': invoice_id,
        }

        wizard_id = client.execute(
            'account.payment.register', 'create', wizard_values, context=ctx
        )
        client.execute(
            'account.payment.register', 'action_create_payments', [wizard_id], context=ctx
        )

        # Read back the invoice to confirm payment state changed
        inv = client.search_read(
            'account.move',
            [['id', '=', invoice_id]],
            fields=['name', 'ref', 'amount_total', 'amount_residual', 'payment_state'],
            limit=1,
        )
        return jsonify({
            'success': True,
            'message': f'Payment of {data["amount"]} registered against invoice {invoice_id}',
            'invoice': inv[0] if inv else None,
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/get_payments', methods=['POST'])
def get_payments():
    """
    Get payments with optional filters
    
    Body:
    {
        "partner_id": 123,           # Filter by customer (optional)
        "state": "posted",           # Status: draft, posted, cancel (optional)
        "limit": 50                  # Limit results (optional)
    }
    """
    try:
        data = request.json or {}
        client = get_odoo_client()
        
        # Build domain
        domain = []
        
        if data.get('partner_id'):
            domain.append(['partner_id', '=', data['partner_id']])
        
        if data.get('state'):
            domain.append(['state', '=', data['state']])
        
        # Get payments
        payments = client.search_read(
            'account.payment',
            domain=domain,
            fields=[
                'name', 'partner_id', 'payment_date', 'amount',
                'payment_type', 'state', 'currency_id', 'create_date'
            ],
            limit=data.get('limit', 50)
        )
        
        return jsonify({
            'success': True,
            'payments': payments,
            'count': len(payments)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== CUSTOMER OPERATIONS ====================

@app.route('/get_customers', methods=['POST'])
def get_customers():
    """
    Get customers (partners)
    
    Body:
    {
        "search": "John",            # Search term (optional)
        "limit": 50                  # Limit results (optional)
    }
    """
    try:
        data = request.json or {}
        client = get_odoo_client()
        
        # Build domain
        domain = [['customer_rank', '>', 0]]
        
        if data.get('search'):
            domain.append(['|', ['name', 'ilike', data['search']], ['email', 'ilike', data['search']]])
        
        # Get customers
        customers = client.search_read(
            'res.partner',
            domain=domain,
            fields=[
                'name', 'email', 'phone', 'street', 'city', 'country_id',
                'vat', 'customer_rank', 'create_date'
            ],
            limit=data.get('limit', 50)
        )
        
        return jsonify({
            'success': True,
            'customers': customers,
            'count': len(customers)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/create_customer', methods=['POST'])
def create_customer():
    """
    Create a customer
    
    Body:
    {
        "name": "John Doe",          # Name (required)
        "email": "john@example.com", # Email (optional)
        "phone": "+1234567890",      # Phone (optional)
        "street": "123 Main St",     # Address (optional)
        "city": "New York",          # City (optional)
        "country_id": 233,           # Country ID (optional)
        "vat": "US123456789"         # VAT number (optional)
    }
    """
    try:
        data = request.json
        client = get_odoo_client()
        
        if not data.get('name'):
            return jsonify({'error': 'name is required'}), 400
        
        customer_values = {
            'name': data['name'],
            'customer_rank': 1  # Mark as customer
        }
        
        # Add optional fields
        optional_fields = ['email', 'phone', 'street', 'city', 'vat']
        for field in optional_fields:
            if field in data:
                customer_values[field] = data[field]
        
        if data.get('country_id'):
            customer_values['country_id'] = data['country_id']
        
        customer_id = client.create('res.partner', customer_values)
        
        return jsonify({
            'success': True,
            'customer_id': customer_id,
            'message': f'Customer {data["name"]} created successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== PRODUCT OPERATIONS ====================

@app.route('/get_products', methods=['POST'])
def get_products():
    """
    Get products/services
    
    Body:
    {
        "search": "Consulting",      # Search term (optional)
        "type": "service",           # Type: product, service (optional)
        "limit": 50                  # Limit results (optional)
    }
    """
    try:
        data = request.json or {}
        client = get_odoo_client()
        
        # Build domain
        domain = []
        
        if data.get('type'):
            domain.append(['type', '=', data['type']])
        
        if data.get('search'):
            domain.append(['|', ['name', 'ilike', data['search']], ['description', 'ilike', data['search']]])
        
        # Get products
        products = client.search_read(
            'product.template',
            domain=domain,
            fields=[
                'name', 'description', 'list_price', 'type', 'taxes_id',
                'default_code', 'create_date'
            ],
            limit=data.get('limit', 50)
        )
        
        return jsonify({
            'success': True,
            'products': products,
            'count': len(products)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/create_product', methods=['POST'])
def create_product():
    """
    Create a product/service
    
    Body:
    {
        "name": "Consulting Service", # Name (required)
        "type": "service",           # Type: product, service (required)
        "list_price": 100.00,        # Price (required)
        "description": "Description", # Description (optional)
        "default_code": "CONS001"    # Internal reference (optional)
    }
    """
    try:
        data = request.json
        client = get_odoo_client()
        
        if not data.get('name'):
            return jsonify({'error': 'name is required'}), 400
        
        if not data.get('type'):
            return jsonify({'error': 'type is required (product or service)'}), 400
        
        if not data.get('list_price'):
            return jsonify({'error': 'list_price is required'}), 400
        
        product_values = {
            'name': data['name'],
            'type': data['type'],
            'list_price': data['list_price']
        }
        
        # Add optional fields
        if data.get('description'):
            product_values['description'] = data['description']
        
        if data.get('default_code'):
            product_values['default_code'] = data['default_code']
        
        product_id = client.create('product.template', product_values)
        
        return jsonify({
            'success': True,
            'product_id': product_id,
            'message': f'Product {data["name"]} created successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== REPORTING OPERATIONS ====================

@app.route('/get_financial_summary', methods=['POST'])
def get_financial_summary():
    """
    Get financial summary
    
    Body:
    {
        "date_from": "2026-02-01",   # Start date (optional)
        "date_to": "2026-02-28"      # End date (optional)
    }
    """
    try:
        data = request.json or {}
        client = get_odoo_client()
        
        date_from = data.get('date_from', datetime.now().replace(day=1).strftime('%Y-%m-%d'))
        date_to = data.get('date_to', datetime.now().strftime('%Y-%m-%d'))
        
        # Get total receivables (unpaid customer invoices)
        receivables = client.search_read(
            'account.move',
            domain=[
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', '!=', 'paid'),
                ('invoice_date', '>=', date_from),
                ('invoice_date', '<=', date_to)
            ],
            fields=['amount_total', 'amount_residual']
        )
        
        total_receivables = sum(r.get('amount_residual', 0) for r in receivables)
        total_invoiced = sum(r.get('amount_total', 0) for r in receivables)
        
        # Get total payables (unpaid vendor bills)
        payables = client.search_read(
            'account.move',
            domain=[
                ('move_type', '=', 'in_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', '!=', 'paid'),
                ('invoice_date', '>=', date_from),
                ('invoice_date', '<=', date_to)
            ],
            fields=['amount_total', 'amount_residual']
        )
        
        total_payables = sum(p.get('amount_residual', 0) for p in payables)
        total_billed = sum(p.get('amount_total', 0) for p in payables)
        
        return jsonify({
            'success': True,
            'summary': {
                'period': {'from': date_from, 'to': date_to},
                'receivables': {
                    'total_invoiced': total_invoiced,
                    'total_outstanding': total_receivables,
                    'invoice_count': len(receivables)
                },
                'payables': {
                    'total_billed': total_billed,
                    'total_outstanding': total_payables,
                    'bill_count': len(payables)
                },
                'net_position': total_receivables - total_payables
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/get_customer_statements', methods=['POST'])
def get_customer_statements():
    """
    Get customer account statements
    
    Body:
    {
        "partner_id": 123,           # Customer ID (required)
        "date_from": "2026-02-01",   # Start date (optional)
        "date_to": "2026-02-28"      # End date (optional)
    }
    """
    try:
        data = request.json
        client = get_odoo_client()
        
        if not data.get('partner_id'):
            return jsonify({'error': 'partner_id is required'}), 400
        
        date_from = data.get('date_from', datetime.now().replace(day=1).strftime('%Y-%m-%d'))
        date_to = data.get('date_to', datetime.now().strftime('%Y-%m-%d'))
        
        # Get all moves for customer
        moves = client.search_read(
            'account.move',
            domain=[
                ('partner_id', '=', data['partner_id']),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', date_from),
                ('invoice_date', '<=', date_to)
            ],
            fields=['name', 'move_type', 'invoice_date', 'amount_total', 'amount_residual', 'payment_state']
        )
        
        # Get all payments for customer
        payments = client.search_read(
            'account.payment',
            domain=[
                ('partner_id', '=', data['partner_id']),
                ('state', '=', 'posted'),
                ('payment_date', '>=', date_from),
                ('payment_date', '<=', date_to)
            ],
            fields=['name', 'payment_date', 'amount', 'payment_type']
        )
        
        return jsonify({
            'success': True,
            'statement': {
                'partner_id': data['partner_id'],
                'period': {'from': date_from, 'to': date_to},
                'invoices': moves,
                'payments': payments,
                'total_invoiced': sum(m.get('amount_total', 0) for m in moves),
                'total_paid': sum(m.get('amount_total', 0) - m.get('amount_residual', 0) for m in moves),
                'outstanding': sum(m.get('amount_residual', 0) for m in moves)
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== BANK OPERATIONS ====================

@app.route('/get_bank_statements', methods=['POST'])
def get_bank_statements():
    """
    Get bank statements

    Body:
    {
        "journal_id": 1,             # Bank journal ID (optional)
        "limit": 50                  # Limit results (optional)
    }

    Note: Odoo 17 moved `state` off account.bank.statement onto
    account.bank.statement.line, so state filtering must be done via
    /get_bank_statement_lines.
    """
    try:
        data = request.json or {}
        client = get_odoo_client()

        domain = []
        if data.get('journal_id'):
            domain.append(['journal_id', '=', data['journal_id']])

        statements = client.search_read(
            'account.bank.statement',
            domain=domain,
            fields=[
                'name', 'journal_id', 'date', 'balance_start', 'balance_end',
                'balance_end_real', 'line_ids', 'create_date'
            ],
            limit=data.get('limit', 50)
        )
        
        return jsonify({
            'success': True,
            'statements': statements,
            'count': len(statements)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/get_bank_statement_lines', methods=['POST'])
def get_bank_statement_lines():
    """
    Get bank statement lines
    
    Body:
    {
        "statement_id": 123,         # Statement ID (optional)
        "limit": 100                 # Limit results (optional)
    }
    """
    try:
        data = request.json or {}
        client = get_odoo_client()
        
        # Build domain
        domain = []
        
        if data.get('statement_id'):
            domain.append(['statement_id', '=', data['statement_id']])
        
        # Get bank statement lines
        lines = client.search_read(
            'account.bank.statement.line',
            domain=domain,
            fields=[
                'name', 'date', 'amount', 'partner_id', 'statement_id',
                'payment_ref', 'narration', 'state'
            ],
            limit=data.get('limit', 100)
        )
        
        return jsonify({
            'success': True,
            'lines': lines,
            'count': len(lines)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("Starting Odoo MCP Server on port 8005...")
    print(f"Odoo URL: {ODOO_URL}")
    print(f"Database: {ODOO_DB}")
    print(f"Username: {ODOO_USERNAME}")
    print()
    print("Available endpoints:")
    print("  Health: GET /health")
    print("  Authenticate: POST /authenticate")
    print()
    print("Invoice Operations:")
    print("  POST /create_invoice")
    print("  POST /update_invoice")
    print("  POST /confirm_invoice")
    print("  POST /cancel_invoice")
    print("  POST /reset_invoice_draft")
    print("  POST /get_invoices")
    print("  POST /get_invoice")
    print()
    print("Payment Operations:")
    print("  POST /register_payment")
    print("  POST /get_payments")
    print()
    print("Customer Operations:")
    print("  POST /get_customers")
    print("  POST /create_customer")
    print()
    print("Product Operations:")
    print("  POST /get_products")
    print("  POST /create_product")
    print()
    print("Reporting Operations:")
    print("  POST /get_financial_summary")
    print("  POST /get_customer_statements")
    print()
    print("Bank Operations:")
    print("  POST /get_bank_statements")
    print("  POST /get_bank_statement_lines")
    
    app.run(host='0.0.0.0', port=8005, debug=False)
