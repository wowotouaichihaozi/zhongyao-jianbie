"""Stage/activate a guarded static release without rebuilding or deleting assets."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

parser = argparse.ArgumentParser()
parser.add_argument('--project', default='/var/www/feishengwangying')
parser.add_argument('--overlay', required=True)
parser.add_argument('--release', required=True)
parser.add_argument('--commit', required=True)
parser.add_argument('--activate', action='store_true')
parser.add_argument('--rollback', action='store_true')
args = parser.parse_args()
assert re.fullmatch(r'[A-Za-z0-9-]+', args.release)
assert re.fullmatch(r'[0-9a-f]{40}', args.commit)
project = Path(args.project).resolve()
dist = project/'frontend/dist'
release = project/'frontend/releases'/args.release
incoming = Path(args.overlay).resolve()
prefix = '/releases/'+args.release+'/'

def atomic(file, data):
    temporary = file.with_name(file.name+'.pending-'+args.release)
    temporary.write_bytes(data)
    os.replace(temporary, file)

if args.rollback:
    old = project/'frontend/releases'/(args.release+'.previous-index.html')
    assert old.is_file()
    atomic(dist/'index.html', old.read_bytes())
    old_version = project/'frontend/releases'/(args.release+'.previous-version.json')
    atomic(dist/'version.json', old_version.read_bytes() if old_version.exists() else json.dumps({'rolledBackFrom':args.release,'commit':None}).encode())
    print(json.dumps({'rolledBack':args.release}))
    raise SystemExit(0)

manifest = json.loads((incoming/'overlay-manifest.json').read_text())
private_index = project/'frontend/production-base-index.html'
for name, expected in manifest['baseline'].items():
    file = private_index if name=='index.html' and private_index.exists() else dist/name
    assert hashlib.sha256(file.read_bytes()).hexdigest()==expected, 'Production baseline changed: '+name
for name, expected in manifest['files'].items():
    assert hashlib.sha256((incoming/name).read_bytes()).hexdigest()==expected, 'Overlay damaged: '+name
if not private_index.exists(): private_index.write_bytes((dist/'index.html').read_bytes())

def rewrite(text):
    text=text.replace('"/assets/', '"'+prefix+'assets/').replace("'/assets/", "'"+prefix+'assets/')
    text=text.replace('"assets/', '"'+prefix.lstrip('/')+'assets/').replace("'assets/", "'"+prefix.lstrip('/')+'assets/')
    text=text.replace('url(/assets/', 'url('+prefix+'assets/')
    for name in ['local-resource-history','local-path-cache','local-account-view','local-exam-evidence']:
        text=text.replace('/'+name+'.mjs', prefix+name+'.js')
    return text

if not release.exists():
    release.mkdir(parents=True)
    shutil.copytree(dist/'assets', release/'assets', copy_function=os.link)
    for file in (release/'assets').rglob('*'):
        if file.is_file() and file.suffix in {'.js','.css','.mjs'}:
            try: original=file.read_text(encoding='utf-8')
            except UnicodeError: continue
            text=rewrite(original)
            if text!=original: atomic(file, text.encode())  # Never truncate a shared hardlink.
    for name in manifest['files']:
        destination=release/(name[:-4]+'.js' if name.endswith('.mjs') else name)
        destination.parent.mkdir(parents=True,exist_ok=True)
        atomic(destination, rewrite((incoming/name).read_text(encoding='utf-8')).encode())
    html=private_index.read_text(encoding='utf-8').replace('/assets/', prefix+'assets/')
    html=html.replace('</head>', '<link rel="stylesheet" href="'+prefix+'local-overrides.css"></head>')
    (release/'index.html').write_text(html,encoding='utf-8')
    version={'releaseId':args.release,'commit':args.commit,'publishedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base':'server-static-build','overlayFiles':len(manifest['files'])}
    (release/'version.json').write_text(json.dumps(version,indent=2),encoding='utf-8')
    index_links=dist/'releases';index_links.mkdir(exist_ok=True)
    (index_links/args.release).symlink_to(release,target_is_directory=True)

version=json.loads((release/'version.json').read_text())
assert version['commit']==args.commit
if args.activate:
    old=project/'frontend/releases'/(args.release+'.previous-index.html')
    if not old.exists(): old.write_bytes((dist/'index.html').read_bytes())
    old_version=project/'frontend/releases'/(args.release+'.previous-version.json')
    if (dist/'version.json').exists() and not old_version.exists(): old_version.write_bytes((dist/'version.json').read_bytes())
    atomic(dist/'version.json',(release/'version.json').read_bytes())
    atomic(dist/'index.html',(release/'index.html').read_bytes())
print(json.dumps({'release':args.release,'commit':args.commit,'staged':True,'activated':args.activate,'index':prefix+'index.html'}))
