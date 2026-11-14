"""Prepare public local-service resources once, without copying online user data."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time
from urllib.parse import urlparse
import urllib.request
import zipfile


def prepare_local_assets(root: Path) -> None:
    manifest_path = root / 'scripts/local-assets.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    url, expected = manifest['url'], manifest['sha256']
    parsed = urlparse(url)
    backend = urlparse(json.loads((root / 'remote-backend.json').read_text(encoding='utf-8'))['backend'])
    if parsed.scheme != 'https' or parsed.hostname != backend.hostname or parsed.username or parsed.password:
        raise RuntimeError('Local resource download must use the configured HTTPS server.')
    state = root / '.local-support'
    state.mkdir(exist_ok=True)
    ready = state / ('ready-' + expected[:16] + '.json')

    def target(name: str) -> Path:
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or name.startswith(('/', '\\')):
            raise RuntimeError('Invalid local resource path.')
        return path

    if ready.is_file() and all(target(name).is_file() and target(name).stat().st_size == item['bytes'] for name, item in manifest['files'].items()):
        return
    archive = state / (expected + '.zip.part')
    total = manifest['bytes']
    print('Preparing local knowledge/model/media tools (first local launch only)...', flush=True)
    for attempt in range(3):
        try:
            offset = archive.stat().st_size if archive.exists() else 0
            if offset < total:
                headers = {'Range': f'bytes={offset}-'} if offset else {}
                with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=45) as response:
                    append = offset > 0 and response.status == 206
                    if not append:
                        offset = 0
                    updated = time.monotonic()
                    with archive.open('ab' if append else 'wb') as output:
                        while chunk := response.read(1024 * 1024):
                            output.write(chunk)
                            offset += len(chunk)
                            if time.monotonic() - updated > 1:
                                print(f'Local resources: {offset / 1048576:.0f}/{total / 1048576:.0f} MB', flush=True)
                                updated = time.monotonic()
            if archive.stat().st_size != total or hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest() != expected:
                # The known download temporary file is safe to discard before retry.
                if archive.parent.resolve() != state.resolve():
                    raise RuntimeError('Download cache path check failed.')
                archive.unlink(missing_ok=True)
                raise RuntimeError('Local resource checksum mismatch.')
            break
        except Exception:
            if attempt == 2:
                raise RuntimeError('First local startup needs a network connection to prepare public resources; retry the script.') from None
            time.sleep(1)
    with zipfile.ZipFile(archive) as bundle:
        if set(bundle.namelist()) != set(manifest['files']):
            raise RuntimeError('Local resource archive file list mismatch.')
        for name, item in manifest['files'].items():
            data = bundle.read(name)
            if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
                raise RuntimeError('Local resource checksum mismatch: ' + name)
            file = target(name)
            file.parent.mkdir(parents=True, exist_ok=True)
            pending = file.with_name(file.name + '.pending-local-support')
            pending.write_bytes(data)
            pending.replace(file)
    ready.write_text(json.dumps({'sha256': expected, 'files': len(manifest['files'])}), encoding='utf-8')
    if archive.parent.resolve() == state.resolve():
        archive.unlink()
    print('Local resources ready. Online user records were not copied.', flush=True)
