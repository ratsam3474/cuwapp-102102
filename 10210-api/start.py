#!/usr/bin/env python3
"""
WhatsApp Agent Startup Script
Easy way to start the WhatsApp Agent application
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def check_requirements():
    """Check if all requirements are met"""
    print("🔍 Checking requirements...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        return False
    
    print(f"✅ Python {sys.version.split()[0]} detected")
    
    # Check if requirements are installed
    try:
        import fastapi
        import uvicorn
        import requests
        print("✅ All required packages are installed")
    except ImportError as e:
        print(f"❌ Missing package: {e.name}")
        print("💡 Run: pip install -r requirements.txt")
        return False
    
    return True

def check_directory_structure():
    """Check if all required files exist"""
    print("📁 Checking directory structure...")
    
    required_files = [
        "main.py",
        "waha_functions.py",
        "static/index.html",
        "static/css/style.css",
        "static/js/app.js"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing required files:")
        for file in missing_files:
            print(f"   - {file}")
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
    
    import requests
    try:
        response = requests.get("http://localhost:4500/ping", timeout=5)
        if response.status_code == 200:
            print("✅ WAHA server is running")
            return True
    except:
        pass
    
    print("⚠️  WAHA server not detected on localhost:4500")
    print("💡 Make sure WAHA server is running before creating sessions")
    return False

def start_server():
    """Start the WhatsApp Agent server"""
    print("🚀 Starting WhatsApp Agent server...")
    print("📱 Dashboard will open automatically in your browser")
    print("🔗 Manual access: https://app.cuwapp.com")
    print("\n" + "="*50)
    print("Press Ctrl+C to stop the server")
    print("="*50 + "\n")
    
    # Open browser after a short delay
    def open_browser():
        time.sleep(3)
        try:
            webbrowser.open("https://app.cuwapp.com")
        except:
            pass
    
    import threading
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Start the server
    try:
        import uvicorn
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")

def show_banner():
    """Show application banner"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║                    WhatsApp Agent v1.0                      ║
║               Professional Management Dashboard              ║
║                                                              ║
║  Features:                                                   ║
║  • Session Management    • Contact Management                ║
║  • Chat Interface       • Group Management                  ║
║  • File Sharing         • Message Broadcasting              ║
║  • Real-time Updates    • Professional UI                   ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def main():
    """Main startup function"""
    show_banner()
    
    # Check requirements
    if not check_requirements():
        input("\nPress Enter to exit...")
        return
    
    # Check directory structure
    if not check_directory_structure():
        print("\n💡 Please ensure all project files are in the correct locations")
        input("Press Enter to exit...")
        return
    
    # Create directories
    create_directories()
    
    # Check WAHA server (optional)
    waha_running = check_waha_server()
    
    if not waha_running:
        response = input("\nWAHA server not detected. Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("💡 Start your WAHA server first, then run this script again")
            return
    
    print("\n🎉 All checks passed! Starting application...\n")
    
    # Start the server
    start_server()

if __name__ == "__main__":
    main()