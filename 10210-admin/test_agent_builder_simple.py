"""
Simple test to check if agent builder is working
"""
import httpx
import asyncio

async def test():
    """Test basic endpoints"""
    try:
        async with httpx.AsyncClient() as client:
            # Test health endpoint
            resp = await client.get("http://localhost:8100/api/health")
            print("Health check:", resp.status_code, resp.json())
            
            # Test triggers endpoint
            resp = await client.get("http://localhost:8100/api/triggers")
            print("Triggers:", resp.status_code)
            
            # Test tools endpoint  
            resp = await client.get("http://localhost:8100/api/tools")
            print("Tools:", resp.status_code)
            
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(test())