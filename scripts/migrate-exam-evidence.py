"""Run once against the question DB after taking a consistent backup."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from exam_evidence import migrate_exam_evidence
parser = argparse.ArgumentParser()
parser.add_argument('database')
args = parser.parse_args()
connection = sqlite3.connect(args.database)
with connection:
    changed = migrate_exam_evidence(connection)
assert connection.execute('pragma integrity_check').fetchone()[0] == 'ok'
print(json.dumps({'changed': changed, 'integrity': 'ok'}))
connection.close()
