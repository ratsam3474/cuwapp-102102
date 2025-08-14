#!/bin/bash

# Deployment script for Cuwhapp to DigitalOcean Docker Droplet

set -e

# Configuration
DOCKERHUB_USERNAME="stainlessman"
DROPLET_IP="174.138.55.42"
DOCKER_TOKEN="${DOCKER_TOKEN:-YOUR_DOCKER_TOKEN_HERE}"

echo "🚀 Deploying Cuwhapp to Docker Droplet..."

# Step 1: Build and tag images locally
echo "📦 Building Docker images..."

echo "Building Landing Page..."
docker build -t ${DOCKERHUB_USERNAME}/cuwhapp-landing:latest ./10210-landing

echo "Building API..."
docker build -t ${DOCKERHUB_USERNAME}/cuwhapp-api:latest ./10210-api

echo "Building Auth..."
docker build -t ${DOCKERHUB_USERNAME}/cuwhapp-auth:latest ./10210-auth

echo "Building Admin..."
docker build -t ${DOCKERHUB_USERNAME}/cuwhapp-admin:latest ./10210-admin

echo "Building Nginx..."
# Create a simple Dockerfile for nginx with config
cat > nginx.Dockerfile << EOF
FROM nginx:alpine
COPY nginx-docker.conf /etc/nginx/nginx.conf
EOF
docker build -f nginx.Dockerfile -t ${DOCKERHUB_USERNAME}/cuwhapp-nginx:latest .
rm nginx.Dockerfile

# Step 2: Push to DockerHub
echo "☁️ Pushing images to DockerHub..."
echo "Logging into DockerHub..."
echo "${DOCKER_TOKEN}" | docker login -u ${DOCKERHUB_USERNAME} --password-stdin

docker push ${DOCKERHUB_USERNAME}/cuwhapp-landing:latest
docker push ${DOCKERHUB_USERNAME}/cuwhapp-api:latest
docker push ${DOCKERHUB_USERNAME}/cuwhapp-auth:latest
docker push ${DOCKERHUB_USERNAME}/cuwhapp-admin:latest
docker push ${DOCKERHUB_USERNAME}/cuwhapp-nginx:latest

# Step 3: Deploy to droplet
echo "🌊 Deploying to Docker droplet..."

# Copy necessary files to droplet
echo "Copying configuration files..."
scp docker-compose.prod.yml root@${DROPLET_IP}:~/docker-compose.yml
scp nginx-docker.conf root@${DROPLET_IP}:~/nginx-docker.conf
scp .env.production root@${DROPLET_IP}:~/.env

# Update docker-compose file with correct username
ssh root@${DROPLET_IP} "sed -i 's/YOUR_DOCKERHUB_USERNAME/${DOCKERHUB_USERNAME}/g' docker-compose.yml"

# SSH into droplet and deploy
ssh root@${DROPLET_IP} << 'ENDSSH'
echo "Pulling latest images..."
docker-compose pull

echo "Stopping old containers..."
docker-compose down

echo "Starting new containers..."
docker-compose up -d

echo "Waiting for services to start..."
sleep 10

echo "Checking container status..."
docker ps

echo "✅ Deployment complete!"
ENDSSH

echo ""
echo "========================================="
echo "✅ Deployment successful!"
echo "========================================="
echo "Your application is now running at:"
echo "  🌐 Main site: http://${DROPLET_IP}"
echo "  📊 Admin: http://${DROPLET_IP}/admin"
echo "  🔐 Auth: http://${DROPLET_IP}/auth"
echo "  🚀 API: http://${DROPLET_IP}/dashboard"
echo ""
echo "WAHA instances:"
echo "  📱 Free: http://${DROPLET_IP}:4500"
echo "========================================="