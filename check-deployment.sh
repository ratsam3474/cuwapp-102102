#!/usr/bin/expect -f

set timeout 30
set password "\$Oden3474"

spawn ssh -o StrictHostKeyChecking=no root@174.138.55.42
expect "password:"
send "$password\r"
expect "root@*"

# Check running containers
send "docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'\r"
expect "root@*"

# Test the application
send "curl -s -o /dev/null -w '%{http_code}' http://localhost\r"
expect "root@*"

send "exit\r"
expect eof