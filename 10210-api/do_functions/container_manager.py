"""
DigitalOcean Function for Docker Container Management
This runs as a serverless function on DO to manage Docker containers
Since containers can't create containers, we use DO Functions
"""

import os
import json
import subprocess
import random
import time
import paramiko
import sqlite3
from typing import Dict, Optional
from datetime import datetime, timedelta

# Configuration from environment variables
DO_SERVER_IP = os.environ.get('DO_SERVER_IP', '174.138.55.42')
DO_SSH_KEY = os.environ.get('DO_SSH_KEY', '/tmp/do_key')
DO_SSH_USER = os.environ.get('DO_SSH_USER', 'root')
DB_PATH = os.environ.get('DB_PATH', '/tmp/infrastructure.db')

def main(args):
    """
    Main function entry point for DO Function
    Args expected:
    - action: create, stop, restart, delete
    - user_id: User ID
    - plan_type: free, hobby, pro, enterprise
    """
    
    action = args.get('action', 'create')
    user_id = args.get('user_id')
    plan_type = args.get('plan_type', 'free')
    
    if not user_id:
        return {
            "statusCode": 400,
            "body": {"error": "user_id is required"}
        }
    
    try:
        if action == 'create':
            result = create_user_container(user_id, plan_type)
        elif action == 'stop':
            result = stop_user_container(user_id)
        elif action == 'restart':
            result = restart_user_container(user_id)
        elif action == 'delete':
            result = delete_user_container(user_id)
        else:
            return {
                "statusCode": 400,
                "body": {"error": f"Unknown action: {action}"}
            }
        
        return {
            "statusCode": 200,
            "body": result
        }
        
    except Exception as e:
        return {
            "statusCode": 500,
            "body": {"error": str(e)}
        }

def get_ssh_client():
    """Create SSH client to connect to DO server"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # Use SSH key if available, otherwise use password
    if os.path.exists(DO_SSH_KEY):
        ssh.connect(DO_SERVER_IP, username=DO_SSH_USER, key_filename=DO_SSH_KEY)
    else:
        # Fallback to password (set in env)
        ssh.connect(DO_SERVER_IP, username=DO_SSH_USER, password=os.environ.get('DO_SSH_PASS'))
    
    return ssh

def find_available_port(ssh, start_port: int, end_port: int) -> int:
    """Find an available port in the given range"""
    for _ in range(100):  # Try 100 times
        port = random.randint(start_port, end_port)
        
        # Check if port is in use
        stdin, stdout, stderr = ssh.exec_command(f"netstat -tuln | grep :{port}")
        if not stdout.read():
            return port
    
    raise Exception(f"No available ports in range {start_port}-{end_port}")

def create_user_container(user_id: str, plan_type: str) -> Dict:
    """Create a new Docker container for the user"""
    
    ssh = get_ssh_client()
    
    try:
        # Allocate ports for the services
        # Each range supports 10,000 users
        api_port = find_available_port(ssh, 40000, 50000)      # 10,000 possible ports
        warmer_port = find_available_port(ssh, 20000, 30000)   # 10,000 possible ports
        campaign_port = find_available_port(ssh, 30000, 40000) # 10,000 possible ports
        
        container_name = f"cuwapp-user-{user_id}"
        
        # Build Docker run command
        # Internal ports = External ports (same port inside and outside)
        docker_cmd = f"""
        docker run -d \\
            --name {container_name} \\
            -p {api_port}:{api_port} \\
            -p {warmer_port}:{warmer_port} \\
            -p {campaign_port}:{campaign_port} \\
            -e USER_ID={user_id} \\
            -e PLAN_TYPE={plan_type} \\
            -e API_PORT={api_port} \\
            -e WARMER_PORT={warmer_port} \\
            -e CAMPAIGN_PORT={campaign_port} \\
            -v /root/102102/data:/app/data \\
            --restart unless-stopped \\
            cuwapp/multi-service:latest
        """
        
        # Execute Docker command
        stdin, stdout, stderr = ssh.exec_command(docker_cmd)
        error = stderr.read().decode()
        
        if error and "Error" in error:
            raise Exception(f"Docker error: {error}")
        
        container_id = stdout.read().decode().strip()
        
        # Wait for container to be ready
        time.sleep(3)
        
        # Verify container is running
        stdin, stdout, stderr = ssh.exec_command(f"docker ps --filter name={container_name} --format '{{{{.Status}}}}'")
        status = stdout.read().decode().strip()
        
        if "Up" not in status:
            raise Exception(f"Container failed to start: {status}")
        
        # Save to database
        save_infrastructure(user_id, {
            'container_id': container_id,
            'container_name': container_name,
            'api_port': api_port,
            'warmer_port': warmer_port,
            'campaign_port': campaign_port,
            'plan_type': plan_type,
            'status': 'active'
        })
        
        # Build URLs
        base_url = f"http://{DO_SERVER_IP}"
        
        return {
            'success': True,
            'container_id': container_id,
            'container_name': container_name,
            'api_url': f"{base_url}:{api_port}",
            'warmer_url': f"{base_url}:{warmer_port}",
            'campaign_url': f"{base_url}:{campaign_port}",
            'status': 'active'
        }
        
    finally:
        ssh.close()

def stop_user_container(user_id: str) -> Dict:
    """Stop a user's container"""
    
    ssh = get_ssh_client()
    
    try:
        container_name = f"cuwapp-user-{user_id}"
        
        # Stop container
        stdin, stdout, stderr = ssh.exec_command(f"docker stop {container_name}")
        result = stdout.read().decode().strip()
        
        # Update database
        update_infrastructure_status(user_id, 'stopped')
        
        return {
            'success': True,
            'message': f"Container {container_name} stopped",
            'status': 'stopped'
        }
        
    finally:
        ssh.close()

def restart_user_container(user_id: str) -> Dict:
    """Restart a user's container"""
    
    ssh = get_ssh_client()
    
    try:
        container_name = f"cuwapp-user-{user_id}"
        
        # Check if container exists
        stdin, stdout, stderr = ssh.exec_command(f"docker ps -a --filter name={container_name} --format '{{{{.Names}}}}'")
        existing = stdout.read().decode().strip()
        
        if existing:
            # Container exists, just restart it
            stdin, stdout, stderr = ssh.exec_command(f"docker restart {container_name}")
            
            # Update database
            update_infrastructure_status(user_id, 'active')
            
            # Get infrastructure details from DB
            infra = get_infrastructure(user_id)
            
            base_url = f"http://{DO_SERVER_IP}"
            
            return {
                'success': True,
                'message': f"Container {container_name} restarted",
                'api_url': f"{base_url}:{infra['api_port']}",
                'warmer_url': f"{base_url}:{infra['warmer_port']}",
                'campaign_url': f"{base_url}:{infra['campaign_port']}",
                'status': 'active'
            }
        else:
            # Container doesn't exist, create new one
            return create_user_container(user_id, 'free')
        
    finally:
        ssh.close()

def delete_user_container(user_id: str) -> Dict:
    """Delete a user's container"""
    
    ssh = get_ssh_client()
    
    try:
        container_name = f"cuwapp-user-{user_id}"
        
        # Stop and remove container
        ssh.exec_command(f"docker stop {container_name}")
        time.sleep(2)
        stdin, stdout, stderr = ssh.exec_command(f"docker rm {container_name}")
        
        # Update database
        update_infrastructure_status(user_id, 'deleted')
        
        return {
            'success': True,
            'message': f"Container {container_name} deleted",
            'status': 'deleted'
        }
        
    finally:
        ssh.close()

def save_infrastructure(user_id: str, data: Dict):
    """Save infrastructure details to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_infrastructure (
            user_id TEXT PRIMARY KEY,
            container_id TEXT,
            container_name TEXT,
            api_port INTEGER,
            warmer_port INTEGER,
            campaign_port INTEGER,
            plan_type TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert or update
    cursor.execute("""
        INSERT OR REPLACE INTO user_infrastructure 
        (user_id, container_id, container_name, api_port, warmer_port, campaign_port, plan_type, status, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        data['container_id'],
        data['container_name'],
        data['api_port'],
        data['warmer_port'],
        data['campaign_port'],
        data['plan_type'],
        data['status'],
        datetime.utcnow()
    ))
    
    conn.commit()
    conn.close()

def get_infrastructure(user_id: str) -> Optional[Dict]:
    """Get infrastructure details from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT container_id, container_name, api_port, warmer_port, campaign_port, plan_type, status
        FROM user_infrastructure
        WHERE user_id = ?
    """, (user_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'container_id': row[0],
            'container_name': row[1],
            'api_port': row[2],
            'warmer_port': row[3],
            'campaign_port': row[4],
            'plan_type': row[5],
            'status': row[6]
        }
    return None

def update_infrastructure_status(user_id: str, status: str):
    """Update infrastructure status in database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE user_infrastructure
        SET status = ?, updated_at = ?
        WHERE user_id = ?
    """, (status, datetime.utcnow(), user_id))
    
    conn.commit()
    conn.close()

# For local testing
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_args = {
            'action': sys.argv[1],
            'user_id': sys.argv[2] if len(sys.argv) > 2 else 'test-user',
            'plan_type': sys.argv[3] if len(sys.argv) > 3 else 'free'
        }
        result = main(test_args)
        print(json.dumps(result, indent=2))