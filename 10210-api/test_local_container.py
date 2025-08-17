#!/usr/bin/env python3
"""
Local testing for container management
Simulates the DO Function locally
"""

import subprocess
import random
import time
import json
import sqlite3
from datetime import datetime

# Local configuration
LOCAL_DB_PATH = './data/local_infrastructure.db'

def find_available_port(start_port: int, end_port: int) -> int:
    """Find an available port locally"""
    import socket
    for _ in range(100):
        port = random.randint(start_port, end_port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        if result != 0:  # Port is available
            return port
    raise Exception(f"No available ports in range {start_port}-{end_port}")

def create_user_container_local(user_id: str, plan_type: str = 'free'):
    """Create a container locally for testing"""
    
    print(f"🚀 Creating container for user {user_id} ({plan_type} plan)")
    
    # Allocate ports
    api_port = find_available_port(40000, 41000)  # Smaller range for local
    warmer_port = find_available_port(20000, 21000)
    campaign_port = find_available_port(30000, 31000)
    
    container_name = f"cuwapp-user-{user_id}"
    
    print(f"📍 Allocated ports:")
    print(f"   API: {api_port}")
    print(f"   Warmer: {warmer_port}")
    print(f"   Campaign: {campaign_port}")
    
    # Build Docker command
    docker_cmd = [
        'docker', 'run', '-d',
        '--name', container_name,
        '-p', f'{api_port}:{api_port}',
        '-p', f'{warmer_port}:{warmer_port}',
        '-p', f'{campaign_port}:{campaign_port}',
        '-e', f'USER_ID={user_id}',
        '-e', f'PLAN_TYPE={plan_type}',
        '-e', f'API_PORT={api_port}',
        '-e', f'WARMER_PORT={warmer_port}',
        '-e', f'CAMPAIGN_PORT={campaign_port}',
        '-v', f'{os.path.abspath("./data")}:/app/data',
        '--restart', 'unless-stopped',
        'cuwapp/multi-service:latest'
    ]
    
    print(f"🐳 Running Docker command...")
    
    try:
        result = subprocess.run(docker_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Docker error: {result.stderr}")
            return None
        
        container_id = result.stdout.strip()
        print(f"✅ Container created: {container_id[:12]}")
        
        # Wait for container to be ready
        print("⏳ Waiting for services to start...")
        time.sleep(5)
        
        # Check container status
        status_cmd = ['docker', 'ps', '--filter', f'name={container_name}', '--format', '{{.Status}}']
        status_result = subprocess.run(status_cmd, capture_output=True, text=True)
        status = status_result.stdout.strip()
        
        if "Up" in status:
            print(f"✅ Container is running: {status}")
        else:
            print(f"⚠️ Container status: {status}")
        
        # Save to local database
        save_to_local_db(user_id, {
            'container_id': container_id,
            'container_name': container_name,
            'api_port': api_port,
            'warmer_port': warmer_port,
            'campaign_port': campaign_port,
            'plan_type': plan_type,
            'status': 'active'
        })
        
        # Test the services
        print("\n🧪 Testing services...")
        test_services(api_port, warmer_port, campaign_port)
        
        return {
            'success': True,
            'container_id': container_id,
            'container_name': container_name,
            'api_url': f"http://localhost:{api_port}",
            'warmer_url': f"http://localhost:{warmer_port}",
            'campaign_url': f"http://localhost:{campaign_port}",
            'status': 'active'
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_services(api_port, warmer_port, campaign_port):
    """Test if services are responding"""
    import requests
    
    services = [
        ('API', f"http://localhost:{api_port}/health"),
        ('Warmer', f"http://localhost:{warmer_port}/health"),
        ('Campaign', f"http://localhost:{campaign_port}/health")
    ]
    
    for name, url in services:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"   ✅ {name} service: OK ({url})")
            else:
                print(f"   ⚠️ {name} service: Status {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"   ❌ {name} service: Not responding ({e})")

def save_to_local_db(user_id, data):
    """Save to local SQLite database"""
    import os
    os.makedirs(os.path.dirname(LOCAL_DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(LOCAL_DB_PATH)
    cursor = conn.cursor()
    
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        INSERT OR REPLACE INTO user_infrastructure 
        (user_id, container_id, container_name, api_port, warmer_port, campaign_port, plan_type, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        data['container_id'],
        data['container_name'],
        data['api_port'],
        data['warmer_port'],
        data['campaign_port'],
        data['plan_type'],
        data['status']
    ))
    
    conn.commit()
    conn.close()
    print(f"💾 Saved to local database")

def stop_user_container_local(user_id: str):
    """Stop a user's container locally"""
    container_name = f"cuwapp-user-{user_id}"
    print(f"🛑 Stopping container {container_name}...")
    
    result = subprocess.run(['docker', 'stop', container_name], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✅ Container stopped")
        return True
    else:
        print(f"❌ Error: {result.stderr}")
        return False

def delete_user_container_local(user_id: str):
    """Delete a user's container locally"""
    container_name = f"cuwapp-user-{user_id}"
    print(f"🗑️ Deleting container {container_name}...")
    
    subprocess.run(['docker', 'stop', container_name], capture_output=True, text=True)
    time.sleep(2)
    result = subprocess.run(['docker', 'rm', container_name], capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ Container deleted")
        return True
    else:
        print(f"❌ Error: {result.stderr}")
        return False

def list_user_containers():
    """List all user containers"""
    print("\n📋 User Containers:")
    result = subprocess.run(
        ['docker', 'ps', '-a', '--filter', 'name=cuwapp-user-', '--format', 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'],
        capture_output=True, text=True
    )
    print(result.stdout)

if __name__ == "__main__":
    import sys
    import os
    
    print("🧪 Local Container Testing")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python test_local_container.py create <user_id> [plan_type]")
        print("  python test_local_container.py stop <user_id>")
        print("  python test_local_container.py delete <user_id>")
        print("  python test_local_container.py list")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == 'create':
        user_id = sys.argv[2] if len(sys.argv) > 2 else 'test-user-1'
        plan_type = sys.argv[3] if len(sys.argv) > 3 else 'free'
        result = create_user_container_local(user_id, plan_type)
        if result:
            print("\n🎉 Container ready!")
            print(json.dumps(result, indent=2))
    
    elif action == 'stop':
        user_id = sys.argv[2] if len(sys.argv) > 2 else 'test-user-1'
        stop_user_container_local(user_id)
    
    elif action == 'delete':
        user_id = sys.argv[2] if len(sys.argv) > 2 else 'test-user-1'
        delete_user_container_local(user_id)
    
    elif action == 'list':
        list_user_containers()
    
    else:
        print(f"Unknown action: {action}")