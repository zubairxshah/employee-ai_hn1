"""
Filesystem MCP Server
Provides file system operations for Claude Code
"""

import json
import os
import sys
from pathlib import Path
from flask import Flask, request, jsonify
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import security modules
from security_config import get_security_config
from secure_action_executor import get_secure_executor


app = Flask(__name__)

VAULT_PATH = os.getenv("VAULT_PATH", r"D:\prompteng\AI_Employee_Vault")
SECURITY_CONFIG = get_security_config()
SECURE_EXECUTOR = get_secure_executor()


@app.route('/capabilities', methods=['GET'])
def get_capabilities():
    """Return the capabilities of this MCP server"""
    capabilities = {
        "name": "filesystem-mcp",
        "version": "1.0.0",
        "description": "File system operations for AI Employee",
        "operations": [
            {
                "name": "read_file",
                "description": "Read content of a file",
                "parameters": {
                    "path": {"type": "string", "description": "Path to the file"}
                }
            },
            {
                "name": "write_file",
                "description": "Write content to a file",
                "parameters": {
                    "path": {"type": "string", "description": "Path to the file"},
                    "content": {"type": "string", "description": "Content to write"}
                }
            },
            {
                "name": "list_files",
                "description": "List files in a directory",
                "parameters": {
                    "path": {"type": "string", "description": "Directory path to list"}
                }
            },
            {
                "name": "move_file",
                "description": "Move a file from one location to another",
                "parameters": {
                    "source": {"type": "string", "description": "Source file path"},
                    "destination": {"type": "string", "description": "Destination file path"}
                }
            }
        ]
    }
    return jsonify(capabilities)


@app.route('/read_file', methods=['POST'])
def read_file():
    """Read content of a file"""
    data = request.json
    file_path = data.get('path', '')
    
    # Ensure the path is within the vault
    full_path = os.path.abspath(os.path.join(VAULT_PATH, file_path))
    vault_path = os.path.abspath(VAULT_PATH)
    
    if not full_path.startswith(vault_path):
        SECURITY_CONFIG.logger.warning(f"Access attempt to path outside vault: {full_path}")
        return jsonify({"error": "Access denied: path outside vault"}), 403
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Log the read operation
        SECURITY_CONFIG.log_action(
            action_type="file_read",
            actor="claude_code",
            target=file_path,
            parameters={"path": file_path},
            approval_status="auto_approved",
            result="success"
        )
        
        return jsonify({"content": content, "success": True})
    except Exception as e:
        SECURITY_CONFIG.logger.error(f"Error reading file {full_path}: {str(e)}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/write_file', methods=['POST'])
def write_file():
    """Write content to a file"""
    data = request.json
    file_path = data.get('path', '')
    content = data.get('content', '')
    
    # Ensure the path is within the vault
    full_path = os.path.abspath(os.path.join(VAULT_PATH, file_path))
    vault_path = os.path.abspath(VAULT_PATH)
    
    if not full_path.startswith(vault_path):
        SECURITY_CONFIG.logger.warning(f"Attempt to write outside vault: {full_path}")
        return jsonify({"error": "Access denied: path outside vault"}), 403
    
    try:
        # Sanitize inputs
        sanitized_path = SECURITY_CONFIG.sanitize_input(file_path)
        sanitized_content = SECURITY_CONFIG.sanitize_input(content)
        
        # Create directory if it doesn't exist
        Path(full_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(sanitized_content)
        
        # Log the write operation
        SECURITY_CONFIG.log_action(
            action_type="file_write",
            actor="claude_code",
            target=file_path,
            parameters={"path": file_path, "content_length": len(content)},
            approval_status="auto_approved",
            result="success"
        )
        
        return jsonify({"success": True, "message": f"File written: {file_path}"})
    except Exception as e:
        SECURITY_CONFIG.logger.error(f"Error writing file {full_path}: {str(e)}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/list_files', methods=['POST'])
def list_files():
    """List files in a directory"""
    data = request.json
    dir_path = data.get('path', '.')
    
    # Ensure the path is within the vault
    full_path = os.path.abspath(os.path.join(VAULT_PATH, dir_path))
    vault_path = os.path.abspath(VAULT_PATH)
    
    if not full_path.startswith(vault_path):
        SECURITY_CONFIG.logger.warning(f"Attempt to list directory outside vault: {full_path}")
        return jsonify({"error": "Access denied: path outside vault"}), 403
    
    try:
        files = []
        for item in os.listdir(full_path):
            item_path = os.path.join(full_path, item)
            is_dir = os.path.isdir(item_path)
            size = 0 if is_dir else os.path.getsize(item_path)
            files.append({
                "name": item,
                "type": "directory" if is_dir else "file",
                "size": size
            })
        
        # Log the list operation
        SECURITY_CONFIG.log_action(
            action_type="file_list",
            actor="claude_code",
            target=dir_path,
            parameters={"path": dir_path, "file_count": len(files)},
            approval_status="auto_approved",
            result="success"
        )
        
        return jsonify({"files": files, "success": True})
    except Exception as e:
        SECURITY_CONFIG.logger.error(f"Error listing directory {full_path}: {str(e)}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/move_file', methods=['POST'])
def move_file():
    """Move a file from one location to another"""
    data = request.json
    source = data.get('source', '')
    destination = data.get('destination', '')
    
    # Ensure both paths are within the vault
    source_full = os.path.abspath(os.path.join(VAULT_PATH, source))
    dest_full = os.path.abspath(os.path.join(VAULT_PATH, destination))
    vault_path = os.path.abspath(VAULT_PATH)
    
    if not source_full.startswith(vault_path) or not dest_full.startswith(vault_path):
        SECURITY_CONFIG.logger.warning(f"Attempt to move file outside vault: {source_full} -> {dest_full}")
        return jsonify({"error": "Access denied: path outside vault"}), 403
    
    # Use the secure executor for file operations
    result = SECURE_EXECUTOR.file_operation("move", source, destination)
    
    if result["success"]:
        return jsonify({
            "success": True, 
            "message": f"File moved from {source} to {destination}",
            "source": source,
            "destination": destination
        })
    else:
        return jsonify({"error": f"File move failed: {result['status']}", "success": False}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    from datetime import datetime
    return jsonify({
        'status': 'healthy',
        'service': 'filesystem-mcp',
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    app.run(host='localhost', port=8000, debug=False)