#!/usr/bin/env python3
"""
Test creating a WAHA container on remote Docker
"""

import requests
import json
import time

DOCKER_HOST = "174.138.55.42"
DOCKER_PORT = 2375
DOCKER_API = f"http://{DOCKER_HOST}:{DOCKER_PORT}"

def create_test_waha():
    """Create a test WAHA container"""
    print(f"🚀 Creating test WAHA container on {DOCKER_HOST}...")
    
    container_name = "waha-test-instance"
    port = 4500
    
    # Container configuration
    config = {
        "Image": "devlikeapro/waha-plus:latest",
        "name": container_name,
        "ExposedPorts": {"3000/tcp": {}},
        "HostConfig": {
            "PortBindings": {
                "3000/tcp": [{"HostPort": str(port)}]
            },
            "RestartPolicy": {"Name": "unless-stopped"}
        },
        "Env": [
            "WHATSAPP_SESSIONS_LIMIT=1",
            "WHATSAPP_RESTART_ALL_SESSIONS=true"
        ]
    }
    
    # Create container
    response = requests.post(
        f"{DOCKER_API}/containers/create",
        params={"name": container_name},
        json=config
    )
    
    if response.status_code == 201:
        container_id = response.json()["Id"]
        print(f"✅ Container created: {container_id[:12]}")
        
        # Start container
        start_response = requests.post(
            f"{DOCKER_API}/containers/{container_id}/start"
        )
        
        if start_response.status_code == 204:
            print(f"✅ Container started successfully")
            print(f"📱 WAHA instance available at: http://{DOCKER_HOST}:{port}")
            
            # Wait a moment for it to start
            print("⏳ Waiting for WAHA to initialize...")
            time.sleep(5)
            
            # Test WAHA API
            try:
                waha_response = requests.get(f"http://{DOCKER_HOST}:{port}/api/sessions", timeout=5)
                if waha_response.status_code == 200:
                    print(f"✅ WAHA API is responding!")
                else:
                    print(f"⚠️  WAHA returned status: {waha_response.status_code}")
            except Exception as e:
                print(f"⚠️  Could not reach WAHA API: {e}")
            
            return True
        else:
            print(f"❌ Failed to start container: {start_response.text}")
            return False
    else:
        if "already in use" in response.text:
            print("⚠️  Container already exists. Checking status...")
            # List containers
            list_response = requests.get(f"{DOCKER_API}/containers/json?all=true")
            containers = list_response.json()
            for c in containers:
                if container_name in str(c.get('Names', [])):
                    print(f"Found existing container: {c['Names'][0]} - {c['State']}")
                    if c['State'] == 'running':
                        print(f"✅ Container is already running at http://{DOCKER_HOST}:{port}")
                    break
        else:
            print(f"❌ Failed to create container: {response.text}")
        return False

def list_all_containers():
    """List all containers"""
    print("\n📦 Current containers:")
    response = requests.get(f"{DOCKER_API}/containers/json?all=true")
    if response.status_code == 200:
        containers = response.json()
        for c in containers:
            name = c['Names'][0].lstrip('/') if c['Names'] else 'Unknown'
            state = c['State']
            print(f"  {'🟢' if state == 'running' else '🔴'} {name} - {state}")
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Remote Docker Setup")
    print("=" * 60)
    
    # Create test WAHA
    create_test_waha()
    
    # List all containers
    list_all_containers()
    
    print("=" * 60)
    print("Test complete!")
    print(f"You can now access:")
    print(f"  WAHA: http://{DOCKER_HOST}:4500")
    print("=" * 60)