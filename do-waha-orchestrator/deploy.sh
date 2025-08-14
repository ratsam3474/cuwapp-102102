#!/bin/bash

# DigitalOcean Function Deployment Script

echo "🚀 Deploying WAHA Orchestrator to DigitalOcean Functions..."

# Check if doctl is installed
if ! command -v doctl &> /dev/null
then
    echo "❌ doctl CLI not found. Please install it first:"
    echo "brew install doctl (macOS)"
    echo "or visit: https://docs.digitalocean.com/reference/doctl/how-to/install/"
    exit 1
fi

# Authenticate with DigitalOcean (if not already)
echo "📝 Checking DigitalOcean authentication..."
if ! doctl auth list &> /dev/null; then
    echo "Please authenticate with DigitalOcean:"
    doctl auth init
fi

# Get or create Functions namespace
echo "🏗️ Setting up Functions namespace..."
NAMESPACE=$(doctl serverless namespaces list --format Label --no-header | head -1)

if [ -z "$NAMESPACE" ]; then
    echo "Creating new Functions namespace..."
    doctl serverless namespaces create --label waha-orchestrator --region nyc1
    NAMESPACE="waha-orchestrator"
else
    echo "Using existing namespace: $NAMESPACE"
fi

# Connect to the namespace
doctl serverless connect $NAMESPACE

# Deploy the function
echo "📦 Deploying function..."
doctl serverless deploy . --env .env

# Get the function URL
echo "🔗 Getting function URL..."
FUNCTION_URL=$(doctl serverless functions get waha-manager/waha-manager --url)

echo "✅ Deployment complete!"
echo ""
echo "========================================="
echo "Function URL: $FUNCTION_URL"
echo "========================================="
echo ""
echo "Test your function with:"
echo "curl -X POST $FUNCTION_URL \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"action\": \"list\"}'"
echo ""
echo "Create a WAHA instance:"
echo "curl -X POST $FUNCTION_URL \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo "    \"action\": \"create\","
echo "    \"docker_host\": \"167.99.123.45\","
echo "    \"image\": \"devlikeapro/waha-plus:latest\","
echo "    \"user_id\": \"test-user\""
echo "  }'"