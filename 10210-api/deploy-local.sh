#!/bin/bash

# CuWhapp Local Deployment Script
# Quick setup for local development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 CuWhapp Local Deployment Script${NC}"
echo ""

# Function to print colored messages
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check Docker
check_docker() {
    log_info "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed!"
        echo "Install Docker with: curl -fsSL https://get.docker.com | sh"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker is not running!"
        echo "Start Docker and try again"
        exit 1
    fi
    
    log_success "Docker is installed and running"
}

# Check Docker Compose
check_docker_compose() {
    log_info "Checking Docker Compose..."
    
    if ! command -v docker-compose &> /dev/null; then
        log_warning "Docker Compose not found, using docker compose"
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    log_success "Docker Compose is available"
}

# Setup environment
setup_environment() {
    log_info "Setting up environment..."
    
    # Check if .env.local exists
    if [ ! -f .env.local ]; then
        if [ -f .env.example ]; then
            cp .env.example .env.local
            log_success "Created .env.local from .env.example"
        else
            # Create basic .env.local
            cat > .env.local << 'EOF'
# Local Development Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=info

# Database (SQLite for local)
DATABASE_URL=sqlite:///./cuwhapp.db

# WAHA WhatsApp
WAHA_BASE_URL=http://localhost:4500
WAHA_PRINT_QR=true

# Clerk Auth (GET FROM https://clerk.dev)
CLERK_PUBLISHABLE_KEY=pk_test_YOUR_KEY_HERE
CLERK_SECRET_KEY=sk_test_YOUR_KEY_HERE

# Hyperswitch Payments (Sandbox - Pre-configured)
HYPERSWITCH_BASE_URL=https://sandbox.hyperswitch.io
HYPERSWITCH_API_KEY=snd_MF6Nc4A5FY42UMtEN1BbdVFHhVC8pXYYATFZNgEIbiFTrA827lCTNO8FldzsBSeR
HYPERSWITCH_PUBLISHABLE_KEY=pk_snd_68a3be601ff24b82a4b163a8b3d046b2
PAYMENT_TEST_MODE=true

# Groq AI (Pre-configured)
GROQ_API_KEY=YOUR_GROQ_API_KEY_HERE
GROQ_MODEL=llama-3.1-8b-instant

# Features
ENABLE_PAYMENTS=true
ENABLE_WARMER=true
ENABLE_ANALYTICS=true
EOF
            log_success "Created .env.local with default configuration"
        fi
        
        log_warning "⚠️  IMPORTANT: Edit .env.local and add your Clerk API keys!"
        log_info "Get your keys from: https://clerk.dev"
        echo ""
        read -p "Have you added your Clerk API keys? (y/n): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_error "Please add your Clerk API keys to .env.local and run again"
            exit 1
        fi
    else
        log_success ".env.local already exists"
    fi
}

# Create Docker Compose file for local
create_docker_compose() {
    log_info "Creating local Docker Compose configuration..."
    
    cat > docker-compose.local.yml << 'EOF'
version: '3.8'

services:
  # Main Backend
  cuwhapp-backend:
    build: .
    container_name: cuwhapp-backend
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - DATABASE_URL=sqlite:///./cuwhapp.db
      - PAYMENT_TEST_MODE=true
      - DEBUG=true
    env_file:
      - .env.local
    volumes:
      - ./data:/app/data
      - ./uploads:/app/uploads
      - ./static:/app/static
      - ./cuwhapp.db:/app/cuwhapp.db
    networks:
      - cuwhapp-network
    healthcheck:
      test: ["CMD", "curl", "-f", "https://app.cuwapp.com/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # WAHA WhatsApp Plus (Unlimited sessions for local)
  waha:
    image: devlikeapro/waha-plus:latest
    container_name: cuwhapp-waha
    ports:
      - "4500:3000"
    environment:
      - WAHA_PRINT_QR=true
      - WAHA_SESSION_STORE_ENABLED=true
      - WAHA_LOG_LEVEL=info
      - WAHA_MAX_SESSIONS=1000  # Support many sessions locally
    volumes:
      - waha_sessions:/app/sessions
      - waha_files:/app/files
    networks:
      - cuwhapp-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/ping"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  waha_sessions:
  waha_files:

networks:
  cuwhapp-network:
    driver: bridge
EOF
    
    log_success "Created docker-compose.local.yml"
}

# Pull WAHA Plus image
pull_waha_plus() {
    log_info "Pulling WAHA Plus image (unlimited sessions)..."
    
    # Login to Docker Hub for WAHA Plus
    docker login -u devlikeapro -p ${DOCKER_TOKEN:-YOUR_DOCKER_TOKEN_HERE} &> /dev/null
    
    # Pull WAHA Plus
    docker pull devlikeapro/waha-plus:latest
    
    # Logout for security
    docker logout &> /dev/null
    
    log_success "WAHA Plus image ready (unlimited sessions)"
}

# Start services
start_services() {
    log_info "Starting services..."
    
    # Pull WAHA Plus first
    pull_waha_plus
    
    $COMPOSE_CMD -f docker-compose.local.yml up -d
    
    log_success "Services starting..."
    
    # Wait for services
    log_info "Waiting for services to be ready..."
    sleep 10
    
    # Check health
    if curl -f https://app.cuwapp.com/health &> /dev/null; then
        log_success "Backend is healthy!"
    else
        log_warning "Backend not ready yet, check logs with: $COMPOSE_CMD -f docker-compose.local.yml logs"
    fi
    
    if curl -f http://localhost:4500/ping &> /dev/null; then
        log_success "WAHA is healthy!"
    else
        log_warning "WAHA not ready yet, check logs with: $COMPOSE_CMD -f docker-compose.local.yml logs waha"
    fi
}

# Initialize database
init_database() {
    log_info "Initializing database..."
    
    # Run migrations
    $COMPOSE_CMD -f docker-compose.local.yml exec -T cuwhapp-backend python migrate_db.py 2>/dev/null || true
    
    log_success "Database initialized"
}

# Show status
show_status() {
    echo ""
    log_success "🎉 Local deployment complete!"
    echo ""
    echo -e "${GREEN}Access your services:${NC}"
    echo "  📱 Main App:     https://app.cuwapp.com"
    echo "  🔗 WAHA API:     http://localhost:4500"
    echo "  📊 API Docs:     https://app.cuwapp.com/docs"
    echo ""
    echo -e "${YELLOW}Quick Commands:${NC}"
    echo "  View logs:       $COMPOSE_CMD -f docker-compose.local.yml logs -f"
    echo "  Stop services:   $COMPOSE_CMD -f docker-compose.local.yml down"
    echo "  Restart:         $COMPOSE_CMD -f docker-compose.local.yml restart"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "  1. Check WAHA QR code: $COMPOSE_CMD -f docker-compose.local.yml logs waha"
    echo "  2. Scan QR with WhatsApp mobile"
    echo "  3. Test payment flow with sandbox cards"
    echo "  4. Start developing!"
    echo ""
    log_info "For production deployment, see DEPLOY_README.md"
}

# Main execution
main() {
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}     CuWhapp Local Deployment${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo ""
    
    check_docker
    check_docker_compose
    setup_environment
    create_docker_compose
    start_services
    init_database
    show_status
}

# Handle command line arguments
case "${1:-deploy}" in
    "stop")
        log_info "Stopping services..."
        $COMPOSE_CMD -f docker-compose.local.yml down
        log_success "Services stopped"
        ;;
    "restart")
        log_info "Restarting services..."
        $COMPOSE_CMD -f docker-compose.local.yml restart
        log_success "Services restarted"
        ;;
    "logs")
        $COMPOSE_CMD -f docker-compose.local.yml logs -f
        ;;
    "status")
        $COMPOSE_CMD -f docker-compose.local.yml ps
        ;;
    "clean")
        log_warning "Cleaning up everything..."
        $COMPOSE_CMD -f docker-compose.local.yml down -v
        rm -f cuwhapp.db
        log_success "Cleanup complete"
        ;;
    *)
        main
        ;;
esac