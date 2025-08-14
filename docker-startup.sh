#!/bin/bash

# CuWhapp Docker Startup Script
echo "🚀 Starting CuWhapp Application Suite..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env file with your API keys and configuration"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Build and start all services
echo "🔨 Building Docker images..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check health of services
echo "🔍 Checking service health..."
services=("nginx" "landing" "api" "admin" "auth" "redis")
all_healthy=true

for service in "${services[@]}"; do
    if docker-compose ps | grep -q "$service.*Up"; then
        echo "✅ $service is running"
    else
        echo "❌ $service failed to start"
        all_healthy=false
    fi
done

if $all_healthy; then
    echo ""
    echo "✨ CuWhapp is ready!"
    echo ""
    echo "🌐 Access the application at:"
    echo "   Main App:  http://localhost:10210"
    echo "   Dashboard: http://localhost:10210/dashboard"
    echo "   Admin:     http://localhost:10210/admin"
    echo "   Blog:      http://localhost:10210/blog"
    echo ""
    echo "📊 View logs: docker-compose logs -f"
    echo "🛑 Stop all:  docker-compose down"
else
    echo ""
    echo "⚠️  Some services failed to start. Check logs with:"
    echo "   docker-compose logs"
fi