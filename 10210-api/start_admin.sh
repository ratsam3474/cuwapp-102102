#!/bin/bash

# Start CuWhapp Admin Dashboard

cd /Users/JE/Documents/10210

# Activate virtual environment
source /Users/JE/Documents/10210/admin_venv/bin/activate

# Install/upgrade required dependencies
echo "Installing admin dashboard dependencies..."
pip install --upgrade fastapi uvicorn jinja2 httpx pydantic docker sqlalchemy

# Set Python path to include project directory
export PYTHONPATH="/Users/JE/Documents/10210:$PYTHONPATH"

# Start admin dashboard
echo "Starting admin dashboard on port 8001..."
python /Users/JE/Documents/10210/admin_dashboard.py