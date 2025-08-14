#!/bin/bash

# Start CuWhapp Admin Dashboard

cd /Users/JE/Documents/102102/10210-admin

# Activate virtual environment if it exists
if [ -d "admin_venv" ]; then
    source admin_venv/bin/activate
else
    # Create virtual environment if it doesn't exist
    echo "Creating virtual environment..."
    python3 -m venv admin_venv
    source admin_venv/bin/activate
fi

# Install/upgrade required dependencies
echo "Installing admin dashboard dependencies..."
pip install --upgrade fastapi uvicorn jinja2 httpx pydantic docker sqlalchemy

# Set Python path to include project directory
export PYTHONPATH="/Users/JE/Documents/102102/10210-admin:$PYTHONPATH"

# Start admin dashboard
echo "Starting admin dashboard on port 8001..."
python admin_dashboard.py