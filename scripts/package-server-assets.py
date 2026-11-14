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

    for directory in ['backend', 'frontend', 'admin', 'ppth5', 'mobile', 'microprogram', 'img']:
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
    for name in ['remote-backend.json', '启动网页.cmd', '启动本地前端_连接服务器.cmd', 'admin/local-admin.css', '.runtime/node/node.exe', '.runtime/node/LICENSE']:
        copy(name)
    config_file = stage / 'remote-backend.json'
    config = json.loads(config_file.read_text(encoding='utf-8'))
    config['preferLocalStatic'] = bool(args.static_cache)
    config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    if args.backend_check:
        for name in ['检查后端代码与依赖.cmd', 'scripts/check-backend.ps1', 'scripts/check-backend-code.py', 'scripts/ensure-local-runtime.ps1', 'scripts/windows-runtime-lock.txt', '.runtime/python-win64.zip', '.runtime/python-win64.zip.sha256']:
            copy(name)
    if (project / 'THIRD_PARTY_NOTICES.md').exists():
        copy('THIRD_PARTY_NOTICES.md')
    if (project / '.gitignore').exists():
        copy('.gitignore')

    cache_notes = '常用图片、字体、药材 3D 展示素材和数字孪生/PPT 静态应用已缓存本地，优先读本地文件；缺失时再从服务器补充。' if args.static_cache else '数字孪生/PPT 静态应用和媒体通过服务器加载，本地只保留主要页面代码。'
    dependency_notes = '另附后端 Python/CPU 依赖，用于“检查后端代码与依赖.cmd”。检查只编译源码、导入依赖，不启动后端、不初始化业务数据库。日常网页启动只使用 Node，无需展开 Python。检查结果在 .backend-check/result.json。' if args.backend_check else '不携带本地 Python/推理环境。'

    notes = f'''# 项目来源与服务器资源版启动说明

Git 仓库：https://github.com/wowotouaichihaozi/zhongyao-jianbie
提交版本：{args.commit}
提交链接：https://github.com/wowotouaichihaozi/zhongyao-jianbie/commit/{args.commit}
线上访问：https://lzhan.xyz

## 启动

在 Windows 10/11 x64 上完整解压后，双击“启动网页.cmd”或“启动本地前端_连接服务器.cmd”。已内置 Node，不需要安装 Node、Python、数据库或编译依赖。默认浏览器会自动打开；端口被其他副本占用时自动换用后续端口，以启动窗口显示的网址为准。运行期间保持窗口打开，按 Ctrl+C 停止。

本地只运行主要前端、管理端和同源网关，后端源码保留供查阅。用户数据库、知识库、药材识别模型、用户图片/视频、上传记录和 AI 生成均连接服务器。需要联网，使用线上账号登录，不初始化本地业务数据库，也不提供纯本地系统入口。接口地址在 remote-backend.json，模型供应商密钥留在服务器，包内无需保存私钥。

## 文件

- frontend/dist、admin/dist：实际运行的主要页面 JS/CSS/HTML。
- frontend/src、admin/src、backend、ppth5 等：保留的源码与依赖声明。
- scripts：启动、网关、打包及开发检查代码。
- .runtime/node：一键启动所需的 Node 与许可证。

{cache_notes} 动态业务接口始终请求服务器，静态缓存不会替代服务器数据库。源码和修改后的主要页面代码保存在包内。开发重建涉及其他公共资源时仍需连接服务器。

{dependency_notes}

本包不含 FFmpeg、业务数据库、知识语料、药材识别模型权重、旧 APK、API 私钥、GitHub 令牌或 SSH 密码。3D 网格与纹理是公开展示素材，不是后端识别模型。程序会产生正常浏览器缓存和登录状态，业务数据以服务器为准。
'''
    for name in ['README.md', '项目来源与启动说明.md']:
        (stage / name).write_text(notes, encoding='utf-8')
    files = sorted(file for file in stage.rglob('*') if file.is_file())
    manifest = {'commit': args.commit, 'mode': 'remote-backend', 'backend': config['backend'], 'localBusinessDatabase': False, 'serverKnowledgeAndAI': True, 'serverPrivateMedia': True, 'publicStaticCache': bool(args.static_cache), 'backendValidationRuntimeIncluded': bool(args.backend_check), 'privateCredentialsIncluded': False, 'nodeSha256': hashlib.file_digest((stage / '.runtime/node/node.exe').open('rb'), 'sha256').hexdigest(), 'files': len(files) + 1}
    (stage / '交付清单.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
        for file in sorted(stage.rglob('*')):
            if file.is_file():
                archive.write(file, '网页前后端源码/' + file.relative_to(stage).as_posix(), compress_type=zipfile.ZIP_STORED if file.suffix == '.zip' else zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        assert not any(name.endswith(('.db', '.sqlite3', '.sqlite', '.pt', '.onnx', '.apk', '.env')) for name in archive.namelist())
    result = {'package': str(output), 'stage': str(stage), 'commit': args.commit, 'bytes': output.stat().st_size, 'sha256': hashlib.file_digest(output.open('rb'), 'sha256').hexdigest(), 'files': manifest['files']}
    output.with_suffix('.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    output.with_suffix('.sha256.txt').write_text(result['sha256'] + '  ' + output.name + '\n', encoding='utf-8')
    print(json.dumps({'files': manifest['files'], 'MB': round(result['bytes'] / 1048576, 1), 'crcVerified': True}), flush=True)


if __name__ == '__main__':
    main()
