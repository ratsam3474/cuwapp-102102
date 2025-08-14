"""
Debug version of agent builder starter without reloader
"""
import uvicorn
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("Starting Agent Builder in debug mode...")
    try:
        # Run without reload to see errors
        uvicorn.run(
            "agent_builder.main:app",
            host="0.0.0.0",
            port=8100,
            reload=False,  # Disable reload to see errors
            log_level="debug"  # More verbose logging
        )
    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()