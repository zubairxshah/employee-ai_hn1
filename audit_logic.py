"""
Audit Logic for Business Handover Feature
Analyzes transactions and identifies patterns for subscription auditing
"""

SUBSCRIPTION_PATTERNS = {
    'netflix.com': 'Netflix',
    'spotify.com': 'Spotify',
    'adobe.com': 'Adobe Creative Cloud',
    'notion.so': 'Notion',
    'slack.com': 'Slack',
    'microsoft.com': 'Microsoft 365',
    'google.com': 'Google Workspace',
    'amazon.com': 'Amazon Prime',
    'apple.com': 'Apple iCloud+',
    'dropbox.com': 'Dropbox',
    'zoom.us': 'Zoom Pro',
    'paypal.com': 'Various Services',
    'stripe.com': 'Various Services',
    'github.com': 'GitHub Pro',
    'figma.com': 'Figma Professional',
    'trello.com': 'Trello Gold',
    'asana.com': 'Asana Premium',
    'airtable.com': 'Airtable Pro',
    'calendly.com': 'Calendly Pro',
    'mailchimp.com': 'Mailchimp',
    'hubspot.com': 'HubSpot',
    'salesforce.com': 'Salesforce',
    'workday.com': 'Workday',
    'servicenow.com': 'ServiceNow',
    'zoom': 'Zoom Pro',
    'teams': 'Microsoft Teams',
    'g-suite': 'Google Workspace',
    'creative cloud': 'Adobe Creative Cloud',
    'creative suite': 'Adobe Creative Cloud',
    'office 365': 'Microsoft 365',
    'microsoft office': 'Microsoft 365',
    'adobe': 'Adobe Creative Cloud',
    'notion': 'Notion',
    'slack': 'Slack',
    'trello': 'Trello',
    'asana': 'Asana',
    'airtable': 'Airtable',
    'figma': 'Figma',
    'github': 'GitHub Pro',
    'calendly': 'Calendly Pro',
    'mailchimp': 'Mailchimp',
    'hubspot': 'HubSpot',
    'salesforce': 'Salesforce',
    'aws': 'Amazon Web Services',
    'azure': 'Microsoft Azure',
    'gcp': 'Google Cloud Platform',
    'digitalocean': 'DigitalOcean',
    'linode': 'Linode',
    'heroku': 'Heroku',
    'vercel': 'Vercel',
    'netlify': 'Netlify',
}


def analyze_transaction(transaction):
    """
    Analyze a transaction to identify if it's a subscription
    :param transaction: dict with keys: 'description', 'amount', 'date'
    :return: dict with subscription info or None
    """
    if not isinstance(transaction, dict):
        return None
        
    description = transaction.get('description', '').lower()
    
    for pattern, name in SUBSCRIPTION_PATTERNS.items():
        if pattern in description:
            return {
                'type': 'subscription',
                'name': name,
                'amount': transaction.get('amount'),
                'date': transaction.get('date'),
                'description': transaction.get('description')
            }
    return None


def analyze_transactions(transactions):
    """
    Analyze multiple transactions
    :param transactions: list of transaction dicts
    :return: list of subscription transactions
    """
    subscriptions = []
    for transaction in transactions:
        result = analyze_transaction(transaction)
        if result:
            subscriptions.append(result)
    return subscriptions


def generate_subscription_report(subscriptions):
    """
    Generate a report of subscriptions
    :param subscriptions: list of subscription dicts
    :return: dict with report data
    """
    report = {
        'total_subscriptions': len(subscriptions),
        'monthly_cost': sum(float(s.get('amount', 0)) for s in subscriptions),
        'unique_services': set(s['name'] for s in subscriptions),
        'subscriptions_by_service': {}
    }
    
    for sub in subscriptions:
        service_name = sub['name']
        if service_name not in report['subscriptions_by_service']:
            report['subscriptions_by_service'][service_name] = []
        report['subscriptions_by_service'][service_name].append(sub)
    
    return report


def identify_potential_cancellations(subscriptions, activity_data=None):
    """
    Identify subscriptions that might be candidates for cancellation
    :param subscriptions: list of subscription dicts
    :param activity_data: optional dict with service activity data
    :return: list of potential cancellations
    """
    potential_cancellations = []
    
    for sub in subscriptions:
        # Simple heuristic: if no activity data is provided, flag expensive subscriptions
        # In a real implementation, this would check for actual usage
        amount = float(sub.get('amount', 0))
        
        # Flag subscriptions over $20/month without activity data
        if amount > 20 and not activity_data:
            potential_cancellations.append({
                'service': sub['name'],
                'amount': sub['amount'],
                'description': sub['description'],
                'reason': 'High cost subscription without usage data',
                'action': 'Review usage and consider cancellation'
            })
    
    return potential_cancellations