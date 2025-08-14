#!/bin/bash

# WhatsApp Agent Startup Script for Linux/Mac
# Make executable with: chmod +x start.sh

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Banner
echo -e "${BLUE}"
echo "======================================================"
echo "           WhatsApp Agent - Starting..."
echo "======================================================"
echo -e "${NC}"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    echo "Please install Python 3.8+ from your package manager:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "  CentOS/RHEL:   sudo yum install python3 python3-pip"
    echo "  macOS:         brew install python3"
    exit 1
fi

print_status "Python $(python3 --version 2>&1 | cut -d' ' -f2) detected"

# Check if required files exist
if [[ ! -f "main.py" ]]; then
    print_error "main.py not found"
    echo "Please ensure all project files are in the current directory"
    exit 1
fi

if [[ ! -f "requirements.txt" ]]; then
    print_error "requirements.txt not found"
    echo "Please ensure all project files are in the current directory"
    exit 1
fi

print_status "Required files found"

# Create virtual environment if it doesn't exist
if [[ ! -d "venv" ]]; then
    print_info "Creating virtual environment..."
    python3 -m venv venv
    if [[ $? -ne 0 ]]; then
        print_error "Failed to create virtual environment"
        exit 1
    fi
    print_status "Virtual environment created"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip --quiet

# Install/upgrade requirements
print_info "Installing/updating requirements..."
pip install -r requirements.txt --quiet

if [[ $? -ne 0 ]]; then
    print_error "Failed to install requirements"
    exit 1
fi

print_status "Requirements installed successfully"

# Check if WAHA server is running (optional)
print_info "Checking WAHA server connection..."
if curl -s http://localhost:4500/ping > /dev/null 2>&1; then
    print_status "WAHA server is running"
else
    print_warning "WAHA server not detected on localhost:4500"
    print_info "Make sure WAHA server is running before creating sessions"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Please start your WAHA server first, then run this script again"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}======================================================"
echo "      WhatsApp Agent is starting..."
echo "      Dashboard will open at: https://app.cuwapp.com"
echo "      Press Ctrl+C to stop the server"
echo -e "======================================================${NC}"
echo ""

# Start the application
python3 start.py

echo ""
print_info "WhatsApp Agent has stopped."