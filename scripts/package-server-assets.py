"""Build a code-and-Node delivery whose data and media stay on the server."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import zipfile


CODE_SUFFIXES = {'.py', '.js', '.mjs', '.cjs', '.ts', '.tsx', '.vue', '.css', '.scss', '.sass', '.less', '.html', '.json', '.yaml', '.yml', '.toml', '.sql', '.txt', '.xml', '.gradle', '.properties', '.md', '.svg', '.java', '.kt', '.kts'}
SKIP_DIRS = {'node_modules', '.git', '__pycache__', '.runtime', '.local-system', '.local-web', '.test-artifacts', 'venv', '.venv', 'dist', 'dist-web', 'build', '.gradle', 'releases', '.cache'}
RUNTIME_SCRIPTS = ['local-web.mjs', 'start-remote.ps1', 'open-browser.ps1', 'package-server-assets.py', 'check-login-layout.mjs', 'check-login-landscape.mjs', 'check-admin-layout.mjs']
STATIC_SUFFIXES = {'.html', '.js', '.mjs', '.css', '.json', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.otf', '.eot', '.wasm', '.gltf', '.glb', '.obj', '.mtl', '.bin', '.hdr', '.ktx', '.ktx2', '.dds', '.vert', '.frag', '.glsl'}


def assets_for(index: Path, public_prefix: str = '') -> set[Path]:
    root = index.parent.resolve()
    todo, seen = [index.resolve()], set()
    references = re.compile(r'''["'`]([^"'`\s<>]+?\.(?:js|mjs|css)(?:\?[^"'`\s<>]*)?)["'`]''')
    while todo:
        file = todo.pop()
        if file in seen or not file.is_file():
            continue
        seen.add(file)
        text = file.read_text(encoding='utf-8', errors='ignore')
        for match in references.finditer(text):
            name = match[1].split('?', 1)[0]
            if name.startswith(('http:', 'https:', '//', 'data:')):
                continue
            if public_prefix and name.startswith(public_prefix + '/'):
                name = name[len(public_prefix):]
            for target in [(root / name.lstrip('/')).resolve(), (file.parent / name).resolve()]:
                if target.is_relative_to(root) and target.is_file() and target not in seen:
                    todo.append(target)
    return seen


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--static-cache', action='store_true', help='Include public browser images/fonts/3D and static apps, with local-first serving.')
    parser.add_argument('--backend-check', action='store_true', help='Include the optional Python archive for source/dependency checks, not a local business server.')
    parser.add_argument('--local-backend', action='store_true', default=True, help='Include the local frontend/backend entry with an independent database.')
    parser.add_argument('--private-api-config', action='store_true', help='Include backend/.env only in the private delivery, never in the Git source commit.')
    args = parser.parse_args()
    project, output = args.project.resolve(), args.output.resolve()
    assert re.fullmatch(r'[0-9a-f]{40}', args.commit), 'Supply the reviewed source commit.'
    assert not output.exists(), 'Choose a new output filename.'
    stage = output.parent / (output.stem + '-内容') / '网页前后端源码'
    assert not stage.exists(), 'Choose a new staging directory.'
    stage.mkdir(parents=True)

    def copy(name: str) -> None:
        source = project / name
        assert source.is_file(), 'Missing file: ' + name
        target = stage / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    for directory in ['backend', 'frontend', 'admin', 'ppth5', 'mobile', 'microprogram', 'img', 'rag文档']:
        source = project / directory
        if not source.exists():
            continue
        for current, dirs, files in os.walk(source):
            parent = Path(current).relative_to(project)
            dirs[:] = [name for name in dirs if name not in SKIP_DIRS and not (parent.as_posix() == 'backend' and name in {'data', 'models', 'uploads', 'generated', 'backups'}) and not (parent.as_posix() == 'admin' and name == 'assets')]
            for name in files:
                file = Path(current) / name
                if name.startswith('.env'):
                    if name != '.env.example':
                        continue
                elif file.suffix.lower() not in CODE_SUFFIXES and not name.upper().startswith(('LICENSE', 'LICENCE', 'NOTICE')):
                    continue
                copy(file.relative_to(project).as_posix())

    for directory, prefix in [('frontend/dist', ''), ('admin/dist', '/admin')]:
        for file in assets_for(project / directory / 'index.html', prefix):
            copy(file.relative_to(project).as_posix())
    if args.static_cache:
        for directory in ['frontend/dist', 'admin/dist']:
            static_root = project / directory
            for current, dirs, files in os.walk(static_root):
                dirs[:] = [name for name in dirs if name not in {'node_modules', '__pycache__', 'uploads', 'generated', 'private', 'backups', 'data'}]
                for name in files:
                    file = Path(current) / name
                    relative = file.relative_to(static_root)
                    if file.suffix.lower() not in STATIC_SUFFIXES or re.search(r'backup|\.bak\b|\.old\b', name, re.I):
                        continue
                    if relative.parts[0] == 'assets' and file.suffix.lower() in {'.js', '.mjs', '.css'}:
                        continue  # Already copied the active dependency graph, not historical bundles.
                    copy(file.relative_to(project).as_posix())
    # Login documents are editable frontend code and must remain same-origin.
    for file in (project / 'frontend/dist/archify').rglob('*'):
        if file.is_file() and file.suffix.lower() in {'.html', '.js', '.mjs', '.css'}:
            copy(file.relative_to(project).as_posix())
    for file in (project / 'frontend').glob('local-*'):
        if file.is_file() and file.suffix in {'.mjs', '.css'}:
            copy(file.relative_to(project).as_posix())
    for name in RUNTIME_SCRIPTS:
        copy('scripts/' + name)
    for name in ['remote-backend.json', '启动本地前端_连接服务器后端.cmd', 'admin/local-admin.css', '.runtime/node/node.exe', '.runtime/node/LICENSE']:
        copy(name)
    config_file = stage / 'remote-backend.json'
    config = json.loads(config_file.read_text(encoding='utf-8'))
    config['preferLocalStatic'] = bool(args.static_cache)
    config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    if args.backend_check or args.local_backend:
        for name in ['scripts/ensure-local-runtime.ps1', 'scripts/windows-runtime-lock.txt', '.runtime/python-win64.zip', '.runtime/python-win64.zip.sha256']:
            copy(name)
    if args.backend_check:
        for name in ['scripts/check-backend.ps1', 'scripts/check-backend-code.py']:
            copy(name)
    if args.local_backend:
        for name in ['启动本地前后端.cmd', 'scripts/start-local.ps1', 'scripts/start-local-system.py', 'scripts/prepare-local-assets.py', 'scripts/local-assets.json']:
            copy(name)
    if args.private_api_config:
        assert args.local_backend, 'Private model configuration is only needed for the local backend mode.'
        # The private delivery needs provider APIs, never server login credentials.
        excluded = re.compile(r'^(?:ADMIN_|REMOTE_UPLOAD_|GITHUB_|SYNC_SSH_|SSH_)')
        lines = []
        for line in (project / 'backend/.env').read_text(encoding='utf-8-sig').splitlines():
            match = re.match(r'\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=', line)
            if match and excluded.match(match[1]):
                continue
            lines.append(line)
        (stage / 'backend/.env').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    if (project / 'THIRD_PARTY_NOTICES.md').exists():
        copy('THIRD_PARTY_NOTICES.md')
    if (project / '.gitignore').exists():
        copy('.gitignore')

    cache_notes = '常用图片、字体、药材 3D 展示素材和数字孪生/PPT 静态应用已缓存本地，优先读本地文件；缺失时再从服务器补充。' if args.static_cache else '数字孪生/PPT 静态应用和媒体通过服务器加载，本地只保留主要页面代码。'
    dependency_notes = '已内置 Python 与后端依赖，本地前后端模式会自动准备运行环境。连接服务器模式只使用 Node，不启动本地后端。' if args.local_backend else '后端校验工具在 scripts 内，不提供额外根目录入口。'
    local_notes = '“启动本地前后端.cmd”：启动真正的本地前端、业务后端及 PPT 服务，首次自动初始化独立 SQLite 数据库。账号在首次生成的“本地登录账号.txt”内。与线上账号和数据分开，不复制线上用户记录。首次需联网自动下载约 173 MB 的公共知识语料、识别模型和媒体运行工具，进度会显示在窗口中；校验完成后复用本地资源。AI、数字人及媒体供应商仍通过网络 API 工作。' if args.local_backend else ''
    api_notes = '本私有包中的 backend/.env 提供必要模型/媒体 API 配置，不提交 Git；不包含 GitHub 令牌、SSH 密码或线上用户数据库。' if args.private_api_config else '模型供应商密钥留在服务器，本包不含私钥。'

    notes = f'''# 项目来源与服务器资源版启动说明

Git 仓库：https://github.com/wowotouaichihaozi/zhongyao-jianbie
提交版本：{args.commit}
提交链接：https://github.com/wowotouaichihaozi/zhongyao-jianbie/commit/{args.commit}
线上访问：https://lzhan.xyz

## 启动

根目录只保留两个启动入口。在 Windows 10/11 x64 上完整解压后按需要选择：

1. “启动本地前端_连接服务器后端.cmd”：只启动本地前端，使用线上后端、数据库、账号和知识网络。
2. {local_notes}

已内置运行依赖，无需手动安装 Node、Python 或数据库。默认浏览器会自动打开；端口被占用时自动选择后续端口，以启动窗口显示的网址为准。运行期间保持窗口打开，按 Ctrl+C 停止本地服务。

连接服务器模式不初始化本地业务数据库。启动本地前后端时，独立业务数据放在 .local-system/app/backend/data；请保留 .local-system 与本地账号文件，以保存自己的数据。两个模式可以共存，使用各自启动窗口中的地址。接口地址在 remote-backend.json。{api_notes}

## 文件

- frontend/dist、admin/dist：实际运行的主要页面 JS/CSS/HTML。
- frontend/src、admin/src、backend、ppth5 等：保留的源码与依赖声明。
- scripts：启动、网关、打包及开发检查代码。
- .runtime/node：一键启动所需的 Node 与许可证。

{cache_notes} 连接服务器模式的业务接口请求服务器；本地前后端模式的业务接口请求独立本地后端。源码和修改后的主要页面代码保存在包内。开发重建涉及其他公共资源时仍需连接服务器。

{dependency_notes}

本包不预装运行产生的业务数据库、不带线上用户记录或旧 APK。本地模式所需的公共语料、模型及媒体工具首次自动获取，避免反复扩大压缩包。3D 网格与纹理是公开展示素材，不是后端识别模型。
'''
    for name in ['README.md', '项目来源与启动说明.md']:
        (stage / name).write_text(notes, encoding='utf-8')
    files = sorted(file for file in stage.rglob('*') if file.is_file())
    manifest = {'commit': args.commit, 'modes': ['remote-backend', 'local-full-stack'] if args.local_backend else ['remote-backend'], 'backend': config['backend'], 'containsBusinessDatabase': False, 'localModeUsesIndependentData': bool(args.local_backend), 'publicStaticCache': bool(args.static_cache), 'pythonRuntimeIncluded': bool(args.local_backend or args.backend_check), 'privateApiConfiguration': 'backend/.env' if args.private_api_config else None, 'nodeSha256': hashlib.file_digest((stage / '.runtime/node/node.exe').open('rb'), 'sha256').hexdigest(), 'files': len(files) + 1}
    (stage / '交付清单.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
        for file in sorted(stage.rglob('*')):
            if file.is_file():
                archive.write(file, '网页前后端源码/' + file.relative_to(stage).as_posix(), compress_type=zipfile.ZIP_STORED if file.suffix == '.zip' else zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        assert not any(name.endswith(('.db', '.sqlite3', '.sqlite', '.pt', '.onnx', '.apk')) for name in archive.namelist())
        assert [name for name in archive.namelist() if name.endswith('/.env')] == (['网页前后端源码/backend/.env'] if args.private_api_config else [])
        entries = {Path(name).name for name in archive.namelist() if len(Path(name).parts) == 2 and name.endswith('.cmd')}
        expected_entries = {'启动本地前端_连接服务器后端.cmd'} | ({'启动本地前后端.cmd'} if args.local_backend else set())
        assert entries == expected_entries, entries
    result = {'package': str(output), 'stage': str(stage), 'commit': args.commit, 'bytes': output.stat().st_size, 'sha256': hashlib.file_digest(output.open('rb'), 'sha256').hexdigest(), 'files': manifest['files']}
    output.with_suffix('.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    output.with_suffix('.sha256.txt').write_text(result['sha256'] + '  ' + output.name + '\n', encoding='utf-8')
    print(json.dumps({'files': manifest['files'], 'MB': round(result['bytes'] / 1048576, 1), 'crcVerified': True}), flush=True)


if __name__ == '__main__':
    main()
