#!/usr/bin/env python3
"""Darwin formatter allocation audits. A crash is FAIL, never qualified."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile

from host_formatted_failures import invocation, run_owned
from host_utilities import sha, source_identity

ROOT = Path(__file__).resolve().parents[1]


def selected_image(image, helper, provider):
    return image == '/usr/lib/system/libsystem_c.dylib' or (
        provider and image.startswith('/') and Path(image).resolve() == helper.resolve())


def allocation_attested(events, ordinal, helper, provider):
    failures = [e for e in events if e['failed']]
    if not events:
        return False
    if ordinal:
        return (len(failures) == 1 and failures[0]['ordinal'] == ordinal and
                selected_image(failures[0]['image'], helper, provider))
    # A passing native-libc-only control cannot qualify the new formatter.
    return not failures and (not provider or any(
        e['symbol'] == 'vasnprintf' and e['image'].startswith('/') and
        Path(e['image']).resolve() == helper.resolve() for e in events))


def conversions(provider):
    fixed = b'1.' + b'0' * 10000
    yield 'fixed', '%.10000f', [fixed]
    if not provider:
        return
    yield 'long-fixed', '%.10000Lf', [fixed]
    for modifier in ('', 'L'):
        yield 'scientific-'+modifier, '%.10000'+modifier+'e', [fixed+b'e+00']
        yield 'general-'+modifier, '%#.10000'+modifier+'g', [b'1.'+b'0'*9999]
        # All four normal leading digits encode exactly one. The standard
        # permits the provider's normalization choice for hexadecimal floats.
        expected = [(f'0x{digit}.'+'0'*10000+f'p{exponent}').encode()
                    for digit, exponent in [('1','+0'),('2','-1'),('4','-2'),('8','-3')]]
        yield 'hex-'+modifier, '%.10000'+modifier+'a', expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', action='store_true',
                        help='Audit the selected portable formatter; default retains native libc comparison')
    parser.add_argument('--record', type=Path, required=True)
    args = parser.parse_args()
    if platform.system() != 'Darwin':
        parser.error('Requires Darwin dyld; Linux libc exhaustion has a separate fixture')
    library = ROOT/'build/tests/host_formatted_libc_alloc.dylib'
    helper = ROOT/('build/tests/host_formatted_alloc' if args.provider else 'build/tests/host_formatted_libc')
    binary = ROOT/'cshell'
    rows = []
    # No reference executable supplies this oracle: 1 to 10000 decimal places.
    with tempfile.TemporaryDirectory(prefix='csh-libc-alloc-') as temporary:
        prefix = Path(temporary)
        (prefix/'printf').symlink_to(helper)
        abort = False
        for conversion, format_string, expected in conversions(args.provider):
            if abort:
                break
            for mode in ('direct', 'exec'):
                targets = [0]
                for ordinal in targets:
                    with tempfile.TemporaryDirectory(dir=prefix) as work:
                        env = dict(PATH=str(prefix)+':'+os.defpath, LC_ALL='C',
                                   DYLD_INSERT_LIBRARIES=str(library), CSH_LIBC_FAIL=str(ordinal))
                        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
                            result = run_owned(invocation(binary, prefix, 'printf', [format_string, '1'], mode),
                                               env, out, err, cwd=work)
                            out.seek(0); err.seek(0)
                            output, diagnostic = out.read(65537), err.read(65537)
                        trace = Path(work)/'libc-alloc.trace'
                        events = []
                        for line in trace.read_text().splitlines() if trace.exists() else []:
                            count, kind, size, failed, image, symbol = line.split('\t')
                            events.append(dict(ordinal=int(count), kind=kind, bytes=int(size),
                                               failed=bool(int(failed)), image=image, symbol=symbol))
                        attested = allocation_attested(events, ordinal, helper, args.provider)
                        # A libc may recover using an unbuffered/stack fallback. If
                        # it cannot, require a diagnostic and normal nonzero exit.
                        recovered = result['status'] == 0 and output in expected and not diagnostic
                        reported = (ordinal != 0 and result['status'] == 1 and any(wanted.startswith(output) for wanted in expected) and
                                    diagnostic == b'printf: write or formatting error: Cannot allocate memory\n')
                        ok = (attested and (recovered or reported) and not result['errors'] and
                              result['reaped'] and result['pid_disappeared'])
                        rows.append(dict(conversion=conversion, format=format_string, mode=mode, ordinal=ordinal, verdict='PASS' if ok else 'FAIL',
                                         invocation=result, events=events, status=result['status'],
                                         stdout_hex=output.hex(), stderr_hex=diagnostic.hex()))
                        print(rows[-1]['verdict'], conversion, mode, 'allocation', ordinal, 'status', result['status'], flush=True)
                        if ordinal == 0 and ok:
                            # Discover site ordinals, not output/status oracles. Only
                            # calls originating in the selected formatter or libc are selected.
                            targets.extend(e['ordinal'] for e in events
                                           if selected_image(e['image'], helper, args.provider))
                        if result['errors'] or not result['pid_disappeared']:
                            abort = True
                            break
                if abort:
                    break  # Never repeat a failed ownership/cleanup attempt.
    record = dict(owner='CSH-079', scope=('selected GNU formatter allocator returns' if args.provider else 'controlled Darwin libc allocator returns')+'; not physical RAM exhaustion', provider=args.provider,
                  platform=platform.platform(), os_build=subprocess.check_output(['sw_vers'], text=True),
                  source_identity=source_identity(), inputs={str(p):sha(p) for p in (library, helper, binary)},
                  cases=rows, totals={v:sum(r['verdict']==v for r in rows) for v in ('PASS','FAIL')})
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(record, indent=2)+'\n')
    return int(bool(record['totals']['FAIL']))


if __name__ == '__main__':
    raise SystemExit(main())
