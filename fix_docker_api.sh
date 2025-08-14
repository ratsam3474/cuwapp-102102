#!/bin/bash

echo "Fixing Docker API proxy on remote server..."
echo "You'll need to enter the password: \$Oden3474"
echo ""

ssh root@174.138.55.42 << 'EOF'
echo "Checking existing docker-api-proxy container..."
docker ps -a | grep docker-api-proxy

echo "Stopping and removing old container if exists..."
docker stop docker-api-proxy 2>/dev/null
docker rm docker-api-proxy 2>/dev/null

echo "Starting new Docker API proxy..."
docker run -d \
  --name docker-api-proxy \
  --restart unless-stopped \
  -p 2375:2375 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  alpine/socat tcp-listen:2375,fork,reuseaddr unix-connect:/var/run/docker.sock

echo "Waiting for container to start..."
sleep 3

echo "Checking if container is running..."
docker ps | grep docker-api-proxy

echo "Testing Docker API locally..."
curl -s http://localhost:2375/version | head -5

echo "Checking all running containers..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo "Done!"
EOF