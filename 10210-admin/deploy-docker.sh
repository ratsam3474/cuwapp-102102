#!/bin/bash

# CuWhapp Docker Deployment Script
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🐳 CuWhapp Docker Deployment${NC}"
echo "=================================="

# Function to check command exists
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ $1 is not installed${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ $1 is installed${NC}"
}

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"
check_command docker
check_command docker-compose

# Load environment variables
if [ -f .env.docker ]; then
    echo -e "${GREEN}✅ Loading environment variables${NC}"
    export $(cat .env.docker | grep -v '^#' | xargs)
else
    echo -e "${YELLOW}⚠️  No .env.docker file found, using defaults${NC}"
fi

# Stop existing containers
echo -e "${YELLOW}Stopping existing containers...${NC}"
docker-compose -f docker-compose.full.yml down 2>/dev/null || true

# Build images
echo -e "${BLUE}Building Docker images...${NC}"
docker-compose -f docker-compose.full.yml build

# Start services
echo -e "${BLUE}Starting services...${NC}"
docker-compose -f docker-compose.full.yml up -d

# Wait for services to be healthy
echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
sleep 10

# Check service status
echo -e "${BLUE}Service Status:${NC}"
docker-compose -f docker-compose.full.yml ps

# Show access URLs
echo ""
echo -e "${GREEN}🎉 CuWhapp is deployed!${NC}"
echo ""
echo -e "${BLUE}Access URLs:${NC}"
echo "  Main App:     http://localhost (via Nginx)"
echo "  Landing:      https://www.cuwapp.com"
echo "  Blog:         http://localhost:5501"
echo "  Auth:         https://auth.cuwapp.com"
echo "  API/Dashboard: https://app.cuwapp.com"
echo "  WAHA:         http://localhost:4500"
echo ""
echo -e "${YELLOW}Commands:${NC}"
echo "  View logs:    docker-compose -f docker-compose.full.yml logs -f"
echo "  Stop all:     docker-compose -f docker-compose.full.yml down"
echo "  Restart:      docker-compose -f docker-compose.full.yml restart"
echo ""
echo -e "${GREEN}Happy messaging! 🚀${NC}"