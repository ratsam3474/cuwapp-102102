#!/usr/bin/expect -f

set timeout 300
set password "\$Oden3474"

# Deploy via SSH
spawn ssh -o StrictHostKeyChecking=no root@174.138.55.42
expect "password:"
send "$password\r"
expect "root@*"

# Pull images
send "echo '📦 Pulling latest images...'\r"
expect "root@*"
send "docker compose pull\r"
expect "root@*"

# Stop old containers (except WAHA instances)
send "echo '🛑 Stopping old containers...'\r"
expect "root@*"
send "docker compose down\r"
expect "root@*"

# Start new containers
send "echo '🚀 Starting new containers...'\r"
expect "root@*"
send "docker compose up -d\r"
expect "root@*"

# Wait for services
send "sleep 10\r"
expect "root@*"

# Check status
send "echo '📊 Checking container status...'\r"
expect "root@*"
send "docker ps\r"
expect "root@*"

send "echo '✅ Deployment complete!'\r"
expect "root@*"
send "exit\r"
expect eof