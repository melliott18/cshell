#!/usr/bin/env python3
"""Current host-contract ownership, checked against immutable normative evidence.

This checks accounting, never utility conformance. It deliberately does not derive
required names from host_utility_cases.HOSTS (the selected harness subset).
"""
import ast
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = Path(__file__).with_name('host_contracts.json')


def load_contracts():
    return json.loads(MANIFEST.read_text())


def utility_owner(name):
    return next(owner['ticket'] for owner in load_contracts()['owners']
                if name in owner['utilities'])


def condition_owner(condition):
    contracts = load_contracts()
    if condition in contracts['conditional_owners']:
        return contracts['conditional_owners'][condition]
    return next(owner['ticket'] for owner in contracts['owners']
                if condition in owner['conditions'])


def validate(contracts, root=ROOT):
    """Return actionable errors, including loss, duplication and closed owners."""
    errors = []
    inventory = json.loads((root / contracts['inventory']).read_text())
    sources = json.loads((root / contracts['inventory']).with_name('utility-sources.json').read_text())
    retained = json.loads((root / contracts['residual_evidence']).read_text())
    entries = inventory['entries']
    names = [e['name'] for e in entries]
    expected = {e['name'] for e in entries if e['exec_required']}
    if len(names) != 156 or len(set(names)) != 156 or set(names) != {p['utility'] for p in sources['pages']} | {'['}:
        errors.append('normative inventory differs from the 155-page index plus [')
    if len(expected) != 101 or sum(e['scope'] == 'base' for e in entries) != 111:
        errors.append('base/exec applicability counts changed: review normative scope')
    utilities, conditions, tickets = [], [], []
    ledger = (root / 'docs/host-system-inventory.md').read_text()
    for owner in contracts['owners']:
        ticket = owner['ticket']
        tickets.append(ticket)
        utilities.extend(owner['utilities'])
        conditions.extend(owner['conditions'])
        path = root / owner['path']
        if not path.is_file():
            errors.append(f'{ticket}: missing ticket {path}')
            continue
        body = path.read_text()
        if not re.search(r'^- Status: (backlog|ready|in-progress|blocked|review)$', body, re.M):
            errors.append(f'{ticket}: outstanding contracts require an open ticket')
        for name in owner['utilities']:
            # A row must agree in both human-readable ownership directions.
            row = next((line for line in ledger.splitlines()
                        if f'>[`{name}`](' in line), '')
            if f'[{ticket}](' not in row:
                errors.append(f'{name}: inventory owner differs from {ticket}')
            if f'| [`{name}`](' not in body:
                errors.append(f'{ticket}: missing utility row {name}')
        for condition in owner['conditions']:
            if f'`{condition}`' not in body:
                errors.append(f'{ticket}: missing retained condition {condition}')
    for label, assigned, required in (
            ('utility', utilities, expected),
            ('condition', conditions, {r['condition'] for r in retained['residuals']})):
        for missing in sorted(required - set(assigned)):
            errors.append(f'unowned {label}: {missing}')
        for extra in sorted(set(assigned) - required):
            errors.append(f'unknown {label}: {extra}')
        for duplicate in sorted({x for x in assigned if assigned.count(x) > 1}):
            errors.append(f'duplicate {label}: {duplicate}')
    if len(tickets) != len(set(tickets)):
        errors.append('duplicate owner ticket')
    # Read the emitter's literal condition tuples without running host probes.
    emitter = ast.parse((root / 'tests/host_utilities.py').read_text())
    emitted = {node.elts[0].value for node in ast.walk(emitter)
               if isinstance(node, ast.Tuple) and len(node.elts) == 3
               and isinstance(node.elts[0], ast.Constant)
               and isinstance(node.elts[0].value, str)
               and re.match(r'U-\d{3}/', node.elts[0].value)}
    if set(contracts['conditional_owners']) != emitted:
        errors.append('conditional prerequisite ownership differs from emitted conditions')
    for condition, ticket in contracts['conditional_owners'].items():
        owner = next((o for o in contracts['owners'] if o['ticket'] == ticket), None)
        if owner is None:
            errors.append(f'{condition}: unknown conditional owner {ticket}')
        elif not (root / owner['path']).is_file() or f'`{condition}`' not in (root / owner['path']).read_text():
            errors.append(f'{ticket}: missing conditional prerequisite {condition}')
    # Retained evidence never changes with the current owner allocation.
    from host_capability_limits import RESIDUAL
    current = {c: (u, reason) for c, u, reason in RESIDUAL}
    for row in retained['residuals']:
        pair = current.get(row['condition'])
        if pair is None or pair[1] != row['reason'] or not row['source'].endswith('/' + pair[0] + '.html'):
            errors.append(f"retained residual changed: {row['condition']}")
    return errors


if __name__ == '__main__':
    problems = validate(load_contracts())
    for problem in problems:
        print('FAIL:', problem)
    if not problems:
        print('PASS: 156 utility names; 101 external contracts; 30 retained conditions; current open owners')
    raise SystemExit(bool(problems))
