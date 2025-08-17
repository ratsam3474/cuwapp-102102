#!/usr/bin/env python3
"""
WhatsApp Agent Startup Script
Manages the application lifecycle
"""

import os
import sys
import time
import subprocess
import signal
import requests
import webbrowser
from pathlib import Path

# Get URLs from environment
API_GATEWAY_URL = os.getenv('API_GATEWAY_URL', 'http://34.173.85.56:8000')
WAHA_BASE_URL = os.getenv('WAHA_BASE_URL', 'http://34.133.143.67:4500')
WAHA_VM_IP = os.getenv('WAHA_VM_EXTERNAL_IP', '34.133.143.67')

# Process tracking
main_process = None

def print_banner():
    """Display startup banner"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║                    WhatsApp Agent v1.0                      ║
║               Professional Management Dashboard              ║
║                                                              ║
║  Features:                                                   ║
║  • Session Management    • Contact Management               ║
║  • Chat Interface       • Group Management                  ║
║  • File Sharing         • Message Broadcasting              ║
║  • Real-time Updates    • Professional UI                   ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_python_version():
    """Check if Python version is 3.8+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python 3.8+ required. You have {version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")
    return True

def check_requirements():
    """Check if all required packages are installed"""
    required_packages = [
        'fastapi',
        'uvicorn',
        'aiohttp',
        'pandas',
        'python-multipart',
        'websockets'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("📦 Installing missing packages...")
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
    
    print("✅ All required packages are installed")
    return True

def check_files():
    """Check if required files exist"""
    required_files = ['main.py', 'requirements.txt']
    missing_files = []
    
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing files: {', '.join(missing_files)}")
        return False
    
    print("✅ All required files present")
    return True

def create_directories():
    """Create necessary directories"""
    directories = ["static/uploads", "logs"]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Created necessary directories")

def check_waha_server():
    """Check if WAHA server is running"""
    print("🔌 Checking WAHA server connection...")
    
    try:
        response = requests.get(f"{WAHA_BASE_URL}/ping", timeout=5)
        if response.status_code == 200:
            print("✅ WAHA server is running")
            return True
    except:
        pass
    
    print(f"⚠️  WAHA server not detected on {WAHA_VM_IP}:4500")
    print("💡 Make sure WAHA server is running before creating sessions")
    print("")
    
    # Ask if user wants to continue
    response = input("Continue anyway? (y/N): ").lower()
    return response == 'y'

def start_application():
    """Start the main application"""
    global main_process
    
    print("\n🚀 Starting WhatsApp Agent...")
    print(f"🔗 Dashboard will be available at: {API_GATEWAY_URL}")
    print("📝 Press Ctrl+C to stop\n")
    
    # Start the main application
    try:
        main_process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Wait a moment for the server to start
        time.sleep(3)
        
        # Check if server is running
        try:
            response = requests.get(f"{API_GATEWAY_URL}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ Server is running at {API_GATEWAY_URL}")
                
                # Try to open browser
                try:
                    webbrowser.open(API_GATEWAY_URL)
                    print("🌐 Opening dashboard in browser...")
                except:
                    print(f"📱 Please open your browser and navigate to: {API_GATEWAY_URL}")
        except:
            print(f"⚠️  Server is starting... Please wait and navigate to: {API_GATEWAY_URL}")
        
        # Stream output
        for line in iter(main_process.stdout.readline, ''):
            print(line, end='')
            
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
        stop_application()
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        stop_application()

def stop_application():
    """Stop the application gracefully"""
    global main_process
    
    if main_process:
        print("📤 Sending shutdown signal...")
        main_process.terminate()
        
        try:
            main_process.wait(timeout=5)
            print("✅ Application stopped gracefully")
        except subprocess.TimeoutExpired:
            print("⚠️  Force stopping application...")
            main_process.kill()
            main_process.wait()
            print("✅ Application stopped")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("\n🛑 Received shutdown signal...")
    stop_application()
    sys.exit(0)

def main():
    """Main startup sequence"""
    print_banner()
    
    # Check environment
    print("🔍 Checking requirements...")
    
    if not check_python_version():
        sys.exit(1)
    
    if not check_requirements():
        sys.exit(1)
    
    print("📁 Checking directory structure...")
    
    if not check_files():
        sys.exit(1)
    
    create_directories()
    
    # Check WAHA server
    waha_running = check_waha_server()
    
    if not waha_running:
        print("⚠️  Starting without WAHA server")
        print("   Some features may not be available")
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start the application
    start_application()

if __name__ == "__main__":
    main()