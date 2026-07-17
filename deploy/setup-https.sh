#!/usr/bin/env bash
# Add a domain + HTTPS (Let's Encrypt) to the MoonBite Dashboard on the VPS.
# Run as root AFTER setup-dashboard.sh. Requires the domain's DNS to already
# point at this server's public IP.
#
# Usage:
#   DOMAIN=your.domain.tld ./setup-https.sh
#
# Default domain uses sslip.io (a free wildcard DNS that maps
# <ip>.sslip.io -> <ip> with no signup). Replace with your own domain
# by exporting DOMAIN before running.
set -euo pipefail

DOMAIN="${DOMAIN:-67-205-154-64.sslip.io}"

echo "=== 1/4  Install certbot ==="
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq certbot python3-certbot-nginx > /dev/null

echo "=== 2/4  Point nginx at the domain ==="
cat > /etc/nginx/sites-available/moonbite-dashboard <<NGINX
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:8050;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
    }
}
NGINX
nginx -t && systemctl reload nginx

echo "=== 3/4  Issue certificate + enable HTTPS redirect ==="
# --register-unsafely-without-email keeps this non-interactive; certbot still
# installs a systemd timer that auto-renews the cert before expiry.
certbot --nginx -d "$DOMAIN" \
    --non-interactive --agree-tos \
    --register-unsafely-without-email \
    --redirect

echo "=== 4/4  Open firewall for 443 ==="
ufw allow 443/tcp 2>/dev/null || true
nginx -t && systemctl reload nginx

echo ""
echo "=== DONE ==="
echo "Dashboard live at: https://$DOMAIN"
