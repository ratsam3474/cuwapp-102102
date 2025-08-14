#!/bin/bash

# Firewall configuration for WhatsApp Agent Platform
# Run this script on your Digital Ocean server as root

echo "Configuring firewall for WhatsApp Agent Platform..."

# Allow SSH (keep this first to avoid locking yourself out)
ufw allow 22/tcp

# Allow main nginx port
ufw allow 10210/tcp

# Allow individual service ports
ufw allow 5500/tcp  # Landing page
ufw allow 5502/tcp  # Auth service
ufw allow 8000/tcp  # Main API
ufw allow 8001/tcp  # Admin panel
ufw allow 4500/tcp  # WAHA WhatsApp

# Allow HTTP and HTTPS for future nginx setup
ufw allow 80/tcp
ufw allow 443/tcp

# Enable firewall if not already enabled
ufw --force enable

# Show status
ufw status verbose

echo "Firewall configuration complete!"
echo ""
echo "Accessible ports:"
echo "  - 22 (SSH)"
echo "  - 80 (HTTP)"
echo "  - 443 (HTTPS)"
echo "  - 4500 (WAHA)"
echo "  - 5500 (Landing)"
echo "  - 5502 (Auth)"
echo "  - 8000 (API)"
echo "  - 8001 (Admin)"
echo "  - 10210 (Main nginx)"
