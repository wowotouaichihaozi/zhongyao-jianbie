import json
from pathlib import Path
import stat
import subprocess
import sys
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXTRACTOR = (
    PROJECT_ROOT
    / "deploy"
    / "deepseek-harness"
    / "workspace"
    / ".agents"
    / "skills"
    / "safe-archive-workspace"
    / "scripts"
    / "safe_extract_zip.py"
)
PLUGIN_HOST = (
    PROJECT_ROOT
    / "deploy"
    / "deepseek-harness"
    / "plugins"
    / "dsh-attachment-upload"
    / "lib"
    / "index.js"
)
NGINX_CONFIG = PROJECT_ROOT / "deploy" / "nginx" / "ai-coding-runtime.conf"


def run_extractor(archive: Path, destination: Path):
    completed = subprocess.run(
        [sys.executable, str(EXTRACTOR), str(archive), str(destination)],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed, json.loads(completed.stdout)


def test_safe_zip_extracts_regular_files(tmp_path):
    archive = tmp_path / "project.zip"
    destination = tmp_path / "output"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("src/main.c", "int main(void) { return 0; }\n")
        bundle.writestr("README.md", "# demo\n")

    completed, payload = run_extractor(archive, destination)

    assert completed.returncode == 0
    assert payload == {"ok": True, "entries": 2, "totalBytes": 36}
    assert (destination / "src" / "main.c").read_text(encoding="utf-8").startswith("int main")


def test_safe_zip_rejects_parent_traversal(tmp_path):
    archive = tmp_path / "traversal.zip"
    destination = tmp_path / "output"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("../outside.txt", "blocked")

    completed, payload = run_extractor(archive, destination)

    assert completed.returncode == 1
    assert payload["ok"] is False
    assert "unsafe archive path" in payload["error"]
    assert not (tmp_path / "outside.txt").exists()


def test_safe_zip_rejects_symbolic_links(tmp_path):
    archive = tmp_path / "link.zip"
    destination = tmp_path / "output"
    link = zipfile.ZipInfo("link")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(link, "/etc/passwd")

    completed, payload = run_extractor(archive, destination)

    assert completed.returncode == 1
    assert payload["ok"] is False
    assert "symbolic link" in payload["error"]


def test_safe_zip_rejects_suspicious_compression_ratio(tmp_path):
    archive = tmp_path / "compressed.zip"
    destination = tmp_path / "output"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("zeros.bin", b"\0" * (2 * 1024 * 1024))

    completed, payload = run_extractor(archive, destination)

    assert completed.returncode == 1
    assert payload["ok"] is False
    assert "compression ratio" in payload["error"]


def test_upload_plugin_uses_fixed_workspace_and_authenticated_proxy():
    plugin_source = PLUGIN_HOST.read_text(encoding="utf-8")
    nginx_source = NGINX_CONFIG.read_text(encoding="utf-8")

    assert "DSH_FILE_UPLOAD_ROOT" in plugin_source
    assert "x-cwd" not in plugin_source
    assert "location = /_dsh/attachment-upload/upload" in nginx_source
    assert "auth_request /_ai_coding_auth;" in nginx_source
    assert "client_max_body_size 64m;" in nginx_source
    assert "header:has(nav[aria-label=\"会话层级\"])" in nginx_source
