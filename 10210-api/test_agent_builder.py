"""
Test script for Agent Builder
"""
import asyncio
import httpx
import json

BASE_URL = "http://localhost:8100"

async def test_agent_builder():
    """Test agent builder endpoints"""
    print("🧪 Testing Agent Builder API...\n")
    
    async with httpx.AsyncClient() as client:
        # Test health check
        print("1. Testing health check...")
        try:
            resp = await client.get(f"{BASE_URL}/api/health")
            print(f"   ✅ Health check: {resp.json()}")
        except Exception as e:
            print(f"   ❌ Health check failed: {e}")
            return
        
        # Test triggers endpoint
        print("\n2. Testing triggers endpoint...")
        try:
            resp = await client.get(f"{BASE_URL}/api/triggers")
            triggers = resp.json()
            print(f"   ✅ Found {sum(len(v) for v in triggers.values())} triggers in {len(triggers)} categories")
            for category, items in list(triggers.items())[:2]:
                print(f"   - {category}: {len(items)} triggers")
        except Exception as e:
            print(f"   ❌ Triggers endpoint failed: {e}")
        
        # Test tools endpoint
        print("\n3. Testing tools endpoint...")
        try:
            resp = await client.get(f"{BASE_URL}/api/tools")
            tools = resp.json()
            print(f"   ✅ Found tools:")
            print(f"   - WAHA tools: {len(tools.get('waha', []))}")
            print(f"   - Built-in tools: {len(tools.get('builtin', []))}")
            print(f"   - MCP tools: {len(tools.get('mcp', []))}")
            print(f"   - Custom tools: {len(tools.get('custom', []))}")
        except Exception as e:
            print(f"   ❌ Tools endpoint failed: {e}")
        
        # Test agent creation
        print("\n4. Testing agent creation...")
        agent_data = {
            "name": "Test Customer Support Agent",
            "description": "Automated customer support assistant",
            "triggers": ["message", "group.v2.join"],
            "trigger_instructions": {
                "message": "Respond to customer queries professionally and helpfully",
                "group.v2.join": "Welcome new members to the group"
            },
            "additional_instructions": "Always be polite and professional",
            "tools": {
                "waha_tools": ["send_text", "send_image", "start_typing", "stop_typing"],
                "builtin_tools": ["google_search"],
                "mcp_tools": [],
                "custom_tools": []
            },
            "model": "gemini-2.0-flash",
            "temperature": 0.7,
            "whatsapp_session": "default"
        }
        
        try:
            resp = await client.post(
                f"{BASE_URL}/api/agents",
                json=agent_data
            )
            if resp.status_code == 200:
                agent = resp.json()
                print(f"   ✅ Agent created: {agent['name']} (ID: {agent['id']})")
                
                # Test agent lifecycle
                agent_id = agent['id']
                
                print(f"\n5. Testing agent lifecycle for {agent_id}...")
                
                # Start agent
                print("   - Starting agent...")
                resp = await client.post(f"{BASE_URL}/api/agents/{agent_id}/start")
                if resp.status_code == 200:
                    result = resp.json()
                    print(f"     ✅ Agent started on port {result.get('port')}")
                else:
                    print(f"     ❌ Failed to start: {resp.text}")
                
                # Get status
                await asyncio.sleep(2)
                resp = await client.get(f"{BASE_URL}/api/agents/{agent_id}/status")
                status = resp.json()
                print(f"   - Status: {status}")
                
                # Pause agent
                print("   - Pausing agent...")
                resp = await client.post(f"{BASE_URL}/api/agents/{agent_id}/pause")
                if resp.status_code == 200:
                    print("     ✅ Agent paused")
                
                # Resume agent
                await asyncio.sleep(1)
                print("   - Resuming agent...")
                resp = await client.post(f"{BASE_URL}/api/agents/{agent_id}/resume")
                if resp.status_code == 200:
                    print("     ✅ Agent resumed")
                
                # Stop agent
                await asyncio.sleep(1)
                print("   - Stopping agent...")
                resp = await client.post(f"{BASE_URL}/api/agents/{agent_id}/stop")
                if resp.status_code == 200:
                    print("     ✅ Agent stopped")
                
                # Delete agent
                print("   - Deleting agent...")
                resp = await client.delete(f"{BASE_URL}/api/agents/{agent_id}")
                if resp.status_code == 200:
                    print("     ✅ Agent deleted")
                
            else:
                print(f"   ❌ Failed to create agent: {resp.text}")
        except Exception as e:
            print(f"   ❌ Agent operations failed: {e}")
        
        print("\n✅ Agent Builder API tests completed!")

if __name__ == "__main__":
    print("="*50)
    print("WhatsApp Agent Builder Test Suite")
    print("="*50)
    print("\nMake sure the Agent Builder is running on port 8100")
    print("Start it with: python start_agent_builder.py\n")
    
    asyncio.run(test_agent_builder())