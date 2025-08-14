#!/bin/bash

echo "🧹 Cleaning up Docker containers on remote server..."
echo "You'll need to enter the password: \$Oden3474"
echo ""

ssh root@174.138.55.42 << 'EOF'
echo "Current running containers:"
docker ps --format "table {{.Names}}\t{{.Status}}"
echo ""

echo "⚠️  Stopping and removing all containers EXCEPT docker-api-proxy..."
echo ""

# List of containers to remove
CONTAINERS=(
    "cuwhapp-nginx"
    "cuwhapp-auth"
    "cuwhapp-landing"
    "cuwhapp-api"
    "cuwhapp-redis"
    "cuwhapp-admin"
    "waha-test-fun-4536"
    "waha-pro-4501"
    "waha-free"
)

# Stop and remove each container
for container in "${CONTAINERS[@]}"; do
    echo "Removing $container..."
    docker stop $container 2>/dev/null
    docker rm $container 2>/dev/null
done

echo ""
echo "Removing any other WAHA containers..."
docker ps -a --filter "name=waha-" --format "{{.Names}}" | while read container; do
    echo "Removing $container..."
    docker stop $container 2>/dev/null
    docker rm $container 2>/dev/null
done

echo ""
echo "Removing any stopped containers..."
docker container prune -f

echo ""
echo "✅ Cleanup complete! Remaining containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "Docker images on server:"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

echo ""
echo "Do you want to remove unused images? (This will free up disk space)"
echo "Run: docker image prune -a"
EOF