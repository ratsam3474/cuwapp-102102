"""
WhatsApp Agent - Dependency Installation Script
Run this to install all required dependencies
"""

import subprocess
import sys
import os

def install_dependencies():
    """Install all required dependencies"""
    print("🔧 Installing WhatsApp Agent dependencies...")
    
    # Check if pip is available
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "--version"], stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("❌ pip is not available. Please install pip first.")
        return False
    
    # Install requirements
    try:
        print("📦 Installing Python packages...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("✅ All dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def create_venv():
    """Create virtual environment if it doesn't exist"""
    if not os.path.exists("venv"):
        print("🏗️  Creating virtual environment...")
        try:
            subprocess.check_call([sys.executable, "-m", "venv", "venv"])
            print("✅ Virtual environment created!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create virtual environment: {e}")
            return False
    else:
        print("✅ Virtual environment already exists")
        return True

def main():
    """Main installation function"""
    print("🚀 WhatsApp Agent - Setup Assistant")
    print("=" * 40)
    
    # Create virtual environment
    if not create_venv():
        print("\n💡 You can still proceed without a virtual environment")
        response = input("Continue installation? (y/n): ")
        if response.lower() != 'y':
            return
    
    # Install dependencies
    if install_dependencies():
        print("\n🎉 Setup completed successfully!")
        print("\n📝 Next steps:")
        print("1. Make sure WAHA server is running on localhost:4500")
        print("2. Run: python start.py")
        print("3. Open: https://app.cuwapp.com")
        print("\n📖 For detailed instructions, see SETUP_GUIDE.md")
    else:
        print("\n❌ Setup failed. Please check the errors above.")

if __name__ == "__main__":
    main()