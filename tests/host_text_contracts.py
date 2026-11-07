#!/usr/bin/env python3
"""Validate section accounting, never infer whole-page conformance from tests."""
import json
from pathlib import Path
from host_contract_inventory import load_contracts
from host_text_cases import UTILITIES, cases

SECTIONS = ('DESCRIPTION','OPTIONS','OPERANDS','STDIN','INPUT FILES',
            'ENVIRONMENT VARIABLES','ASYNCHRONOUS EVENTS','STDOUT','STDERR',
            'OUTPUT FILES','EXTENDED DESCRIPTION','EXIT STATUS','CONSEQUENCES OF ERRORS')


def load():
    return json.loads(Path(__file__).with_suffix('.json').read_text())


def validate(data):
    errors=[]
    manifest=load_contracts()
    if manifest.get('qualification_maps',{}).get('CSH-073')!='tests/host_text_contracts.json':
        errors.append('ownership manifest lost CSH-073 qualification map')
    expected=next(o['utilities'] for o in manifest['owners'] if o['ticket']=='CSH-073')
    names=[row['utility'] for row in data['utilities']]
    if sorted(names)!=sorted(expected) or set(names)!=set(UTILITIES):
        errors.append('utility coverage differs from CSH-073 owner')
    defined={c['id'] for c in cases('en_US.UTF-8',True)}
    mapped=set()
    for row in data['utilities']:
        name=row['utility']
        if set(row['sections'])!=set(SECTIONS):
            errors.append(name+': missing or unknown sections')
        for section,disposition in row['sections'].items():
            if disposition['status'] not in ('partial','open','not-applicable') or not disposition['reason']:
                errors.append(name+': unjustified disposition '+section)
        for item in row['cases']:
            if item not in defined or not item.startswith(name+'/'):
                errors.append(name+': unknown case '+item)
            mapped.add(item)
        if row['owner']!='CSH-073' or row['full_contract_qualified']:
            errors.append(name+': unsupported full-contract claim or owner')
        if not row.get('remaining_contracts'):
            errors.append(name+': lost unqualified contracts')
    if mapped!=defined:
        errors.append('case accounting incomplete')
    expected_conditions=next(o['conditions'] for o in load_contracts()['owners'] if o['ticket']=='CSH-073')
    if set(data['conditions'])!=set(expected_conditions):
        errors.append('retained condition accounting incomplete')
    from host_text_interruptions import definitions
    expected_groups = {name: {c['id'] for c in cases('en_US.UTF-8', True)
                              if c.get('category') == name}
                       for name in ('transformations', 'offsets', 'large-inputs')}
    expected_groups['interruptions'] = {tool+'/'+kind for tool, kind in definitions()}
    for name, expected_group in expected_groups.items():
        actual_group = data.get('coverage_groups', {}).get(name, [])
        if set(actual_group) != expected_group or len(actual_group) != len(expected_group):
            errors.append('missing, duplicate or unknown coverage group entries: '+name)
    return errors


if __name__=='__main__':
    errors=validate(load())
    for error in errors:
        print('FAIL:',error)
    if not errors:
        print('PASS: CSH-073 25 utility pages, 13 normative sections each, five retained conditions')
    raise SystemExit(bool(errors))
