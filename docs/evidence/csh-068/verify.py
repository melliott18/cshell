"""Recheck retained artifacts, complete ownership and changed Markdown links."""
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tests'))
from host_contract_inventory import load_contracts, validate

errors = validate(load_contracts())
for item in json.loads((HERE / 'artifacts.json').read_text()):
    data = (HERE / item['path']).read_bytes()
    if hashlib.sha256(data).hexdigest() != item['sha256']:
        errors.append('artifact drift: ' + item['path'])
for label in ('native', 'docker'):
    record = json.loads(gzip.decompress((HERE / (label + '-profile.json.gz')).read_bytes()))
    if record['totals'] != {'passed': 1162, 'failed': 0, 'gaps': 0}:
        errors.append(label + ': unexpected strict profile totals')
    if any(row['owner'] in ('CSH-064', 'CSH-068') for row in record['limitations']):
        errors.append(label + ': stale report owner')


def anchors(path):
    text = path.read_text()
    result = set(re.findall(r'<a\s+(?:name|id)="([^"]+)"', text))
    seen = {}
    for heading in re.findall(r'^#+\s+(.+)$', text, re.M):
        heading = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', heading).replace('`', '').lower()
        slug = re.sub(r'[^\w\- ]', '', heading).replace(' ', '-')
        index = seen.get(slug, 0)
        seen[slug] = index + 1
        result.add(slug + ('-' + str(index) if index else ''))
    return result

# The file list is retained so this also works after the branch is integrated.
links = 0
for relative in json.loads((HERE / 'markdown-files.json').read_text()):
    path = ROOT / relative
    for target in re.findall(r'\]\(([^\s)]+)\)', path.read_text()):
        if target.startswith(('http:', 'https:', 'mailto:')):
            continue
        base, separator, anchor = target.partition('#')
        destination = (path.parent / base).resolve() if base else path
        links += 1
        if not destination.exists():
            errors.append(f'{relative}: missing {target}')
        elif separator and destination.suffix == '.md' and anchor not in anchors(destination):
            errors.append(f'{relative}: missing anchor {target}')
print(json.dumps(dict(local_links=links, errors=errors), indent=2))
raise SystemExit(bool(errors))
