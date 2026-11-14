"""Run isolated local services with the packaged runtimes; no system installation."""
from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

from dotenv import dotenv_values
from importlib.util import module_from_spec, spec_from_file_location

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / '.local-system'
APP = STATE / 'app'
BACKEND = APP / 'backend'
PUBLIC_DATA = {
    'course_knowledge_index.json', 'course_knowledge_index_catalog.json',
    'tcm_graph_index.json', 'tcm_hybrid_corpus.db.gz',
    'tcm_hybrid_corpus_manifest.json', 'tcm_qa_pairs.json',
}


def copy_if_changed(source: Path, target: Path) -> None:
    if target.exists() and target.stat().st_size == source.stat().st_size and target.stat().st_mtime_ns == source.stat().st_mtime_ns:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def prepare() -> dict:
    STATE.mkdir(exist_ok=True)
    BACKEND.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'backend'
    for directory, dirs, files in os.walk(source):
        dirs[:] = [name for name in dirs if name not in {'data', 'generated', 'uploads', 'backups', 'tests', '__pycache__', 'venv', '.venv', 'node_modules'}]
        for name in files:
            file = Path(directory) / name
            if file.suffix not in {'.py', '.json', '.yaml', '.yml', '.pt', '.csv', '.txt', '.mmd', '.toml'}:
                continue
            copy_if_changed(file, BACKEND / file.relative_to(source))
    for name in PUBLIC_DATA:
        file = source / 'data' / name
        if file.is_file():
            copy_if_changed(file, BACKEND / 'data' / name)
    # Public static files keep their ordinary project-relative paths. Junctions
    # need no administrator rights; copying is a fallback on other filesystems.
    for name in ['frontend', 'admin', 'img', 'ppth5', 'rag文档']:
        source_dir, target = ROOT / name, APP / name
        if not source_dir.is_dir() or target.exists():
            continue
        if os.name == 'nt':
            result = subprocess.run([os.environ.get('COMSPEC', 'cmd.exe'), '/d', '/c', 'mklink', '/J', str(target), str(source_dir)], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode == 0:
                continue
        shutil.copytree(source_dir, target, ignore=shutil.ignore_patterns('node_modules', '__pycache__', '.env', '*.log'))
    account_file = STATE / 'local-account.json'
    if account_file.exists():
        account = json.loads(account_file.read_text(encoding='utf-8'))
    else:
        account = {'username': 'localadmin', 'password': secrets.token_urlsafe(14)}
        account_file.write_text(json.dumps(account, ensure_ascii=False, indent=2), encoding='utf-8')
        (ROOT / '本地登录账号.txt').write_text('仅用于本机纯本地模式\n账号：' + account['username'] + '\n密码：' + account['password'] + '\n数据库与设置保存在 .local-system，请勿删除或覆盖。\n', encoding='utf-8-sig')
    return account


def free_port(preferred: int) -> int:
    for candidate in range(preferred, preferred + 30):
        with socket.socket() as sock:
            try:
                sock.bind(('127.0.0.1', candidate))
                return candidate
            except OSError:
                pass
    raise RuntimeError('No available local port; close unused application instances.')


def read_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=2) as response:
        return json.load(response)


def wait_ready(process: subprocess.Popen, url: str, label: str) -> None:
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(label + ' stopped. See .local-system/logs for details.')
        try:
            read_json(url)
            return
        except (OSError, ValueError, urllib.error.URLError):
            time.sleep(.4)
    raise RuntimeError(label + ' did not become ready. See .local-system/logs.')


def request_browser(port: int) -> None:
    if os.getenv('BENCAO_NO_BROWSER') != '1':
        subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT / 'scripts/open-browser.ps1'), '-Url', f'http://127.0.0.1:{port}/login'], check=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))


def main() -> None:
    node = ROOT / '.runtime/node/node.exe'
    if not node.is_file():
        raise RuntimeError('The bundled Node runtime is missing. Extract the complete delivery ZIP.')
    state_file = STATE / 'services.json'
    if state_file.exists():
        try:
            previous = json.loads(state_file.read_text(encoding='utf-8'))
            status = read_json(f"http://127.0.0.1:{previous['frontendPort']}/__launcher/status")
            if status.get('mode') == 'local-full-stack' and Path(status.get('projectRoot', '')).resolve() == ROOT:
                read_json(status['backend'] + '/api/health')
                print(f"Local system already running: http://127.0.0.1:{previous['frontendPort']}/login", flush=True)
                request_browser(previous['frontendPort'])
                return
        except (OSError, ValueError, KeyError, urllib.error.URLError):
            pass
    print('Preparing the independent local database and services...', flush=True)
    resource_spec = spec_from_file_location('local_support', ROOT / 'scripts/prepare-local-assets.py')
    resource_module = module_from_spec(resource_spec)
    resource_spec.loader.exec_module(resource_module)
    resource_module.prepare_local_assets(ROOT)
    account = prepare()
    frontend = free_port(int(os.getenv('LOCAL_FRONTEND_PORT', '5089')))
    backend = free_port(int(os.getenv('LOCAL_BACKEND_PORT', '5091')))
    ppt = free_port(int(os.getenv('LOCAL_PPT_PORT', '5095')))
    while backend == frontend:
        backend = free_port(backend + 1)
    while ppt in {frontend, backend}:
        ppt = free_port(ppt + 1)
    env = dict(os.environ)
    private = {key: value for key, value in dotenv_values(ROOT / 'backend/.env').items() if value is not None}
    env.update(private)
    env.update({
        'PORT': str(backend), 'PORTABLE_HOST': '127.0.0.1', 'PYTHONUTF8': '1',
        'PYTHONIOENCODING': 'utf-8', 'PYTHONDONTWRITEBYTECODE': '1',
        'FRONTEND_ORIGIN': f'http://127.0.0.1:{frontend}',
        'ADMIN_USERNAME': account['username'], 'ADMIN_PASSWORD': account['password'],
        'OHMYPPT_API_URL': f'http://127.0.0.1:{ppt}/api',
        'PLATFORM_AUTH_ME_URL': f'http://127.0.0.1:{backend}/api/auth/me',
        'COURSE_KNOWLEDGE_CORPUS_DIR': str(ROOT / 'rag文档'),
        'YOLO_CONFIG_DIR': str(STATE / 'ultralytics'),
        'PATH': str(node.parent) + os.pathsep + str(Path(sys.executable).parent) + os.pathsep + env.get('PATH', ''),
    })
    for variable, filename in [('VIDEO_FFMPEG_PATH', 'ffmpeg.exe'), ('VIDEO_FFPROBE_PATH', 'ffprobe.exe')]:
        tool = ROOT / '.runtime/ffmpeg' / filename
        if tool.is_file():
            env[variable] = str(tool)
    logs = STATE / 'logs'
    logs.mkdir(exist_ok=True)
    children, handles = [], []
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

    def launch(args: list[str], cwd: Path, name: str, child_env: dict) -> subprocess.Popen:
        handle = (logs / (name + '.log')).open('ab')
        handles.append(handle)
        process = subprocess.Popen(args, cwd=cwd, env=child_env, stdout=handle, stderr=subprocess.STDOUT, creationflags=flags)
        children.append(process)
        return process

    try:
        ppt_service = launch([sys.executable, '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', str(ppt)], ROOT / 'ppth5/backend', 'ppt', env)
        wait_ready(ppt_service, f'http://127.0.0.1:{ppt}/api/health', 'PPT service')
        app = launch([sys.executable, str(BACKEND / 'portable_server.py')], BACKEND, 'backend', env)
        wait_ready(app, f'http://127.0.0.1:{backend}/api/health', 'Local backend')
        front_env = dict(env, PORT=str(frontend), LOCAL_BACKEND_URL=f'http://127.0.0.1:{backend}')
        front_env.pop('REMOTE_BACKEND_URL', None)
        web = launch([str(node), str(ROOT / 'scripts/local-web.mjs')], ROOT, 'frontend', front_env)
        wait_ready(web, f'http://127.0.0.1:{frontend}/__launcher/status', 'Local frontend')
        state_file.write_text(json.dumps({'frontendPort': frontend, 'backendPort': backend, 'pptPort': ppt, 'pids': [p.pid for p in children]}, indent=2), encoding='utf-8')
        print(f'Local system: http://127.0.0.1:{frontend}/login\nAdmin: http://127.0.0.1:{frontend}/admin/dashboard\nAccount: see 本地登录账号.txt\nDatabase: {BACKEND / "data"}\nKeep this window open. Press Ctrl+C to stop all local services.', flush=True)
        request_browser(frontend)
        while all(process.poll() is None for process in children):
            time.sleep(.5)
        raise RuntimeError('A local service stopped; see .local-system/logs.')
    except KeyboardInterrupt:
        print('Stopping local services...', flush=True)
    finally:
        for process in reversed(children):
            if process.poll() is None:
                process.terminate()
        for process in reversed(children):
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
        for handle in handles:
            handle.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Startup failed: ' + str(error), file=sys.stderr, flush=True)
        raise SystemExit(1)
