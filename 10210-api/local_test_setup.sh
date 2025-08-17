#!/bin/bash

# Complete Local Test Environment Setup
# This sets up auth, landing, WAHA, API Gateway, and main app

echo "🚀 Complete Local Test Environment Setup"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get local IP (for Mac)
LOCAL_IP=$(ipconfig getifaddr en0 || ipconfig getifaddr en1 || echo "localhost")
echo -e "${BLUE}Local IP: $LOCAL_IP${NC}"
echo ""

# Step 1: Create Docker network
echo -e "${YELLOW}Step 1: Creating Docker network...${NC}"
docker network create cuwhapp-network 2>/dev/null || echo "Network already exists"
echo -e "${GREEN}✅ Network ready${NC}"
echo ""

# Step 2: Start WAHA Plus instance
echo -e "${YELLOW}Step 2: Starting WAHA Plus instance...${NC}"
docker run -d \
    --name waha-plus-1 \
    --network cuwhapp-network \
    -p 4500:3000 \
    -e WAHA_API_KEY=your-api-key \
    -e WAHA_BASE_URL=http://$LOCAL_IP:4500 \
    --restart unless-stopped \
    devlikeapro/waha-plus:latest

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ WAHA Plus started on port 4500${NC}"
else
    echo -e "${YELLOW}WAHA Plus already running or failed to start${NC}"
fi
echo ""

# Step 3: Set environment variables
echo -e "${YELLOW}Step 3: Setting environment variables...${NC}"
cat > .env.local << EOF
# Local Test Environment Configuration
ENV=local
WAHA_BASE_URL=http://$LOCAL_IP
WAHA_MAX_SESSIONS_PER_INSTANCE=10
API_URL=http://localhost:8080
AUTH_URL=http://localhost:5502
LANDING_URL=http://localhost:10210
GATEWAY_URL=http://localhost:8000
DASHBOARD_URL=http://localhost:3000

# Database
DB_PATH=./data/wagent.db

# WAHA Configuration
WAHA_API_KEY=your-api-key

# Docker Host (for container management)
DOCKER_HOST=unix:///var/run/docker.sock

# DigitalOcean Function (local simulation)
DO_FUNCTION_URL=http://localhost:8003
EOF

echo -e "${GREEN}✅ Environment variables saved to .env.local${NC}"
echo ""

# Step 4: Start Auth Service (landing page simulation)
echo -e "${YELLOW}Step 4: Creating mock auth service...${NC}"
cat > mock_auth.py << 'EOF'
from flask import Flask, request, redirect
import json
import uuid

app = Flask(__name__)

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>CuWapp Auth - Local Test</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            .container {
                background: white;
                padding: 2rem;
                border-radius: 10px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                text-align: center;
                max-width: 400px;
            }
            h1 { color: #667eea; }
            input {
                width: 100%;
                padding: 10px;
                margin: 10px 0;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                width: 100%;
            }
            button:hover { opacity: 0.9; }
            .plan-selector {
                margin: 20px 0;
            }
            select {
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 CuWapp</h1>
            <h2>Local Test Login</h2>
            <form action="/login" method="post">
                <input type="email" name="email" placeholder="Email" value="test@example.com" required>
                <input type="password" name="password" placeholder="Password" value="password123" required>
                <div class="plan-selector">
                    <label>Select Plan:</label>
                    <select name="plan">
                        <option value="free">Free (30 min timeout)</option>
                        <option value="hobby">Hobby ($29/mo)</option>
                        <option value="pro">Pro ($99/mo)</option>
                        <option value="enterprise">Enterprise ($299/mo)</option>
                    </select>
                </div>
                <button type="submit">Login & Start Container</button>
            </form>
        </div>
    </body>
    </html>
    '''

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    plan = request.form.get('plan', 'free')
    
    # Generate mock token and user ID
    token = str(uuid.uuid4())
    user_id = email.split('@')[0].replace('.', '-')
    
    # Redirect to API Gateway with credentials
    gateway_url = f"http://localhost:8000?token={token}&user_id={user_id}&plan={plan}"
    return redirect(gateway_url)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5502, debug=True)
EOF

echo -e "${GREEN}✅ Mock auth service created${NC}"
echo ""

# Step 5: Start API Gateway
echo -e "${YELLOW}Step 5: Starting API Gateway...${NC}"
python3 api_gateway.py &
GATEWAY_PID=$!
echo -e "${GREEN}✅ API Gateway started on port 8000 (PID: $GATEWAY_PID)${NC}"
echo ""

# Step 6: Start main API service
echo -e "${YELLOW}Step 6: Starting main API service...${NC}"
export $(cat .env.local | xargs)
python3 main.py &
API_PID=$!
echo -e "${GREEN}✅ Main API started on port 8080 (PID: $API_PID)${NC}"
echo ""

# Step 7: Start mock auth service
echo -e "${YELLOW}Step 7: Starting mock auth service...${NC}"
python3 mock_auth.py &
AUTH_PID=$!
echo -e "${GREEN}✅ Mock auth started on port 5502 (PID: $AUTH_PID)${NC}"
echo ""

# Step 8: Create local container manager (simulates DO Function)
echo -e "${YELLOW}Step 8: Creating local container manager...${NC}"
cat > local_container_manager.py << 'EOF'
from flask import Flask, request, jsonify
import subprocess
import json
import os

app = Flask(__name__)

# Import the container manager functions
import sys
sys.path.append('do_functions')
from container_manager import create_user_container, stop_user_container, restart_user_container

@app.route('/function/container_manager', methods=['POST'])
def handle_container_request():
    """Simulate DO Function endpoint"""
    data = request.json
    action = data.get('action', 'create')
    user_id = data.get('user_id')
    plan_type = data.get('plan_type', 'free')
    
    try:
        if action == 'create':
            result = create_user_container(user_id, plan_type)
        elif action == 'stop':
            result = stop_user_container(user_id)
        elif action == 'restart':
            result = restart_user_container(user_id)
        else:
            return jsonify({'error': f'Unknown action: {action}'}), 400
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8003, debug=True)
EOF

python3 local_container_manager.py &
CONTAINER_MGR_PID=$!
echo -e "${GREEN}✅ Container manager started on port 8003 (PID: $CONTAINER_MGR_PID)${NC}"
echo ""

# Step 9: Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✨ Local Test Environment Ready!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Services Running:"
echo -e "  ${BLUE}Auth/Login:${NC}     http://localhost:5502"
echo -e "  ${BLUE}API Gateway:${NC}    http://localhost:8000"
echo -e "  ${BLUE}Main API:${NC}       http://localhost:8080"
echo -e "  ${BLUE}WAHA Plus:${NC}      http://localhost:4500"
echo -e "  ${BLUE}Container Mgr:${NC}  http://localhost:8003"
echo ""
echo "Test Flow:"
echo "1. Open http://localhost:5502 in your browser"
echo "2. Login with any email and select a plan"
echo "3. You'll be redirected to API Gateway"
echo "4. Gateway will provision your container"
echo "5. You'll see the loading page"
echo "6. Then redirect to dashboard with dynamic URLs"
echo ""
echo "Process PIDs (for stopping later):"
echo "  API Gateway: $GATEWAY_PID"
echo "  Main API: $API_PID"
echo "  Auth Service: $AUTH_PID"
echo "  Container Manager: $CONTAINER_MGR_PID"
echo ""
echo "To stop all services:"
echo "  kill $GATEWAY_PID $API_PID $AUTH_PID $CONTAINER_MGR_PID"
echo "  docker stop waha-plus-1"
echo "  docker stop \$(docker ps -q --filter name=cuwapp-user-)"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"

# Keep script running
wait