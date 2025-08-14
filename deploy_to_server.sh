#!/bin/bash

echo "🚀 Manual deployment to Digital Ocean"
echo "You'll need to enter the password: \$Oden3474"
echo ""

# First, push to GitHub
echo "📤 Pushing to GitHub..."
git add .
git commit -m "Deploy to server"
git push origin main

# Then deploy on server
echo "📥 Deploying on server..."
ssh root@174.138.55.42 << 'EOF'
# Clone or update repository
if [ -d "/root/102102" ]; then
    echo "Updating repository..."
    cd /root/102102
    git pull origin main
else
    echo "Cloning repository..."
    # Replace with your GitHub username
    git clone https://github.com/ratsam3474/102102.git /root/102102
    cd /root/102102
fi

# Setup environment
export DOCKER_HOST=tcp://localhost:2375
export SERVER_IP=174.138.55.42

# Run the startup script
echo "Starting services..."
python3 main_startup.py
EOF