"""
Create Odoo Database
Uses Odoo's database manager API
"""

import requests

ODOO_URL = "http://localhost:8069"
MASTER_PASSWORD = "admin"
DB_NAME = "odoo"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin"

# Create database using Odoo's RPC interface
session = requests.Session()

# First, get the CSRF token if needed
print("Creating Odoo database...")
print(f"URL: {ODOO_URL}")
print(f"Database: {DB_NAME}")
print(f"Admin Password: {ADMIN_PASSWORD}")

try:
    # Try the database creation endpoint
    response = session.post(
        f"{ODOO_URL}/web/database/create",
        data={
            'master_pwd': MASTER_PASSWORD,
            'name': DB_NAME,
            'login': 'admin',
            'password': ADMIN_PASSWORD,
            'email': ADMIN_EMAIL,
            'language': 'en_US',
            'country': 'US',
            'demo': '0',
            'phone': '',
        },
        timeout=60
    )
    
    print(f"Response Status: {response.status_code}")
    
    if response.status_code in [200, 302, 303]:
        print("Database created successfully!")
    else:
        print(f"Response: {response.text[:500]}")
        
except Exception as e:
    print(f"Error: {e}")

# Alternative: Use PostgreSQL directly
print("\n--- Alternative: Creating via PostgreSQL ---")
import subprocess

result = subprocess.run(
    ["docker", "exec", "odoo-postgres", "psql", "-U", "odoo", "-c", f"CREATE DATABASE \"{DB_NAME}\" OWNER odoo ENCODING 'UTF8'"],
    capture_output=True,
    text=True
)

if result.returncode == 0:
    print("PostgreSQL database created!")
else:
    print(f"PostgreSQL result: {result.stdout}")
    print(f"PostgreSQL error: {result.stderr}")
