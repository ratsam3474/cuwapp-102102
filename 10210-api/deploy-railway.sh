#!/bin/bash

echo "🚂 Deploying CuWhapp to Railway..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo -e "${RED}Railway CLI not installed!${NC}"
    echo "Installing Railway CLI..."
    curl -fsSL https://railway.app/install.sh | sh
fi

# Login to Railway
echo -e "${YELLOW}Logging into Railway...${NC}"
railway login

# Initialize Railway project
echo -e "${YELLOW}Initializing Railway project...${NC}"
railway init

# Link to GitHub (optional but recommended)
echo -e "${YELLOW}Would you like to connect to GitHub for automatic deployments? (y/n)${NC}"
read -r github_choice
if [[ $github_choice == "y" ]]; then
    railway link
fi

# Set up environment variables
echo -e "${YELLOW}Setting up environment variables...${NC}"

# Database
railway variables set POSTGRES_DB=cuwhapp
railway variables set POSTGRES_USER=cuwhapp
railway variables set POSTGRES_PASSWORD=$(openssl rand -hex 32)

# Generate secure tokens
railway variables set SECRET_KEY=$(openssl rand -hex 32)
railway variables set JWT_SECRET=$(openssl rand -hex 32)
railway variables set ADMIN_TOKEN=$(openssl rand -hex 32)

# Clerk (you'll need to set these)
echo -e "${YELLOW}Enter your Clerk API key (from https://clerk.dev):${NC}"
read -r clerk_key
railway variables set CLERK_API_KEY="$clerk_key"

# Groq API
echo -e "${YELLOW}Enter your Groq API key (from https://console.groq.com):${NC}"
read -r groq_key
railway variables set GROQ_API_KEY="$groq_key"

# Hyperswitch
echo -e "${YELLOW}Enter your Hyperswitch API key:${NC}"
read -r hyperswitch_key
railway variables set HYPERSWITCH_API_KEY="$hyperswitch_key"

# Deploy
echo -e "${GREEN}Deploying to Railway...${NC}"
railway up

# Get deployment URL
echo -e "${GREEN}Getting deployment URLs...${NC}"
railway status

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Set up custom domain in Railway dashboard"
echo "2. Configure PostgreSQL database connection"
echo "3. Update environment variables as needed"
echo "4. Monitor logs with: railway logs"