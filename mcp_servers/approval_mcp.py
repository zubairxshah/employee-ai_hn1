"""
Approval System for Human-in-the-Loop
Manages approval requests for sensitive actions
"""

import os
import json
from pathlib import Path
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import uuid


app = Flask(__name__)

VAULT_PATH = os.getenv("VAULT_PATH", r"D:\prompteng\AI_Employee_Vault")
PENDING_APPROVAL_DIR = os.path.join(VAULT_PATH, "Pending_Approval")
APPROVED_DIR = os.path.join(VAULT_PATH, "Approved")
REJECTED_DIR = os.path.join(VAULT_PATH, "Rejected")


@app.route('/request_approval', methods=['POST'])
def request_approval():
    """Create an approval request file"""
    data = request.json
    
    # Generate a unique ID for this request
    request_id = str(uuid.uuid4())
    filename = f"APPROVAL_{request_id}.md"
    filepath = os.path.join(PENDING_APPROVAL_DIR, filename)
    
    # Ensure the directory exists
    Path(PENDING_APPROVAL_DIR).mkdir(parents=True, exist_ok=True)
    
    # Create the approval request content
    content = f"""---
type: approval_request
id: {request_id}
action: {data.get('action', 'unknown')}
amount: {data.get('amount', 'N/A')}
recipient: {data.get('recipient', 'N/A')}
reason: {data.get('reason', 'N/A')}
created: {datetime.now().isoformat()}
expires: {(datetime.now() + timedelta(days=1)).isoformat()}
status: pending
---


## Request Details
- Action: {data.get('action', 'unknown')}
- Amount: {data.get('amount', 'N/A')}
- Recipient: {data.get('recipient', 'N/A')}
- Reason: {data.get('reason', 'N/A')}


## To Approve
Move this file to {APPROVED_DIR} folder.


## To Reject
Move this file to {REJECTED_DIR} folder.
"""
    
    # Write the approval request file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return jsonify({
        "success": True,
        "message": f"Approval request created: {filename}",
        "request_id": request_id,
        "filepath": filepath
    })


@app.route('/check_approval', methods=['POST'])
def check_approval():
    """Check if an approval request has been approved or rejected"""
    data = request.json
    request_id = data.get('request_id')
    
    # Look for the file in Approved or Rejected directories
    approved_file = os.path.join(APPROVED_DIR, f"APPROVAL_{request_id}.md")
    rejected_file = os.path.join(REJECTED_DIR, f"APPROVAL_{request_id}.md")
    
    if os.path.exists(approved_file):
        return jsonify({
            "status": "approved",
            "filepath": approved_file
        })
    elif os.path.exists(rejected_file):
        return jsonify({
            "status": "rejected",
            "filepath": rejected_file
        })
    else:
        return jsonify({
            "status": "pending",
            "message": "Approval still pending"
        })


@app.route('/approve_action', methods=['POST'])
def approve_action():
    """Approve an action by moving it to the approved directory"""
    data = request.json
    request_id = data.get('request_id')
    
    pending_file = os.path.join(PENDING_APPROVAL_DIR, f"APPROVAL_{request_id}.md")
    approved_file = os.path.join(APPROVED_DIR, f"APPROVAL_{request_id}.md")
    
    if os.path.exists(pending_file):
        Path(APPROVED_DIR).mkdir(parents=True, exist_ok=True)
        os.rename(pending_file, approved_file)
        return jsonify({
            "success": True,
            "message": f"Action approved: {request_id}",
            "status": "approved"
        })
    else:
        return jsonify({
            "success": False,
            "error": "Approval request not found"
        }), 404


@app.route('/reject_action', methods=['POST'])
def reject_action():
    """Reject an action by moving it to the rejected directory"""
    data = request.json
    request_id = data.get('request_id')
    
    pending_file = os.path.join(PENDING_APPROVAL_DIR, f"APPROVAL_{request_id}.md")
    rejected_file = os.path.join(REJECTED_DIR, f"APPROVAL_{request_id}.md")
    
    if os.path.exists(pending_file):
        Path(REJECTED_DIR).mkdir(parents=True, exist_ok=True)
        os.rename(pending_file, rejected_file)
        return jsonify({
            "success": True,
            "message": f"Action rejected: {request_id}",
            "status": "rejected"
        })
    else:
        return jsonify({
            "success": False,
            "error": "Approval request not found"
        }), 404


@app.route('/list_pending_approvals', methods=['GET'])
def list_pending_approvals():
    """List all pending approval requests"""
    pending_approvals = []

    if os.path.exists(PENDING_APPROVAL_DIR):
        for filename in os.listdir(PENDING_APPROVAL_DIR):
            if filename.startswith("APPROVAL_") and filename.endswith(".md"):
                filepath = os.path.join(PENDING_APPROVAL_DIR, filename)
                stat = os.stat(filepath)
                pending_approvals.append({
                    "filename": filename,
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "request_id": filename.replace("APPROVAL_", "").replace(".md", "")
                })
    
    return jsonify({
        "pending_approvals": pending_approvals,
        "count": len(pending_approvals)
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'approval-mcp',
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    # Ensure directories exist
    Path(PENDING_APPROVAL_DIR).mkdir(parents=True, exist_ok=True)
    Path(APPROVED_DIR).mkdir(parents=True, exist_ok=True)
    Path(REJECTED_DIR).mkdir(parents=True, exist_ok=True)
    
    app.run(host='localhost', port=8003, debug=False)