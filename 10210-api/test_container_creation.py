#!/usr/bin/env python3
"""
Test script to simulate container creation for users
Shows how the system would allocate ports and create containers
"""

import docker
import sqlite3
import os
import json
from datetime import datetime

def test_container_creation():
    """Simulate what would happen when a user signs up"""
    
    # Configuration
    user_id = "test_user_demo_001"
    plan_type = "free"
    base_port = 40000  # Starting port for user containers
    
    print(f"🚀 Simulating container creation for user: {user_id}")
    print(f"📋 Plan type: {plan_type}")
    print("-" * 50)
    
    # Calculate ports for this user's services
    app_port = base_port
    warmer_port = base_port + 1
    campaign_port = base_port + 2
    
    print(f"\n📍 Port allocation:")
    print(f"  - API Service:      port {app_port}")
    print(f"  - Warmer Service:   port {warmer_port}")
    print(f"  - Campaign Service: port {campaign_port}")
    
    container_name = f"cuwhapp-user-{user_id[:8]}-{app_port}"
    
    # Show what Docker command would be executed
    docker_command = f"""
docker run -d \\
  --name {container_name} \\
  -p {app_port}:8000 \\
  -p {warmer_port}:20000 \\
  -p {campaign_port}:30000 \\
  -e USER_ID={user_id} \\
  -e PLAN_TYPE={plan_type} \\
  -e API_PORT=8000 \\
  -e WARMER_PORT=20000 \\
  -e CAMPAIGN_PORT=30000 \\
  --network cuwhapp-network \\
  cuwhapp/multi-service:latest
    """
    
    print(f"\n🐳 Docker command that would be executed:")
    print(docker_command)
    
    # Show the URLs that would be assigned
    server_ip = "174.138.55.42"  # Production server IP
    
    urls = {
        'api_url': f"http://{server_ip}:{app_port}",
        'warmer_url': f"http://{server_ip}:{warmer_port}",
        'campaign_url': f"http://{server_ip}:{campaign_port}",
        'container_name': container_name,
        'status': 'simulated'
    }
    
    print(f"\n🌐 User's dedicated URLs:")
    print(f"  - API URL:      {urls['api_url']}")
    print(f"  - Warmer URL:   {urls['warmer_url']}")
    print(f"  - Campaign URL: {urls['campaign_url']}")
    
    # Show database record that would be created
    print(f"\n💾 Database record (user_infrastructure table):")
    db_record = {
        'user_id': user_id,
        'container_name': container_name,
        'api_url': urls['api_url'],
        'warmer_url': urls['warmer_url'],
        'campaign_url': urls['campaign_url'],
        'app_port': app_port,
        'plan_type': plan_type,
        'status': 'active',
        'created_at': datetime.now().isoformat()
    }
    print(json.dumps(db_record, indent=2))
    
    # Check if Docker is available for local testing
    try:
        client = docker.from_env()
        print(f"\n✅ Docker is available locally")
        
        # Check if the multi-service image exists
        try:
            client.images.get("cuwhapp/multi-service:latest")
            print("✅ Multi-service image found")
        except docker.errors.ImageNotFound:
            print("⚠️  Multi-service image not found locally")
            print("   In production, this image would be pulled from the registry")
            
    except Exception as e:
        print(f"\n⚠️  Docker not available for local testing: {e}")
        print("   In production, the DO Function would handle container creation")
    
    print("\n" + "=" * 50)
    print("📌 Summary:")
    print(f"When user {user_id} signs up:")
    print("1. They get assigned 3 consecutive ports")
    print("2. A Docker container is created with all 3 services")
    print("3. The container runs API, Warmer, and Campaign services")
    print("4. URLs are saved to the database")
    print("5. Dashboard connects directly to user's container")
    print("=" * 50)

if __name__ == "__main__":
    test_container_creation()