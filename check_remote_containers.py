#!/usr/bin/env python3
"""
Check Docker containers on remote Digital Ocean server
Using Docker API endpoint
"""

import requests
import json
from datetime import datetime

# Docker API configuration from do-waha-orchestrator
DOCKER_HOST = "174.138.55.42"
DOCKER_PORT = 2375
DOCKER_API = f"http://{DOCKER_HOST}:{DOCKER_PORT}"

def check_docker_api():
    """Check if Docker API is accessible"""
    try:
        response = requests.get(f"{DOCKER_API}/version", timeout=5)
        if response.status_code == 200:
            version = response.json()
            print(f"✅ Docker API is accessible")
            print(f"   Docker version: {version.get('Version', 'Unknown')}")
            print(f"   API version: {version.get('ApiVersion', 'Unknown')}")
            return True
        else:
            print(f"❌ Docker API returned status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to Docker API at {DOCKER_API}")
        print("   Make sure Docker is configured with -H tcp://0.0.0.0:2375")
        return False
    except Exception as e:
        print(f"❌ Error checking Docker API: {e}")
        return False

def list_all_containers():
    """List all Docker containers"""
    try:
        response = requests.get(f"{DOCKER_API}/containers/json", params={"all": True})
        if response.status_code == 200:
            containers = response.json()
            return containers
        else:
            print(f"Error listing containers: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error: {e}")
        return []

def list_waha_containers():
    """List WAHA containers specifically"""
    try:
        # Filter for WAHA containers
        filters = {"ancestor": ["devlikeapro/waha-plus"]}
        response = requests.get(
            f"{DOCKER_API}/containers/json",
            params={"all": True, "filters": json.dumps(filters)}
        )
        if response.status_code == 200:
            return response.json()
        else:
            return []
    except Exception as e:
        print(f"Error listing WAHA containers: {e}")
        return []

def format_container_info(container):
    """Format container information for display"""
    name = container['Names'][0].lstrip('/') if container['Names'] else 'Unknown'
    status = container['Status']
    state = container['State']
    image = container['Image']
    
    # Extract ports
    ports = []
    if container.get('Ports'):
        for port in container['Ports']:
            if port.get('PublicPort'):
                ports.append(f"{port['PublicPort']}->{port['PrivatePort']}/{port['Type']}")
    
    return {
        'name': name,
        'status': status,
        'state': state,
        'image': image,
        'ports': ', '.join(ports) if ports else 'No ports',
        'id': container['Id'][:12]
    }

def main():
    print("=" * 70)
    print(f"🐳 Docker Container Status on {DOCKER_HOST}")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    
    # Check API connectivity
    if not check_docker_api():
        print("\n⚠️  Cannot connect to Docker API")
        print("   The Docker daemon might need to be configured to listen on TCP")
        print("   On the server, check if Docker is running with:")
        print("   docker run -d -p 2375:2375 -v /var/run/docker.sock:/var/run/docker.sock alpine/socat tcp-listen:2375,fork,reuseaddr unix-connect:/var/run/docker.sock")
        return
    
    print()
    
    # Get all containers
    all_containers = list_all_containers()
    
    if not all_containers:
        print("No containers found or unable to retrieve container list")
        return
    
    # Summary
    running = [c for c in all_containers if c['State'] == 'running']
    stopped = [c for c in all_containers if c['State'] != 'running']
    
    print(f"📊 Container Summary:")
    print(f"   Total containers: {len(all_containers)}")
    print(f"   Running: {len(running)}")
    print(f"   Stopped: {len(stopped)}")
    print()
    
    # List all containers
    print("📦 All Containers:")
    print("-" * 70)
    print(f"{'Name':<30} {'Status':<15} {'Ports':<25}")
    print("-" * 70)
    
    for container in all_containers:
        info = format_container_info(container)
        status_icon = "🟢" if container['State'] == 'running' else "🔴"
        print(f"{status_icon} {info['name']:<28} {info['state']:<15} {info['ports']:<25}")
    
    print()
    
    # WAHA containers specifically
    waha_containers = list_waha_containers()
    if waha_containers:
        print("📱 WAHA Containers:")
        print("-" * 70)
        for container in waha_containers:
            info = format_container_info(container)
            print(f"   {info['name']}")
            print(f"   Status: {info['status']}")
            print(f"   Ports: {info['ports']}")
            print(f"   ID: {info['id']}")
            print()
    else:
        print("📱 No WAHA containers found")
    
    # Show how to connect
    print()
    print("=" * 70)
    print("📌 Access Information:")
    print(f"   Server IP: {DOCKER_HOST}")
    print(f"   Docker API: http://{DOCKER_HOST}:{DOCKER_PORT}")
    print()
    print("   To SSH into the server:")
    print(f"   ssh root@{DOCKER_HOST}")
    print("   Password: $Oden3474")
    print("=" * 70)

if __name__ == "__main__":
    main()