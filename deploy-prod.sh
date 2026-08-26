#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/var/www/feishengwangying"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
MOBILE_DIR="$PROJECT_DIR/mobile"
ADMIN_DIR="$PROJECT_DIR/admin"
PPTH5_DIR="$PROJECT_DIR/ppth5"
PPTAGENT_DIR="$PROJECT_DIR/pptagent"
SOURCE_DIR="${DEPLOY_SOURCE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
UV_BOOTSTRAP_DIR="/opt/feishengwangying-uv"
UV_BIN="$UV_BOOTSTRAP_DIR/bin/uv"
export UV_PYTHON_INSTALL_DIR="/opt/feishengwangying-python"
CERT_FILE=/etc/nginx/ssl/lzhan.xyz/lzhan.xyz.pem
KEY_FILE=/etc/nginx/ssl/lzhan.xyz/lzhan.xyz.key

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "ERROR: deploy-prod.sh must run as root" >&2
  exit 1
fi

for required in \
  "$SOURCE_DIR/backend/app.py" \
  "$SOURCE_DIR/backend/requirements.txt" \
  "$SOURCE_DIR/backend/data/course_knowledge_index.json" \
  "$SOURCE_DIR/frontend/dist/index.html" \
  "$SOURCE_DIR/mobile/dist/index.html" \
  "$SOURCE_DIR/admin/dist/index.html" \
  "$SOURCE_DIR/ppth5/dist-web/index.html"; do
  if [ ! -s "$required" ]; then
    echo "ERROR: required release artifact is missing: $required" >&2
    exit 1
  fi
done

if [ ! -d "$SOURCE_DIR/rag文档" ]; then
  echo "ERROR: course knowledge corpus is missing: $SOURCE_DIR/rag文档" >&2
  exit 1
fi

if [ ! -s "$CERT_FILE" ] || [ ! -s "$KEY_FILE" ]; then
  echo "ERROR: install the lzhan.xyz Nginx certificate before deploying" >&2
  exit 1
fi

if [ ! -s "$BACKEND_DIR/.env" ]; then
  echo "ERROR: migrate the production backend/.env before deploying" >&2
  exit 1
fi

if [ ! -s "$PPTAGENT_DIR/backend/.env" ]; then
  echo "ERROR: migrate the production PPT backend/.env before deploying" >&2
  exit 1
fi

echo "[1/9] Install runtime dependencies"
apt-get update -qq
apt-get install -y ca-certificates nginx python3 python3-pip python3-venv curl ffmpeg rsync

# The production host has less than 2 GiB RAM. A small swap file prevents
# dependency installation or FFmpeg from taking down the whole instance.
if ! swapon --noheadings --show=NAME | grep -q .; then
  if [ ! -e /swapfile ]; then
    fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048 status=progress
    chmod 600 /swapfile
    mkswap /swapfile >/dev/null
  fi
  chmod 600 /swapfile
  swapon /swapfile
  grep -qE '^/swapfile[[:space:]]' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

if [ ! -x "$UV_BIN" ]; then
  python3 -m venv "$UV_BOOTSTRAP_DIR"
  "$UV_BOOTSTRAP_DIR/bin/pip" install --no-cache-dir "uv==0.8.14"
fi

echo "[2/9] Prepare directories"
mkdir -p "$BACKEND_DIR/data" "$FRONTEND_DIR/dist" "$MOBILE_DIR/dist" "$ADMIN_DIR/dist" "$PPTH5_DIR" "$PPTAGENT_DIR/backend" "$PPTAGENT_DIR/dist-web"
mkdir -p /var/log/feishengwangying

echo "[3/9] Sync backend"
rsync -a --checksum --delete --exclude "venv/" --exclude "data/" --exclude ".env" "$SOURCE_DIR/backend/" "$BACKEND_DIR/"
install -o root -g root -m 644 \
  "$SOURCE_DIR/backend/data/course_knowledge_index.json" \
  "$BACKEND_DIR/data/course_knowledge_index.json"
cd "$BACKEND_DIR"
if [ ! -x venv/bin/python ] || ! venv/bin/python -c 'import sys; raise SystemExit(sys.version_info[:2] != (3, 12))'; then
  rm -rf venv
  "$UV_BIN" venv --python 3.12 venv
fi
"$UV_BIN" pip install --python venv/bin/python -r requirements.txt
venv/bin/python -c "from app import init_auth_db; init_auth_db(); print('database initialized')"

echo "[4/9] Sync desktop, mobile and admin frontends"
# Vite hashes asset filenames. Preserve prior chunks while clients revalidate
# index.html, so an old document cannot reference an already-deleted chunk.
rsync -a --checksum "$SOURCE_DIR/frontend/dist/" "$FRONTEND_DIR/dist/"
test -f "$FRONTEND_DIR/dist/index.html"
while IFS= read -r asset; do
  test -f "$FRONTEND_DIR/dist${asset}"
done < <(grep -oE '/assets/[^" ]+\.(js|css)' "$FRONTEND_DIR/dist/index.html")
rsync -a --checksum --delete "$SOURCE_DIR/mobile/dist/" "$MOBILE_DIR/dist/"
test -f "$MOBILE_DIR/dist/index.html"
while IFS= read -r asset; do
  test -f "$MOBILE_DIR/dist${asset#/m}"
done < <(grep -oE '/m/assets/[^" ]+\.(js|css)' "$MOBILE_DIR/dist/index.html")
if [ -d "$SOURCE_DIR/admin/dist" ]; then
  rsync -a --checksum --delete "$SOURCE_DIR/admin/dist/" "$ADMIN_DIR/dist/"
fi

echo "[5/9] Sync course knowledge corpus"
if [ -d "$SOURCE_DIR/rag文档" ]; then
  mkdir -p "$PROJECT_DIR/rag文档"
  rsync -a --delete "$SOURCE_DIR/rag文档/" "$PROJECT_DIR/rag文档/"
fi

echo "[6/9] Sync PPT H5 assets"
if [ -d "$SOURCE_DIR/ppth5/backend" ]; then
  rsync -a --checksum --delete --exclude ".venv/" --exclude "__pycache__/" --exclude ".env" "$SOURCE_DIR/ppth5/backend/" "$PPTAGENT_DIR/backend/"
fi
if [ -d "$SOURCE_DIR/ppth5/dist-web" ]; then
  rsync -a --checksum --delete "$SOURCE_DIR/ppth5/dist-web/" "$FRONTEND_DIR/dist/ppt/"
elif [ -d "$SOURCE_DIR/frontend/dist/ppt" ]; then
  rsync -a --checksum --delete "$SOURCE_DIR/frontend/dist/ppt/" "$FRONTEND_DIR/dist/ppt/"
fi
if [ -f "$SOURCE_DIR/ppth5/ohmyppt.dev.db" ]; then
  cp -f "$SOURCE_DIR/ppth5/ohmyppt.dev.db" "$PPTH5_DIR/ohmyppt.dev.db"
fi
if [ -d "$SOURCE_DIR/ppth5/resources" ]; then
  rsync -a --checksum --delete "$SOURCE_DIR/ppth5/resources/" "$PPTH5_DIR/resources/"
fi

echo "[7/9] Prepare PPT H5 API runtime"
if [ -f "$PPTAGENT_DIR/backend/requirements.txt" ]; then
  cd "$PPTAGENT_DIR/backend"
  if [ ! -x .venv/bin/python ] || ! .venv/bin/python -c 'import sys; raise SystemExit(sys.version_info[:2] != (3, 12))'; then
    rm -rf .venv
    "$UV_BIN" venv --python 3.12 .venv
  fi
  "$UV_BIN" pip install --python .venv/bin/python -r requirements.txt
fi

echo "[8/9] Configure nginx and systemd"
cat > /etc/nginx/sites-available/lzhan.xyz <<'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name lzhan.xyz www.lzhan.xyz;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    http2 on;
    server_name lzhan.xyz www.lzhan.xyz;

    root /var/www/feishengwangying/frontend/dist;
    index index.html;

    location = /index.html {
        try_files /index.html =404;
        add_header Cache-Control "no-cache, no-store, must-revalidate" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    }

    ssl_certificate /etc/nginx/ssl/lzhan.xyz/lzhan.xyz.pem;
    ssl_certificate_key /etc/nginx/ssl/lzhan.xyz/lzhan.xyz.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_cache shared:LzhanSSL:10m;
    ssl_session_timeout 1d;
    client_max_body_size 256m;

    location /ppt-api/ {
        proxy_pass http://127.0.0.1:8765/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 660s;
        proxy_send_timeout 660s;
        client_max_body_size 256m;
        proxy_buffering off;
    }

    location /api {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 660s;
        proxy_send_timeout 660s;
        client_max_body_size 256m;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
        proxy_buffering off;
        proxy_cache off;
    }

    location ~ ^/(api-bili|api-cover|api-mimo) {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 660s;
        proxy_send_timeout 660s;
        proxy_buffering off;
    }

    location = /m {
        return 301 /m/;
    }

    location ^~ /m/ {
        alias /var/www/feishengwangying/mobile/dist/;
        index index.html;
        try_files $uri $uri/ /m/index.html;
        add_header Cache-Control "no-cache, no-store, must-revalidate" always;
    }

    location = /admin {
        return 301 /admin/;
    }

    location = /admin/index.html {
        alias /var/www/feishengwangying/admin/dist/index.html;
        add_header Cache-Control "no-cache, no-store, must-revalidate" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    }

    location ^~ /admin/assets/ {
        alias /var/www/feishengwangying/admin/dist/assets/;
        add_header Cache-Control "public, max-age=31536000, immutable" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    }

    location ^~ /admin/ {
        alias /var/www/feishengwangying/admin/dist/;
        index index.html;
        try_files $uri $uri/ /admin/index.html;
        add_header Cache-Control "no-cache, no-store, must-revalidate" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    }

    location = /ppt {
        return 301 /ppt/;
    }

    location = /ppt/ {
        try_files /ppt/index.html =404;
        add_header Cache-Control "no-cache, no-store, must-revalidate" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    }

    location = /ppt/index.html {
        try_files /ppt/index.html =404;
        add_header Cache-Control "no-cache, no-store, must-revalidate" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    }

    location ^~ /ppt/ {
        alias /var/www/feishengwangying/frontend/dist/ppt/;
        index index.html;
        try_files $uri $uri/ /ppt/index.html;
    }

    location /neuroguard-media {
        alias /var/www/neuroguard-media;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location ^~ /assets/ {
        try_files $uri =404;
        add_header Cache-Control "public, max-age=31536000, immutable" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    }

    location ~* \.(png|jpg|jpeg|webp|avif|gif|ico|svg|woff|woff2|ttf|eot)$ {
        try_files $uri =404;
        add_header Cache-Control "public, max-age=604800" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    }

    location / {
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "no-cache, no-store, must-revalidate" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    }

    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

}
EOF

ln -sfn /etc/nginx/sites-available/lzhan.xyz /etc/nginx/sites-enabled/lzhan.xyz
rm -f /etc/nginx/sites-enabled/feishengwangying
nginx -t

cat > /etc/systemd/system/feishengwangying-backend.service <<EOF
[Unit]
Description=FeishengWangYing Backend API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$BACKEND_DIR/venv/bin"
Environment="MALLOC_ARENA_MAX=2"
Environment="OMP_NUM_THREADS=1"
Environment="OPENBLAS_NUM_THREADS=1"
Environment="MKL_NUM_THREADS=1"
ExecStart=$BACKEND_DIR/venv/bin/gunicorn --workers 1 --worker-class gthread --threads 4 --bind 127.0.0.1:3000 --timeout 300 --graceful-timeout 120 --keep-alive 5 app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/feishengwangying-pptapi.service <<EOF
[Unit]
Description=FeishengWangYing PPT H5 API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$PPTAGENT_DIR/backend
Environment="PATH=$PPTAGENT_DIR/backend/.venv/bin"
ExecStart=$PPTAGENT_DIR/backend/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8765
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable feishengwangying-backend
systemctl enable feishengwangying-pptapi
systemctl restart feishengwangying-backend
systemctl restart feishengwangying-pptapi
systemctl reload nginx

echo "[9/9] Verify services"
wait_for_url() {
  local url="$1"
  local attempts="${2:-60}"
  local delay="${3:-2}"
  for ((attempt = 1; attempt <= attempts; attempt++)); do
    if curl --noproxy '*' -fsS --max-time 10 "$url" >/dev/null; then
      return 0
    fi
    sleep "$delay"
  done
  echo "ERROR: health check failed: $url" >&2
  return 1
}

wait_for_url http://127.0.0.1:3000/api/health
curl --noproxy '*' -fsS http://127.0.0.1:3000/api/health
echo
wait_for_url http://127.0.0.1:8765/api/health
curl --noproxy '*' -fsS http://127.0.0.1:8765/api/health
echo
curl --noproxy '*' --resolve lzhan.xyz:443:127.0.0.1 -fsS https://lzhan.xyz/ >/dev/null
curl --noproxy '*' --resolve lzhan.xyz:443:127.0.0.1 -fsSI https://lzhan.xyz/m/ >/dev/null
curl --noproxy '*' --resolve lzhan.xyz:443:127.0.0.1 -fsS https://lzhan.xyz/api/health >/dev/null
curl --noproxy '*' --resolve lzhan.xyz:443:127.0.0.1 -fsS https://lzhan.xyz/ppt-api/health >/dev/null
curl --noproxy '*' --resolve lzhan.xyz:443:127.0.0.1 -fsSI https://lzhan.xyz/admin/ >/dev/null
curl --noproxy '*' --resolve lzhan.xyz:443:127.0.0.1 -fsSI https://lzhan.xyz/ppt/ >/dev/null
echo "Deploy complete: https://lzhan.xyz"
