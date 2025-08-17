#!/bin/bash

# CuWapp Complete Deployment Script
# Deploys all services with environment variables
# Run this after pulling from GitHub

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Banner
echo -e "${BLUE}"
echo "======================================================"
echo "       CuWapp Complete Deployment Script"
echo "======================================================"
echo -e "${NC}"

# Check if running as root (recommended for production)
if [[ $EUID -ne 0 ]]; then
   print_warning "Not running as root. Some operations may require sudo."
fi

# Step 1: Export environment variables
print_info "Loading environment variables..."
if [ -f ".env.production" ]; then
    export $(cat .env.production | grep -v '^#' | xargs)
    print_status "Production environment loaded"
elif [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
    print_status "Environment variables loaded from .env"
else
    print_warning "No .env file found. Using defaults..."
fi

# Set default values if not in env
export ENV=${ENV:-production}
export NEW_SERVER_IP=${NEW_SERVER_IP:-34.173.85.56}
export WAHA_VM_EXTERNAL_IP=${WAHA_VM_EXTERNAL_IP:-34.133.143.67}
export API_GATEWAY_URL=${API_GATEWAY_URL:-https://app.cuwapp.com}
export AUTH_SERVICE_URL=${AUTH_SERVICE_URL:-https://auth.cuwapp.com}
export LANDING_PAGE_URL=${LANDING_PAGE_URL:-https://cuwapp.com}

print_info "Environment Configuration:"
echo "  - Server IP: $NEW_SERVER_IP"
echo "  - WAHA VM: $WAHA_VM_EXTERNAL_IP"
echo "  - API Gateway: $API_GATEWAY_URL"
echo ""

# Step 2: Install dependencies if needed
print_info "Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Installing..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi
print_status "Node.js $(node --version) installed"

print_info "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Installing..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-venv
fi
print_status "Python $(python3 --version) installed"

# Step 3: Build and run Landing Page (Port 5500)
print_info "Setting up Landing Page..."
cd 10210-landing

# Copy environment file
if [ ! -f ".env.local" ]; then
    cat > .env.local << EOF
NEXT_PUBLIC_API_GATEWAY_URL=$API_GATEWAY_URL
NEXT_PUBLIC_AUTH_SERVICE_URL=$AUTH_SERVICE_URL
NEXT_PUBLIC_LANDING_PAGE_URL=$LANDING_PAGE_URL
NEXT_PUBLIC_ADMIN_SERVICE_URL=${ADMIN_SERVICE_URL:-https://admin.cuwapp.com}
NEXT_PUBLIC_NEW_SERVER_IP=$NEW_SERVER_IP
NEXT_PUBLIC_WAHA_VM_IP=$WAHA_VM_EXTERNAL_IP
EOF
    print_status "Created .env.local for landing page"
fi

print_info "Installing landing page dependencies..."
npm install --silent

print_info "Building landing page..."
npm run build

print_info "Starting landing page on port 5500..."
# Kill existing process if running
pkill -f "next start -p 5500" || true
PORT=5500 npm start > ../logs/landing.log 2>&1 &
print_status "Landing page started on port 5500"

cd ..

# Step 4: Build and run Auth Service (Port 5502)
print_info "Setting up Auth Service..."
cd 10210-auth

# Copy environment file
if [ ! -f ".env.local" ]; then
    cat > .env.local << EOF
NEXT_PUBLIC_API_URL=$API_GATEWAY_URL
NEXT_PUBLIC_API_GATEWAY_URL=$API_GATEWAY_URL
NEXT_PUBLIC_AUTH_SERVICE_URL=$AUTH_SERVICE_URL
NEXT_PUBLIC_LANDING_PAGE_URL=$LANDING_PAGE_URL
NEXT_PUBLIC_NEW_SERVER_IP=$NEW_SERVER_IP
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=$API_GATEWAY_URL
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=$API_GATEWAY_URL
EOF
    # Append existing Clerk keys if they exist
    if [ -f ".env" ]; then
        grep "CLERK" .env >> .env.local || true
    fi
    print_status "Created .env.local for auth service"
fi

print_info "Installing auth service dependencies..."
npm install --silent

print_info "Building auth service..."
npm run build

print_info "Starting auth service on port 5502..."
# Kill existing process if running
pkill -f "next start -p 5502" || true
PORT=5502 npm start > ../logs/auth.log 2>&1 &
print_status "Auth service started on port 5502"

cd ..

# Step 5: Run API Gateway (Port 8000)
print_info "Setting up API Gateway..."
cd 10210-api

# Create logs directory
mkdir -p ../logs

# Create Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_info "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
print_status "API dependencies installed"

print_info "Starting API Gateway on port 8000..."
# Kill existing process if running
pkill -f "python.*api_gateway.py" || true
nohup python api_gateway.py > ../logs/api_gateway.log 2>&1 &
print_status "API Gateway started on port 8000"

# Step 6: Run Warmer Service (Port 8001)
print_info "Starting Warmer Service on port 8001..."
cd ../10210-warmer

# Use the same virtual environment
source ../10210-api/venv/bin/activate

# Kill existing process if running
pkill -f "python.*main.py.*8001" || true
nohup python main.py > ../logs/warmer.log 2>&1 &
print_status "Warmer service started on port 8001"

cd ..

# Step 7: Run Campaign Service (Port 8002)
print_info "Starting Campaign Service on port 8002..."
cd 10210-campaigns

# Use the same virtual environment
source ../10210-api/venv/bin/activate

# Kill existing process if running
pkill -f "python.*main.py.*8002" || true
nohup python main.py > ../logs/campaign.log 2>&1 &
print_status "Campaign service started on port 8002"

cd ..

# Step 8: Build Docker image for user containers
print_info "Building Docker image for user containers..."
cd 10210-api

# Build the multi-service Docker image
docker build -f Dockerfile.multiservice -t cuwhapp-multi-service:latest .
print_status "Docker image built: cuwhapp-multi-service:latest"

# Tag for Docker Hub
docker tag cuwhapp-multi-service:latest stainlessman/cuwhapp-multi-service:latest
print_status "Docker image tagged for Docker Hub"

# Optional: Push to Docker Hub (requires login)
print_info "To push to Docker Hub, run:"
echo "  docker login"
echo "  docker push stainlessman/cuwhapp-multi-service:latest"

cd ..

# Step 9: Check all services
print_info "Checking service status..."
sleep 5  # Give services time to start

# Function to check if service is running
check_service() {
    local port=$1
    local name=$2
    if curl -s http://localhost:$port/health > /dev/null 2>&1 || curl -s http://localhost:$port > /dev/null 2>&1; then
        print_status "$name is running on port $port"
        return 0
    else
        print_error "$name is NOT running on port $port"
        return 1
    fi
}

echo ""
print_info "Service Status:"
check_service 5500 "Landing Page"
check_service 5502 "Auth Service"
check_service 8000 "API Gateway"
check_service 8001 "Warmer Service"
check_service 8002 "Campaign Service"

# Step 10: Show logs location
echo ""
print_info "Service logs available at:"
echo "  - Landing: logs/landing.log"
echo "  - Auth: logs/auth.log"
echo "  - API Gateway: logs/api_gateway.log"
echo "  - Warmer: logs/warmer.log"
echo "  - Campaign: logs/campaign.log"

# Step 11: Show next steps
echo ""
echo -e "${GREEN}======================================================"
echo "       Deployment Complete!"
echo "======================================================"
echo -e "${NC}"
echo "Next steps:"
echo "1. Update DNS records to point to: $NEW_SERVER_IP"
echo "2. Configure nginx (if not already done):"
echo "   sudo cp nginx-vm.conf /etc/nginx/nginx.conf"
echo "   sudo nginx -t && sudo systemctl reload nginx"
echo "3. Push Docker image to registry:"
echo "   docker push stainlessman/cuwhapp-multi-service:latest"
echo "4. Pull image on User VM ($NEW_SERVER_IP):"
echo "   docker pull stainlessman/cuwhapp-multi-service:latest"
echo ""
echo "To stop all services, run: ./stop-all-services.sh"
echo "To view logs, run: tail -f logs/*.log"
echo ""
print_status "All services deployed successfully!"