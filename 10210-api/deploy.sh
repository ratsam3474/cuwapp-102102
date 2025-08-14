#!/bin/bash

# CuWhapp Deployment Script
# Usage: ./deploy.sh [dev|prod|staging]

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default environment
ENVIRONMENT=${1:-dev}

echo -e "${BLUE}🚀 CuWhapp Deployment Script${NC}"
echo -e "${BLUE}Environment: ${ENVIRONMENT}${NC}"
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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command_exists docker; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command_exists docker-compose; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    # Check git
    if ! command_exists git; then
        log_warning "Git is not installed. Some features may not work."
    fi
    
    # Check curl
    if ! command_exists curl; then
        log_error "curl is not installed. Please install curl first."
        exit 1
    fi
    
    log_success "All prerequisites met"
}

# Function to setup environment
setup_environment() {
    log_info "Setting up environment configuration..."
    
    case $ENVIRONMENT in
        "dev")
            ENV_FILE=".env"
            COMPOSE_FILE="docker-compose.yml"
            ;;
        "prod")
            ENV_FILE=".env.production"
            COMPOSE_FILE="docker-compose.prod.yml"
            ;;
        "staging")
            ENV_FILE=".env.staging"
            COMPOSE_FILE="docker-compose.staging.yml"
            ;;
        *)
            log_error "Invalid environment: $ENVIRONMENT. Use: dev, prod, or staging"
            exit 1
            ;;
    esac
    
    # Check if environment file exists
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "${ENV_FILE}.example" ]; then
            log_warning "Environment file $ENV_FILE not found. Copying from example..."
            cp "${ENV_FILE}.example" "$ENV_FILE"
            log_warning "⚠️  Please edit $ENV_FILE with your configuration before deploying!"
            
            # Ask user if they want to edit now
            read -p "Do you want to edit the environment file now? (y/n): " edit_env
            if [ "$edit_env" = "y" ] || [ "$edit_env" = "Y" ]; then
                ${EDITOR:-nano} "$ENV_FILE"
            else
                log_warning "Remember to edit $ENV_FILE before production deployment!"
            fi
        else
            log_error "Environment file $ENV_FILE not found and no example available."
            exit 1
        fi
    fi
    
    # Export environment for Docker Compose
    export ENV_FILE
    export COMPOSE_FILE
    
    log_success "Environment configured: $ENV_FILE"
}

# Function to create necessary directories
create_directories() {
    log_info "Creating necessary directories..."
    
    # Create directories for volumes
    mkdir -p data uploads logs ssl backups
    mkdir -p static/exports
    
    # Set permissions
    chmod 755 data uploads logs static/exports
    
    # Create ssl directory for certificates
    if [ "$ENVIRONMENT" = "prod" ]; then
        mkdir -p ssl
        log_info "SSL directory created. Please add your SSL certificates:"
        log_info "  - ssl/fullchain.pem"
        log_info "  - ssl/privkey.pem"
    fi
    
    log_success "Directories created"
}

# Function to run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    # Wait for database to be ready
    log_info "Waiting for database to be ready..."
    sleep 10
    
    # Run migrations in the main container
    if docker-compose -f "$COMPOSE_FILE" ps | grep -q "cuwhapp-main.*Up"; then
        docker-compose -f "$COMPOSE_FILE" exec cuwhapp-main python migrations/add_user_id_to_campaigns.py || true
        docker-compose -f "$COMPOSE_FILE" exec cuwhapp-main python migrations/add_user_id_to_warmer_tables.py || true
        log_success "Database migrations completed"
    else
        log_warning "Main container not running. Migrations will run on first startup."
    fi
}

# Function to setup SSL certificates (Let's Encrypt)
setup_ssl() {
    if [ "$ENVIRONMENT" = "prod" ]; then
        log_info "Setting up SSL certificates..."
        
        if command_exists certbot; then
            read -p "Enter your domain name: " DOMAIN
            if [ ! -z "$DOMAIN" ]; then
                log_info "Obtaining SSL certificate for $DOMAIN..."
                certbot certonly --standalone -d "$DOMAIN" -d "www.$DOMAIN" -d "admin.$DOMAIN"
                
                # Copy certificates to ssl directory
                cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ssl/
                cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" ssl/
                
                log_success "SSL certificates configured"
            else
                log_warning "No domain provided. Skipping SSL setup."
            fi
        else
            log_warning "Certbot not installed. Please install SSL certificates manually."
            log_info "Place your certificates in:"
            log_info "  - ssl/fullchain.pem"
            log_info "  - ssl/privkey.pem"
        fi
    fi
}

# Function to build and start services
start_services() {
    log_info "Building and starting services..."
    
    # Pull latest images
    log_info "Pulling latest Docker images..."
    docker-compose -f "$COMPOSE_FILE" pull
    
    # Build custom images
    log_info "Building application images..."
    docker-compose -f "$COMPOSE_FILE" build --no-cache
    
    # Start services
    log_info "Starting services..."
    docker-compose -f "$COMPOSE_FILE" up -d
    
    log_success "Services started"
}

# Function to run health checks
health_check() {
    log_info "Running health checks..."
    
    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 30
    
    # Check main application
    if curl -f https://app.cuwapp.com/health >/dev/null 2>&1; then
        log_success "Main application is healthy"
    else
        log_error "Main application health check failed"
        return 1
    fi
    
    # Check admin dashboard
    if curl -f https://admin.cuwapp.com/health >/dev/null 2>&1; then
        log_success "Admin dashboard is healthy"
    else
        log_warning "Admin dashboard health check failed"
    fi
    
    # Check WAHA API
    if curl -f http://localhost:4500/ping >/dev/null 2>&1; then
        log_success "WAHA API is healthy"
    else
        log_warning "WAHA API health check failed"
    fi
    
    # Check database connection
    if docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U cuwhapp_user -d cuwhapp >/dev/null 2>&1; then
        log_success "Database connection is healthy"
    else
        log_warning "Database connection check failed"
    fi
    
    log_success "Health checks completed"
}

# Function to show service status
show_status() {
    log_info "Service Status:"
    docker-compose -f "$COMPOSE_FILE" ps
    
    echo ""
    log_info "Service URLs:"
    echo "  Main Application: https://app.cuwapp.com"
    echo "  Admin Dashboard:  https://admin.cuwapp.com"
    echo "  WAHA API:        http://localhost:4500"
    echo "  API Documentation: https://app.cuwapp.com/docs"
    
    if [ "$ENVIRONMENT" = "prod" ]; then
        echo ""
        echo "  Production URLs:"
        echo "  Main: https://cuwapp.com"
        echo "  Admin: https://admin.cuwapp.com"
    fi
}

# Function to setup monitoring
setup_monitoring() {
    if [ "$ENVIRONMENT" = "prod" ]; then
        log_info "Setting up monitoring..."
        
        # Create monitoring script
        cat > monitor.sh << 'EOF'
#!/bin/bash
# Simple monitoring script
while true; do
    if ! curl -f https://app.cuwapp.com/health >/dev/null 2>&1; then
        echo "$(date): Main application is down!" >> monitor.log
        # Add your notification logic here (email, Slack, etc.)
    fi
    sleep 60
done
EOF
        
        chmod +x monitor.sh
        log_success "Basic monitoring setup completed"
        log_info "You can run ./monitor.sh in the background for basic monitoring"
    fi
}

# Function to create backup script
create_backup_script() {
    log_info "Creating backup script..."
    
    cat > backup.sh << 'EOF'
#!/bin/bash
# Database backup script
BACKUP_DIR="./backups"
DATE=$(date +"%Y%m%d_%H%M%S")

mkdir -p $BACKUP_DIR

# Backup PostgreSQL database
docker-compose exec -T postgres pg_dump -U cuwhapp_user cuwhapp > "$BACKUP_DIR/cuwhapp_db_$DATE.sql"

# Backup uploaded files
tar -czf "$BACKUP_DIR/uploads_$DATE.tar.gz" uploads/

# Backup configuration
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" *.env *.yml ssl/

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF
    
    chmod +x backup.sh
    log_success "Backup script created: ./backup.sh"
}

# Function to show logs
show_logs() {
    log_info "Recent logs (use Ctrl+C to exit):"
    docker-compose -f "$COMPOSE_FILE" logs -f --tail=50
}

# Main deployment function
deploy() {
    log_info "Starting CuWhapp deployment..."
    
    check_prerequisites
    setup_environment
    create_directories
    
    # Production-specific setup
    if [ "$ENVIRONMENT" = "prod" ]; then
        setup_ssl
    fi
    
    start_services
    run_migrations
    health_check
    setup_monitoring
    create_backup_script
    
    show_status
    
    log_success "🎉 Deployment completed successfully!"
    
    if [ "$ENVIRONMENT" = "prod" ]; then
        echo ""
        log_info "Production deployment checklist:"
        echo "  ✅ Services are running"
        echo "  ⚠️  Update DNS records to point to this server"
        echo "  ⚠️  Configure firewall rules (ports 80, 443, 22)"
        echo "  ⚠️  Setup monitoring and alerts"
        echo "  ⚠️  Configure automated backups"
        echo "  ⚠️  Test all critical user flows"
        echo ""
        log_warning "Remember to:"
        echo "  - Set strong passwords in $ENV_FILE"
        echo "  - Configure SSL certificates"
        echo "  - Setup monitoring"
        echo "  - Test payment webhooks"
        echo "  - Verify email delivery"
    fi
    
    echo ""
    log_info "Useful commands:"
    echo "  View logs:     docker-compose -f $COMPOSE_FILE logs -f"
    echo "  Restart:       docker-compose -f $COMPOSE_FILE restart"
    echo "  Stop:          docker-compose -f $COMPOSE_FILE down"
    echo "  Update:        ./deploy.sh $ENVIRONMENT"
    echo "  Backup:        ./backup.sh"
    echo "  Monitor:       ./monitor.sh"
}

# Handle different commands
case "${2:-deploy}" in
    "logs")
        setup_environment
        show_logs
        ;;
    "status")
        setup_environment
        show_status
        ;;
    "health")
        setup_environment
        health_check
        ;;
    "stop")
        setup_environment
        log_info "Stopping services..."
        docker-compose -f "$COMPOSE_FILE" down
        log_success "Services stopped"
        ;;
    "restart")
        setup_environment
        log_info "Restarting services..."
        docker-compose -f "$COMPOSE_FILE" restart
        log_success "Services restarted"
        ;;
    "update")
        setup_environment
        log_info "Updating services..."
        docker-compose -f "$COMPOSE_FILE" pull
        docker-compose -f "$COMPOSE_FILE" up -d
        health_check
        log_success "Services updated"
        ;;
    *)
        deploy
        ;;
esac