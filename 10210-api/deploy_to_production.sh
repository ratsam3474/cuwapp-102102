#!/bin/bash

# Deployment script for production server 174.138.55.42
# Run this from your local machine

echo "========================================="
echo "DEPLOYING WARMER FIXES TO PRODUCTION"
echo "========================================="

SERVER="root@174.138.55.42"
REMOTE_DIR="/root/102102/10210-api"

echo ""
echo "Step 1: Copying migration scripts..."
scp add_warmer_archive.py $SERVER:$REMOTE_DIR/
scp fix_session_name_constraint.py $SERVER:$REMOTE_DIR/
scp fix_production_warmer.py $SERVER:$REMOTE_DIR/

echo ""
echo "Step 2: Copying updated API files..."
scp warmer/api.py $SERVER:$REMOTE_DIR/warmer/
scp warmer/warmer_engine.py $SERVER:$REMOTE_DIR/warmer/
scp warmer/models.py $SERVER:$REMOTE_DIR/warmer/
scp analytics/api.py $SERVER:$REMOTE_DIR/analytics/

echo ""
echo "Step 3: SSHing to server to run migrations..."
ssh $SERVER << 'ENDSSH'
cd /root/102102/10210-api

echo ""
echo "Checking database status..."
python3 fix_production_warmer.py

echo ""
echo "Adding archive columns to warmer_sessions..."
python3 add_warmer_archive.py

echo ""
echo "Fixing session name constraint..."
python3 fix_session_name_constraint.py

echo ""
echo "Restarting API service..."
pkill -f "python3 main.py" || true
sleep 2
nohup python3 main.py > api.log 2>&1 &

echo ""
echo "Checking if API is running..."
sleep 3
ps aux | grep "python3 main.py" | grep -v grep

echo "Deployment complete!"
ENDSSH

echo ""
echo "========================================="
echo "DEPLOYMENT FINISHED"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Test warmer functionality at http://174.138.55.42:4500"
echo "2. Check analytics at http://174.138.55.42:4500/api/analytics/warmer/overview"
echo "3. Monitor logs: ssh $SERVER 'tail -f /root/102102/10210-api/api.log'"