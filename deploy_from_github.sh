#!/bin/bash

# Deployment script to run on Digital Ocean server
# This pulls from GitHub and runs main_startup.py

set -e

echo "🚀 Deploying 102102 from GitHub..."

# Configuration
GITHUB_REPO="https://github.com/ratsam3474/102102.git"
DEPLOY_DIR="/root/102102"
BRANCH="main"

# Clone or update repository
if [ -d "$DEPLOY_DIR" ]; then
    echo "📥 Updating existing repository..."
    cd $DEPLOY_DIR
    git fetch origin
    git reset --hard origin/$BRANCH
    git pull origin $BRANCH
else
    echo "📥 Cloning repository..."
    git clone $GITHUB_REPO $DEPLOY_DIR
    cd $DEPLOY_DIR
fi

# Copy environment files (these should NOT be in git)
echo "📝 Setting up environment files..."
if [ -f "/root/.env.production" ]; then
    cp /root/.env.production $DEPLOY_DIR/.env
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
apt-get update
apt-get install -y python3-pip python3-venv

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate and install dependencies
source venv/bin/activate
pip install --upgrade pip
pip install requests python-dotenv

# Set environment variables for remote Docker
export DOCKER_HOST=tcp://localhost:2375
export SERVER_IP=174.138.55.42
export ENV=production

# Run the main startup script
echo "🚀 Starting services..."
python3 main_startup.py

echo "✅ Deployment complete!"