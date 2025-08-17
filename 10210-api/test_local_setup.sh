#!/bin/bash

# Local testing setup script
echo "🚀 Local Multi-Service Container Testing"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Step 1: Build the multi-service image
echo -e "${YELLOW}Step 1: Building multi-service Docker image...${NC}"
docker build -f Dockerfile.multiservice -t cuwapp/multi-service:latest .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Image built successfully${NC}"
else
    echo -e "${RED}❌ Failed to build image${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 2: Testing container creation...${NC}"

# Test creating a container for user1
python3 test_local_container.py create test-user-1 free

echo ""
echo -e "${YELLOW}Step 3: Testing multiple users...${NC}"

# Create multiple test users
python3 test_local_container.py create test-user-2 hobby
python3 test_local_container.py create test-user-3 pro

echo ""
echo -e "${YELLOW}Step 4: Listing all containers...${NC}"
python3 test_local_container.py list

echo ""
echo -e "${GREEN}✨ Local testing complete!${NC}"
echo ""
echo "Available commands:"
echo "  python3 test_local_container.py create <user_id> [plan]"
echo "  python3 test_local_container.py stop <user_id>"
echo "  python3 test_local_container.py delete <user_id>"
echo "  python3 test_local_container.py list"
echo ""
echo "Test the services:"
echo "  User 1 API: http://localhost:40xxx/health"
echo "  User 1 Warmer: http://localhost:20xxx/health"
echo "  User 1 Campaign: http://localhost:30xxx/health"
echo ""
echo "Clean up when done:"
echo "  docker stop \$(docker ps -q --filter name=cuwapp-user-)"
echo "  docker rm \$(docker ps -aq --filter name=cuwapp-user-)"