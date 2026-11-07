#!/usr/bin/env python3
"""Reserve sequential CSH IDs atomically and check ticket/issue identity."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

REGISTRY_REF = 'refs/heads/chore/CSH-001-ticket-registry'
ID = r'CSH-\d{3,}'


def command(*args, cwd=None, data=None, check=True):
    return subprocess.run(args, input=data, text=True, capture_output=True,
                          cwd=cwd, check=check, timeout=60)


def registry_errors(registry):
    errors, seen = [], set()
    if not isinstance(registry, dict) or registry.get('schema_version') != 1 or not isinstance(registry.get('reservations'), dict):
        return ['invalid registry schema']
    for ticket, issue in registry['reservations'].items():
        if not re.fullmatch(ID, ticket) or ticket != f'CSH-{int(ticket[4:]):03d}' or int(ticket[4:]) < 1:
            errors.append(f'invalid reserved ID: {ticket}')
        if type(issue) is not int or issue < 1:
            errors.append(f'{ticket}: invalid issue number')
        elif issue in seen:
            errors.append(f'issue #{issue} has multiple reservations')
        if type(issue) is int:
            seen.add(issue)
    return errors


class Registry:
    """An append-only data branch; normal fast-forward pushes are the lock."""
    def __init__(self, cwd, remote='origin', ref=REGISTRY_REF):
        self.cwd, self.remote, self.ref = cwd, remote, ref

    def git(self, *args, **kwargs):
        return command('git', *args, cwd=self.cwd, **kwargs)

    def tip(self):
        lines = self.git('ls-remote', '--refs', self.remote, self.ref).stdout.splitlines()
        if len(lines) != 1:
            raise ValueError('shared registry is missing; do not fall back to a local next-ID scan')
        return lines[0].split()[0]

    def read(self):
        revision = self.tip()
        # Use the exact advertised object, never shared FETCH_HEAD: worktrees
        # and concurrent allocators can fetch independently.
        self.git('fetch', '--quiet', '--no-tags', self.remote, revision)
        value = json.loads(self.git('show', revision + ':allocations.json').stdout)
        errors = registry_errors(value)
        if errors:
            raise ValueError('; '.join(errors))
        return revision, value

    def publish(self, revision, value):
        blob = self.git('hash-object', '-w', '--stdin', data=json.dumps(value, indent=2) + '\n').stdout.strip()
        tree = self.git('mktree', data=f'100644 blob {blob}\tallocations.json\n').stdout.strip()
        commit = self.git('commit-tree', tree, '-p', revision,
                          data='Reserve a CSH ticket number\n').stdout.strip()
        return self.git('push', '--porcelain', self.remote, commit + ':' + self.ref, check=False)

    def reserve(self, issue):
        if type(issue) is not int or issue < 1:
            raise ValueError('issue number must be positive')
        for _ in range(12):
            revision, value = self.read()
            for ticket, existing in value['reservations'].items():
                if existing == issue:
                    return ticket, value
            number = max((int(key[4:]) for key in value['reservations']), default=0) + 1
            ticket = f'CSH-{number:03d}'
            value['reservations'][ticket] = issue
            result = self.publish(revision, value)
            if result.returncode == 0:
                return ticket, value
            # A lost response can hide a successful push; rereading and retrying
            # recovers the issue's reservation without allocating a second ID.
            if self.tip() == revision:
                raise ValueError('reservation push failed without a competing update: ' + result.stderr.strip())
        raise ValueError('registry contention: retry with the SAME issue number')


def github(repo, endpoint, *, value=None):
    args = ['gh', 'api', f'repos/{repo}/{endpoint}']
    if value is not None:
        args += ['--method', 'PATCH', '--input', '-']
    return json.loads(command(*args, data=json.dumps(value) if value is not None else None).stdout)


def all_issues(repo):
    pages = json.loads(command('gh', 'api', '--paginate', '--slurp',
                              f'repos/{repo}/issues?state=all&per_page=100').stdout)
    return [issue for page in pages for issue in page if 'pull_request' not in issue]


def validate(documents, issues, registry):
    """Use None for offline validation; an empty live response is still checked."""
    errors = registry_errors(registry)
    if errors:
        return errors, []
    reservations = registry['reservations']
    issues_by_number = {issue['number']: issue for issue in issues or []}
    issue_ids, file_ids, warnings = {}, {}, []
    for issue in issues or []:
        match = re.match(r'^(CSH-\d+): (.+)$', issue['title'])
        if not match:
            if re.match(r'^CSH-\d', issue['title']):
                errors.append(f'issue #{issue["number"]}: malformed CSH title')
            continue  # Unallocated drafts and explicitly named duplicate issues.
        ticket = match[1]
        if ticket in issue_ids:
            errors.append(f'{ticket}: duplicate GitHub issues #{issue_ids[ticket]} and #{issue["number"]}')
        issue_ids[ticket] = issue['number']
        if reservations.get(ticket) != issue['number']:
            errors.append(f'{ticket}: GitHub issue #{issue["number"]} does not own this reservation')
        heading = re.search(r'^# (CSH-\d+): (.+)$', issue.get('body') or '', re.M)
        if heading and heading[0][2:] != issue['title']:
            errors.append(f'issue #{issue["number"]}: body heading differs from title')
        status = re.search(r'^- Status: (.+)$', issue.get('body') or '', re.M)
        if status and issue.get('state', '').lower() == 'closed' and status[1] not in ('done', 'superseded'):
            warnings.append(f'{ticket}: closed issue body still says {status[1]}')
    index = documents.get('docs/tickets/README.md', '')
    for path, body in documents.items():
        filename = re.fullmatch(r'docs/tickets/(CSH-\d+)-[a-z0-9-]+\.md', path)
        if not filename:
            if re.match(r'docs/tickets/CSH-\d+', path):
                errors.append(f'{path}: invalid ticket filename')
            continue
        ticket = filename[1]
        if ticket in file_ids:
            errors.append(f'{ticket}: duplicate ticket files')
        file_ids[ticket] = path
        heading = re.search(r'^# (CSH-\d+): (.+)$', body, re.M)
        link = re.search(r'^- Issue: \[#(?P<label>\d+)\]\((?P<url>https://github\.com/[^/]+/[^/]+/issues/(?P<number>\d+))\)', body, re.M)
        if not heading or heading[1] != ticket:
            errors.append(f'{path}: filename and heading disagree')
        if not link or link['label'] != link['number']:
            errors.append(f'{path}: missing or inconsistent Issue link')
            continue
        number = int(link['number'])
        if reservations.get(ticket) != number:
            errors.append(f'{path}: issue #{number} does not own {ticket}')
        if issues is not None:
            issue = issues_by_number.get(number)
            if not issue:
                errors.append(f'{path}: linked GitHub issue is missing')
            else:
                if heading and heading[0][2:] != issue['title']:
                    errors.append(f'{path}: title differs from GitHub issue #{number}')
                if issue.get('html_url') and link['url'] != issue['html_url']:
                    errors.append(f'{path}: Issue link targets a different repository')
        if f'[{ticket}]({Path(path).name})' not in index:
            errors.append(f'{path}: missing matching ticket-index link')
        branch = re.search(r'^- Branch:.*?(CSH-\d+)', body, re.M)
        if branch and branch[1] != ticket:
            status = re.search(r'^- Status: (.+)$', body, re.M)
            if status and status[1] in ('done', 'superseded'):
                warnings.append(f'{path}: historical shared branch identifies {branch[1]}')
            else:
                errors.append(f'{path}: branch field identifies {branch[1]}')
    for label, target in re.findall(r'\[(CSH-\d+)\]\(([^)]+)\)', index):
        file_id = re.search(r'(CSH-\d+)-', target)
        if file_id and file_id[1] != label:
            errors.append(f'index: {label} links to {file_id[1]}')
        if target.endswith('.md') and '://' not in target and 'docs/tickets/' + target not in documents:
            errors.append(f'index: missing ticket target {target}')
    return sorted(set(errors)), sorted(set(warnings))


def documents_at(root, revision=None):
    if revision is None:
        return {str(path.relative_to(root)): path.read_text() for path in (root / 'docs/tickets').glob('*.md')}
    paths = command('git', 'ls-tree', '-r', '--name-only', revision, 'docs/tickets', cwd=root).stdout.splitlines()
    return {path: command('git', 'show', revision + ':' + path, cwd=root).stdout
            for path in paths if path.endswith('.md')}


def snapshot_errors(root, revision, registry):
    """Check each audited snapshot against the authoritative reservation map."""
    path = 'docs/tickets/allocations.json'
    if revision is None:
        source = (root / path).read_text()
    else:
        # Older branches predate the registry. Only a missing path is allowed;
        # an invalid ref or unreadable blob must still fail the command.
        if not command('git', 'ls-tree', '--name-only', revision, '--', path, cwd=root).stdout.strip():
            return []
        source = command('git', 'show', revision + ':' + path, cwd=root).stdout
    try:
        snapshot = json.loads(source)
    except ValueError as error:
        return [f'invalid allocation snapshot: {error}']
    errors = registry_errors(snapshot)
    if errors:
        return ['invalid allocation snapshot: ' + '; '.join(errors)]
    # A stale snapshot may omit newer reservations, but cannot contradict one.
    return [f'snapshot conflicts with authoritative reservation: {ticket}'
            for ticket, number in snapshot['reservations'].items()
            if registry['reservations'].get(ticket) != number]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', help='GitHub owner/repository; defaults to this checkout')
    sub = parser.add_subparsers(dest='command', required=True)
    reserve = sub.add_parser('reserve', help='reserve an ID for an existing unnumbered issue, then publish its title')
    reserve.add_argument('--issue', required=True, type=int)
    check = sub.add_parser('check', help='check identities; offline by default')
    check.add_argument('--live', action='store_true', help='check current GitHub issues and the shared registry')
    check.add_argument('--ref', action='append', default=[], help='also audit a fetched branch/ref without checking it out')
    check.add_argument('--record', type=Path)
    args = parser.parse_args(argv)
    root = Path(command('git', 'rev-parse', '--show-toplevel').stdout.strip())
    snapshot = root / 'docs/tickets/allocations.json'
    repo = args.repo
    if args.command == 'reserve' or args.live:
        remote = command('git', 'remote', 'get-url', 'origin').stdout.strip()
        match = re.fullmatch(r'(?:https://github\.com/|git@github\.com:)([^/]+/[^/]+?)(?:\.git)?', remote)
        if not match:
            raise ValueError('origin must identify a github.com repository')
        origin_repo = match[1]
        if repo and repo.lower() != origin_repo.lower():
            raise ValueError('--repo must match origin: reservations cannot cross repositories')
        repo = origin_repo
    if args.command == 'reserve':
        issue = github(repo, f'issues/{args.issue}')
        if 'pull_request' in issue:
            raise ValueError('reserve an issue, not a pull request')
        registry = Registry(root)
        _, existing = registry.read()
        current = next((key for key, number in existing['reservations'].items() if number == args.issue), None)
        title = issue['title']
        numbered = re.match(r'^(CSH-\d+): ', title)
        if re.match(r'^CSH-\d', title) and not numbered:
            raise ValueError('issue has a malformed CSH title; reconcile it before allocation')
        if numbered and numbered[1] != current:
            raise ValueError('issue already has an unreserved/different ID; reconcile it before allocation')
        ticket, value = registry.reserve(args.issue)
        plain_title = re.sub(r'^CSH-(?:\d+|NNN): ', '', title)
        body = issue.get('body') or ''
        body = re.sub(r'^# CSH-NNN:', '# ' + ticket + ':', body, flags=re.M)
        body = body.replace('- Issue: Assigned when published',
                            f'- Issue: [#{args.issue}](https://github.com/{repo}/issues/{args.issue})')
        github(repo, f'issues/{args.issue}', value={'title': ticket + ': ' + plain_title, 'body': body})
        # Only after both remote steps succeed. On a failure rerun this command
        # with the same issue; the durable reservation is never reused.
        snapshot.write_text(json.dumps(value, indent=2) + '\n')
        print(ticket)
        return 0
    registry = Registry(root).read()[1] if args.live else json.loads(snapshot.read_text())
    errors = registry_errors(registry)
    if errors:
        raise ValueError('invalid registry: ' + '; '.join(errors))
    issues = all_issues(repo) if args.live else None
    findings = {}
    for ref in [None, *args.ref]:
        errors, warnings = validate(documents_at(root, ref), issues, registry)
        errors.extend(snapshot_errors(root, ref, registry))
        findings[ref or 'worktree'] = dict(errors=errors, warnings=warnings)
    if args.record:
        args.record.parent.mkdir(parents=True, exist_ok=True)
        args.record.write_text(json.dumps(dict(registry=registry, findings=findings), indent=2) + '\n')
    for ref, result in findings.items():
        for error in result['errors']:
            print(f'FAIL {ref}: {error}')
        for warning in result['warnings']:
            print(f'WARN {ref}: {warning}')
    failed = any(result['errors'] for result in findings.values())
    if not failed:
        print(f'PASS: ticket identities; {len(registry["reservations"])} shared reservations; {len(findings)} snapshots')
    return int(failed)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        raise SystemExit(2)
