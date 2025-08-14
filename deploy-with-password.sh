#!/usr/bin/expect -f

set timeout 300
set password "\$Oden3474"

# Copy docker-compose.yml
spawn scp -o StrictHostKeyChecking=no docker-compose.prod.yml root@174.138.55.42:~/docker-compose.yml
expect "password:"
send "$password\r"
expect eof

# Copy nginx config
spawn scp -o StrictHostKeyChecking=no nginx-docker.conf root@174.138.55.42:~/nginx-docker.conf
expect "password:"
send "$password\r"
expect eof

# Copy .env.production
spawn scp -o StrictHostKeyChecking=no .env.production root@174.138.55.42:~/.env
expect "password:"
send "$password\r"
expect eof

# Deploy via SSH
spawn ssh -o StrictHostKeyChecking=no root@174.138.55.42
expect "password:"
send "$password\r"
expect "root@*"

# Pull images
send "echo 'Pulling latest images...'\r"
expect "root@*"
send "docker-compose pull\r"
expect "root@*"

# Stop old containers
send "echo 'Stopping old containers...'\r"
expect "root@*"
send "docker-compose down\r"
expect "root@*"

# Start new containers
send "echo 'Starting new containers...'\r"
expect "root@*"
send "docker-compose up -d\r"
expect "root@*"

# Check status
send "echo 'Checking container status...'\r"
expect "root@*"
send "docker ps\r"
expect "root@*"

send "echo 'Deployment complete!'\r"
expect "root@*"
send "exit\r"
expect eof