#!/usr/bin/expect -f

set timeout 30
set password "\$Oden3474"

spawn ssh -o StrictHostKeyChecking=no root@174.138.55.42
expect "password:"
send "$password\r"
expect "root@*"

# Allow HTTP and HTTPS traffic
send "ufw allow 80/tcp\r"
expect "root@*"

send "ufw allow 443/tcp\r"
expect "root@*"

send "ufw status\r"
expect "root@*"

send "exit\r"
expect eof