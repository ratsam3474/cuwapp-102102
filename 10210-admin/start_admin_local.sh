#!/bin/bash

# Start CuWhapp Admin Dashboard
echo "Starting CuWhapp Admin Dashboard..."

# Navigate to the admin directory
cd /Users/JE/Documents/102102/10210-admin

# Check if virtual environment exists, create if not
if [ ! -d "admin_venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv admin_venv
fi

# Activate virtual environment
source admin_venv/bin/activate

# Install/upgrade required dependencies
echo "Installing admin dashboard dependencies..."
pip install --upgrade pip
pip install --upgrade -r admin_requirements.txt

# Set Python path to include project directory
export PYTHONPATH="/Users/JE/Documents/102102/10210-admin:$PYTHONPATH"

# Set database path
export DATABASE_URL="sqlite:///data/wagent.db"

# Start admin dashboard on port 8001
echo "Starting admin dashboard on port 8001..."
uvicorn admin_dashboard:app --host 0.0.0.0 --port 8001 --reload