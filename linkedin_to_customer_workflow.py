"""
LinkedIn to Customer Workflow
Parses LinkedIn messages/connection requests and creates customers in Odoo

Workflow:
1. LinkedIn watcher detects new messages/connection requests
2. Parser extracts lead details (name, company, message)
3. Creates customer/lead in Odoo
4. Tracks lead status
5. Optional: Send follow-up email
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
INCOMING_LINKEDIN_DIR = os.path.join(VAULT_PATH, "Incoming_LinkedIn")
PROCESSED_LINKEDIN_DIR = os.path.join(VAULT_PATH, "Processed_LinkedIn")
LEADS_DIR = os.path.join(VAULT_PATH, "Leads")

ODOO_MCP_URL = "http://localhost:8005"
EMAIL_MCP_URL = "http://localhost:8001"

# Lead scoring thresholds
LEAD_SCORE_HOT = 80      # Ready for immediate follow-up
LEAD_SCORE_WARM = 50     # Needs nurturing
LEAD_SCORE_COLD = 20     # Low priority


class LinkedInLeadWorkflow:
    """
    Workflow for converting LinkedIn leads to Odoo customers
    """

    def __init__(self):
        self.odoo_mcp_url = ODOO_MCP_URL
        self.email_mcp_url = EMAIL_MCP_URL

        # Create directories
        Path(INCOMING_LINKEDIN_DIR).mkdir(parents=True, exist_ok=True)
        Path(PROCESSED_LINKEDIN_DIR).mkdir(parents=True, exist_ok=True)
        Path(LEADS_DIR).mkdir(parents=True, exist_ok=True)

    def parse_linkedin_message(self, message_data: Dict) -> Optional[Dict]:
        """
        Parse LinkedIn message to extract lead details

        Returns dict with:
        - name, company, email, phone
        - message_content, connection_date
        - lead_score, lead_source
        - keywords (interests mentioned)
        """
        data = {
            'name': None,
            'company': None,
            'email': None,
            'phone': None,
            'headline': None,
            'message_content': '',
            'connection_date': datetime.now().isoformat(),
            'lead_score': 0,
            'lead_source': 'LinkedIn',
            'keywords': [],
            'interests': [],
            'linkedin_url': message_data.get('profile_url', ''),
            'linkedin_urn': message_data.get('person_urn', '')
        }

        # Extract name
        data['name'] = message_data.get('sender_name', '')
        
        # Extract headline/company from profile
        headline = message_data.get('headline', '')
        data['headline'] = headline
        
        # Try to extract company from headline
        if headline:
            # Common patterns: "Role at Company", "Role | Company"
            company_match = re.search(r'(?:at|@|\|)\s*([A-Za-z][\w\s\.]+)', headline)
            if company_match:
                data['company'] = company_match.group(1).strip()

        # Extract email if provided
        message = message_data.get('message', '')
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', message)
        if email_match:
            data['email'] = email_match.group()

        # Extract phone if provided
        phone_match = re.search(r'(?:phone|call|tel)[:\s]*(\+?[\d\s\-\(\)]+)', message, re.IGNORECASE)
        if phone_match:
            data['phone'] = phone_match.group(1).strip()

        # Store message content
        data['message_content'] = message

        # Calculate lead score based on keywords and engagement
        data['lead_score'], data['keywords'], data['interests'] = self._calculate_lead_score(message, headline)

        return data

    def _calculate_lead_score(self, message: str, headline: str) -> Tuple[int, List[str], List[str]]:
        """
        Calculate lead score based on message content and profile

        Returns: (score, keywords, interests)
        """
        score = 20  # Base score for any connection
        keywords = []
        interests = []

        text = (message + ' ' + headline).lower()

        # High-intent keywords (+20 points each)
        high_intent = ['interested', 'want', 'need', 'looking for', 'require', 'budget', 'pricing', 'quote', 'proposal']
        for keyword in high_intent:
            if keyword in text:
                score += 20
                keywords.append(keyword)

        # Medium-intent keywords (+10 points each)
        medium_intent = ['learn more', 'discuss', 'meeting', 'call', 'chat', 'explore', 'opportunity']
        for keyword in medium_intent:
            if keyword in text:
                score += 10
                keywords.append(keyword)

        # Business-related keywords (+5 points each)
        business_terms = ['business', 'company', 'service', 'product', 'solution', 'project', 'contract']
        for keyword in business_terms:
            if keyword in text:
                score += 5
                keywords.append(keyword)

        # Identify interests
        if any(term in text for term in ['marketing', 'advertising', 'promotion']):
            interests.append('Marketing')
        if any(term in text for term in ['sales', 'revenue', 'growth']):
            interests.append('Sales')
        if any(term in text for term in ['technology', 'software', 'digital']):
            interests.append('Technology')
        if any(term in text for term in ['consulting', 'advisory', 'strategy']):
            interests.append('Consulting')

        # Cap score at 100
        score = min(score, 100)

        return score, list(set(keywords)), list(set(interests))

    def get_or_create_lead_customer(self, lead_data: Dict) -> Optional[int]:
        """
        Get existing customer or create new lead in Odoo

        Returns customer_id or None
        """
        try:
            # First, try to find existing customer by email or name
            search_term = lead_data.get('email') or lead_data.get('name')
            
            if search_term:
                response = requests.post(
                    f"{self.odoo_mcp_url}/get_customers",
                    json={'search': search_term, 'limit': 10},
                    timeout=30
                )
                result = response.json()

                if result.get('success') and result.get('customers'):
                    # Check if any customer matches
                    for customer in result.get('customers', []):
                        cust_email = customer.get('email', '')
                        cust_name = customer.get('name', '')
                        
                        if lead_data.get('email') and cust_email == lead_data['email']:
                            print(f"[INFO] Found existing customer by email: {cust_name}")
                            return customer.get('id')
                        
                        if lead_data.get('name') and cust_name == lead_data['name']:
                            print(f"[INFO] Found existing customer by name: {cust_name}")
                            return customer.get('id')

            # Create new customer/lead
            customer_data = {
                'name': lead_data.get('name') or lead_data.get('email') or 'Unknown Lead',
                'email': lead_data.get('email'),
                'phone': lead_data.get('phone'),
            }

            # Add company info
            if lead_data.get('company'):
                customer_data['street'] = lead_data['company']  # Use street for company temporarily

            # Add LinkedIn info to customer record
            if lead_data.get('linkedin_url'):
                customer_data['vat'] = f"LinkedIn: {lead_data['linkedin_url']}"  # Use VAT field for LinkedIn URL

            print(f"[INFO] Creating new lead: {customer_data['name']} (Score: {lead_data.get('lead_score', 0)})")

            response = requests.post(
                f"{self.odoo_mcp_url}/create_customer",
                json=customer_data,
                timeout=30
            )
            result = response.json()

            if result.get('success'):
                customer_id = result.get('customer_id')
                print(f"[OK] Lead created with ID: {customer_id}")
                
                # Save lead details to file for tracking
                self._save_lead_record(customer_id, lead_data)
                
                return customer_id
            else:
                print(f"[ERROR] Failed to create lead: {result.get('error')}")
                return None

        except Exception as e:
            print(f"[ERROR] Error in get_or_create_lead_customer: {e}")
            return None

    def _save_lead_record(self, customer_id: int, lead_data: Dict):
        """Save lead record to file for tracking"""
        filename = f"LEAD_{customer_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(LEADS_DIR, filename)

        record = {
            'customer_id': customer_id,
            'lead_data': lead_data,
            'created': datetime.now().isoformat(),
            'status': 'new',  # new, contacted, qualified, converted, lost
            'notes': []
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(record, f, indent=2)

        return filepath

    def send_follow_up_email(self, customer_id: int, lead_data: Dict) -> bool:
        """
        Send follow-up email to new LinkedIn lead

        Returns True if email sent successfully
        """
        try:
            customer_email = lead_data.get('email')
            if not customer_email:
                print(f"[INFO] No email available for follow-up")
                return False

            # Create personalized follow-up email
            name = lead_data.get('name', 'there')
            company = lead_data.get('company', '')
            interests = ', '.join(lead_data.get('interests', [])) or 'our services'
            
            email_body = f"""Dear {name},

Thank you for connecting with us on LinkedIn!

I noticed your interest in {interests}, and I'd love to explore how we can help you achieve your goals.

{f'Your company, {company}, sounds like an interesting organization.' if company else ''}

Would you be available for a brief call next week to discuss potential opportunities?

Looking forward to hearing from you!

Best regards,
AI Employee System
"""

            # Send via Email MCP
            email_data = {
                "to": customer_email,
                "subject": f"Great connecting with you on LinkedIn, {name}!",
                "body": email_body
            }

            print(f"[EMAIL] Sending follow-up to: {customer_email}")

            response = requests.post(
                f"{self.email_mcp_url}/send_email",
                json=email_data,
                timeout=30
            )
            result = response.json()

            if result.get("success"):
                print(f"[OK] Follow-up email sent to {customer_email}")
                return True
            else:
                print(f"[WARN] Email send failed: {result.get('error')}")
                return False

        except requests.exceptions.ConnectionError:
            print(f"[WARN] Email MCP server not running - skipping follow-up")
            return False
        except Exception as e:
            print(f"[ERROR] Error sending follow-up email: {e}")
            return False

    def process_linkedin_lead(self, message_data: Dict, send_follow_up: bool = True) -> Dict:
        """
        Process a LinkedIn lead

        Args:
            message_data: Dict with sender_name, message, headline, profile_url, person_urn
            send_follow_up: Whether to send follow-up email

        Returns:
            Processing result dict
        """
        result = {
            'success': False,
            'customer_id': None,
            'lead_score': 0,
            'follow_up_sent': False,
            'error': None
        }

        print("\n" + "=" * 60)
        print("[LINKEDIN LEAD] Processing new lead")
        print("=" * 60)
        print(f"Sender: {message_data.get('sender_name', 'Unknown')}")
        print(f"Headline: {message_data.get('headline', 'N/A')}")

        # Step 1: Parse LinkedIn message
        print("\n[STEP 1] Parsing LinkedIn message...")
        parsed_data = self.parse_linkedin_message(message_data)

        if not parsed_data:
            result['error'] = "Failed to parse LinkedIn message"
            return result

        print(f"[OK] Lead score: {parsed_data.get('lead_score', 0)}")
        print(f"   Keywords: {', '.join(parsed_data.get('keywords', []))}")
        print(f"   Interests: {', '.join(parsed_data.get('interests', []))}")

        # Step 2: Get or create customer in Odoo
        print("\n[STEP 2] Creating lead in Odoo...")
        customer_id = self.get_or_create_lead_customer(parsed_data)

        if not customer_id:
            result['error'] = "Failed to create lead in Odoo"
            return result

        result['customer_id'] = customer_id
        result['lead_score'] = parsed_data.get('lead_score', 0)

        # Step 3: Send follow-up email (if enabled and score is high enough)
        if send_follow_up and parsed_data.get('lead_score', 0) >= LEAD_SCORE_WARM:
            print(f"\n[STEP 3] Sending follow-up email (score: {parsed_data.get('lead_score', 0)} >= {LEAD_SCORE_WARM})...")
            follow_up_success = self.send_follow_up_email(customer_id, parsed_data)
            result['follow_up_sent'] = follow_up_success
        else:
            print(f"\n[STEP 3] Skipping follow-up (score: {parsed_data.get('lead_score', 0)} < {LEAD_SCORE_WARM})")

        result['success'] = True
        print("\n" + "=" * 60)
        print("[LINKEDIN LEAD] Processing complete")
        print("=" * 60)

        return result

    def save_message_for_processing(self, message_id: str, message_data: Dict):
        """Save LinkedIn message to incoming directory"""
        filename = f"LINKEDIN_{message_id}.json"
        filepath = os.path.join(INCOMING_LINKEDIN_DIR, filename)

        data = {
            'message_id': message_id,
            'message_data': message_data,
            'received': datetime.now().isoformat()
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        return filepath

    def mark_message_processed(self, message_id: str):
        """Move message to processed directory"""
        src_file = os.path.join(INCOMING_LINKEDIN_DIR, f"LINKEDIN_{message_id}.json")
        dst_file = os.path.join(PROCESSED_LINKEDIN_DIR, f"LINKEDIN_{message_id}.json")

        if os.path.exists(src_file):
            if os.path.exists(dst_file):
                try:
                    os.remove(src_file)
                except:
                    pass
            else:
                os.rename(src_file, dst_file)


# Global workflow instance
_workflow = None


def get_workflow() -> LinkedInLeadWorkflow:
    """Get or create workflow instance"""
    global _workflow
    if _workflow is None:
        _workflow = LinkedInLeadWorkflow()
    return _workflow


def process_linkedin_message(message_id: str, message_data: Dict, send_follow_up: bool = True) -> Dict:
    """
    Process a LinkedIn message and create lead

    Args:
        message_id: Unique message identifier
        message_data: Dict with sender_name, message, headline, profile_url, person_urn
        send_follow_up: Whether to send follow-up email

    Returns:
        Processing result dict
    """
    workflow = get_workflow()

    # Save message for tracking
    workflow.save_message_for_processing(message_id, message_data)

    # Process the lead
    result = workflow.process_linkedin_lead(message_data, send_follow_up)

    # Mark as processed
    if result.get('success'):
        workflow.mark_message_processed(message_id)

    return result


if __name__ == "__main__":
    # Test with sample LinkedIn message
    test_message = {
        'sender_name': 'Sarah Johnson',
        'headline': 'Marketing Director at TechCorp Inc.',
        'message': '''Hi! I came across your profile and I'm very interested in learning more about your services. We're looking for a solution to help with our marketing automation. Would love to discuss this opportunity further. You can reach me at sarah@techcorp.com or call me at +1-555-0123.''',
        'profile_url': 'https://www.linkedin.com/in/sarahjohnson',
        'person_urn': 'sarah_johnson_123'
    }

    result = process_linkedin_message('test_linkedin_001', test_message, send_follow_up=True)
    print(f"\nResult: {json.dumps(result, indent=2)}")
