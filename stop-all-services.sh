#!/bin/bash

# Stop all CuWapp services

echo "Stopping all CuWapp services..."

# Stop Next.js services
echo "Stopping Landing Page..."
pkill -f "next start -p 5500" || true

echo "Stopping Auth Service..."
pkill -f "next start -p 5502" || true

# Stop Python services
echo "Stopping API Gateway..."
pkill -f "python.*api_gateway.py" || true

echo "Stopping Warmer Service..."
pkill -f "python.*main.py.*8001" || true

echo "Stopping Campaign Service..."
pkill -f "python.*main.py.*8002" || true

echo "All services stopped."

# Show any remaining Node or Python processes
echo ""
echo "Remaining Node processes:"
ps aux | grep node | grep -v grep || echo "None"

echo ""
echo "Remaining Python processes:"
ps aux | grep python | grep -v grep || echo "None"