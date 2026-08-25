from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_HOST = "120.26.3.150"
LEGACY_HOST = "47.103.155.248"


def read_project_file(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_deploy_entrypoint_uses_the_canonical_production_script():
    deploy_entrypoint = read_project_file("deploy.sh")

    assert 'exec bash "$SCRIPT_DIR/deploy-prod.sh"' in deploy_entrypoint
    assert "gunicorn" not in deploy_entrypoint
    assert "ssl_certificate" not in deploy_entrypoint


def test_production_script_is_tuned_for_the_low_memory_host():
    deploy_script = read_project_file("deploy-prod.sh")

    assert "--workers 1 --worker-class gthread --threads 4" in deploy_script
    assert "--workers 2" not in deploy_script
    assert "gunicorn -w 4" not in deploy_script
    assert "swapon --noheadings --show=NAME" in deploy_script
    assert 'Environment="OMP_NUM_THREADS=1"' in deploy_script
    assert '"uv==0.8.14"' in deploy_script
    assert '"$UV_BIN" venv --python 3.12 venv' in deploy_script
    assert '"$UV_BIN" venv --python 3.12 .venv' in deploy_script
    assert '"$SOURCE_DIR/backend/data/course_knowledge_index.json"' in deploy_script
    assert '"$BACKEND_DIR/data/course_knowledge_index.json"' in deploy_script
    assert 'rsync -a --checksum "$SOURCE_DIR/frontend/dist/"' in deploy_script
    assert 'rsync -a --checksum --delete "$SOURCE_DIR/ppth5/dist-web/"' in deploy_script


def test_production_script_requires_the_external_digicert_files():
    deploy_script = read_project_file("deploy-prod.sh")

    assert "/etc/nginx/ssl/lzhan.xyz/lzhan.xyz.pem" in deploy_script
    assert "/etc/nginx/ssl/lzhan.xyz/lzhan.xyz.key" in deploy_script
    assert "/etc/letsencrypt/live/lzhan" not in deploy_script
    assert "server_name lzhan.xyz www.lzhan.xyz" in deploy_script


def test_backend_defaults_target_the_new_production_host():
    api_config = read_project_file("backend/api_config.py")
    app_source = read_project_file("backend/app.py")

    assert f'"REMOTE_UPLOAD_HOST": "{PRODUCTION_HOST}"' in api_config
    assert PRODUCTION_HOST in api_config
    assert PRODUCTION_HOST in app_source
    assert LEGACY_HOST not in api_config
    assert LEGACY_HOST not in app_source


def test_production_script_serves_desktop_and_mobile_with_safe_cache_rules():
    deploy_script = read_project_file("deploy-prod.sh")

    assert 'MOBILE_DIR="$PROJECT_DIR/mobile"' in deploy_script
    assert 'rsync -a --checksum --delete "$SOURCE_DIR/mobile/dist/" "$MOBILE_DIR/dist/"' in deploy_script
    assert "location = /m {" in deploy_script
    assert "return 301 /m/;" in deploy_script
    assert "location ^~ /m/ {" in deploy_script
    assert "alias /var/www/feishengwangying/mobile/dist/;" in deploy_script
    assert "try_files $uri $uri/ /m/index.html;" in deploy_script
    assert "location /api {" in deploy_script
    assert "location /ppt-api/ {" in deploy_script
    assert "location ^~ /assets/ {" in deploy_script
    assert 'add_header Cache-Control "public, max-age=31536000, immutable" always;' in deploy_script
    assert 'add_header Cache-Control "public, max-age=604800" always;' in deploy_script
    assert "location / {" in deploy_script
    assert "try_files $uri $uri/ /index.html;" in deploy_script
    assert 'add_header Cache-Control "no-cache, no-store, must-revalidate" always;' in deploy_script
    assert 'return 503 "Web frontend temporarily offline\\n";' not in deploy_script


def test_production_package_contains_mobile_build():
    package_builder = read_project_file("scripts/build_production_package.py")

    assert '"mobile/dist/index.html"' in package_builder
    assert 'iter_tree("mobile/dist", include_frontend_dist)' in package_builder


def test_ai_coding_proxy_forwards_command_menu_rpc_only_through_auth():
    nginx_config = read_project_file("deploy/nginx/ai-coding-runtime.conf")

    assert "commands/(list|execute)" in nginx_config
    assert "auth_request /_ai_coding_auth;" in nginx_config
    assert "location /api/" not in nginx_config
