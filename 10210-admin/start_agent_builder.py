"""
Start the Agent Builder Service
This runs independently on port 8100
"""
import os
import sys
import subprocess

def main():
    print("Starting WhatsApp Agent Builder Service...")
    print("=" * 50)
    print("Service will run on: http://localhost:8100")
    print("=" * 50)
    
    # Change to agent_builder directory
    agent_builder_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_builder")
    
    # Start the service
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "agent_builder.main:app",
            "--host", "0.0.0.0",
            "--port", "8100",
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n👋 Shutting down Agent Builder Service...")

if __name__ == "__main__":
    main()