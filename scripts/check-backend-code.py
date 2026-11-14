"""Check supplied backend source/dependencies without starting services or a DB."""
from __future__ import annotations

import importlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    modules = ['flask', 'flask_cors', 'waitress', 'bcrypt', 'dotenv', 'requests', 'fitz', 'docx', 'pptx', 'langgraph', 'torch', 'torchvision', 'ultralytics', 'fastapi', 'uvicorn']
    for module in modules:
        importlib.import_module(module)
    files = sorted((ROOT / 'backend').rglob('*.py'))
    assert files, 'Backend source files are missing.'
    for file in files:
        compile(file.read_text(encoding='utf-8-sig'), str(file), 'exec')
    report = {'dependencyImports': modules, 'backendSourceFilesChecked': len(files), 'backendServiceStarted': False, 'businessDatabaseCreated': False}
    destination = ROOT / '.backend-check'
    destination.mkdir(exist_ok=True)
    (destination / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f'Backend source and dependencies passed: {len(files)} Python files, {len(modules)} dependencies.')
    print('Business backend, database, knowledge retrieval and AI still run on the server.')


if __name__ == '__main__':
    main()
