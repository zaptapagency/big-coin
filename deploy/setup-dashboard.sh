#!/usr/bin/env bash
# Deploy MoonBite Dashboard (Flask) on the VPS behind nginx
# Run as root on 67.205.154.64
set -euo pipefail

REPO_URL="https://github.com/zaptapagency/big-coin.git"
APP_DIR="/opt/moonbite-dashboard"
APP_USER="dashboard"
PORT=8050  # internal gunicorn port; nginx proxies 80 → here

echo "=== 1/7  Install system packages ==="
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv nginx git curl > /dev/null

echo "=== 2/7  Create app user & clone repo ==="
id "$APP_USER" &>/dev/null || useradd -r -s /usr/sbin/nologin -m "$APP_USER"
rm -rf "$APP_DIR"
git clone --depth 1 "$REPO_URL" "$APP_DIR"
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

echo "=== 3/7  Python venv + dependencies ==="
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/venv/bin/pip" install --quiet flask gunicorn ecdsa

echo "=== 4/7  Systemd service ==="
cat > /etc/systemd/system/moonbite-dashboard.service <<UNIT
[Unit]
Description=MoonBite Dashboard (Flask/Gunicorn)
After=network.target

[Service]
User=$APP_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/gunicorn web_app:app \
    --bind 127.0.0.1:$PORT \
    --workers 1 \
    --timeout 300 \
    --access-logfile - \
    --error-logfile -
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable moonbite-dashboard
systemctl restart moonbite-dashboard

echo "=== 5/7  Nginx reverse proxy ==="
cat > /etc/nginx/sites-available/moonbite-dashboard <<'NGINX'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/moonbite-dashboard /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

echo "=== 6/7  Firewall ==="
ufw allow 80/tcp 2>/dev/null || true

echo "=== 7/7  Health check ==="
sleep 3
echo "--- gunicorn status ---"
systemctl status moonbite-dashboard --no-pager -l || true
echo ""
echo "--- gunicorn journal (last 30 lines) ---"
journalctl -u moonbite-dashboard --no-pager -n 30 || true
echo ""
echo "--- curl test ---"
curl -sf http://127.0.0.1:$PORT/ > /dev/null && echo "OK: gunicorn responds" || echo "FAIL: gunicorn not responding"
curl -sf http://127.0.0.1/ > /dev/null && echo "OK: nginx responds" || echo "FAIL: nginx not responding"

echo ""
echo "=== DONE ==="
echo "Dashboard: http://67.205.154.64"
