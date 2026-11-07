"""CSH-079 finite locale, API-error and actual interrupted-output oracles.

Expectations are authored here, never collected from a reference utility.
Source-including probes are distinct from the unmodified executable witnesses.
"""
import json
import locale
import os
from pathlib import Path
import platform
import signal
import tempfile

from host_formatted_failures import invocation, run_owned


def conversion_cases():
    for name, argv, output in [
        ('exact binary float rounding', ['%.0f:%.0f:%.2f:%.2f', '2.5', '3.5', '1.125', '1.375'], b'2:4:1.12:1.38'),
        ('negative zero optional float', ['%+.1f:%+.1f', '-0', '0'], b'-0.0:+0.0'),
        ('integer precision exceeds width', ['[%+3.6d][%#3.6o][%#3.6X]', '-12', '8', '31'], b'[-000012][000010][0X00001F]'),
        ('character constants both quote forms', ['%d:%d:%x', "'A", '"Z', "' "], b'65:90:20'),
        ('numbered precision truncates bytes', ['[%2$-6.2s][%1$#06x]|', '31', 'abcd', '32', 'efgh'], b'[ab    ][0x001f]|[ef    ][0x0020]|'),
        ('binary every standard escape', ['%b', r'\a\b\f\n\r\t\v\\\000\0377'], b'\a\b\f\n\r\t\v\\\0\xff'),
    ]:
        yield dict(name='CSH-079 ' + name, utility='printf', argv=argv,
                   stdout=output, stderr=b'', status=0, env={})
    # intmax_t in the selected native/Debian providers is signed 64-bit.
    # POSIX requires a range diagnostic and continued accumulated-value output;
    # exact English strerror wording is a declared Darwin/glibc policy.
    diagnostic = 'Result too large' if platform.system() == 'Darwin' else 'Numerical result out of range'
    for fmt, operand, output in [
        ('%d', '9223372036854775808', b'9223372036854775807'),
        ('%d', '-9223372036854775809', b'-9223372036854775808'),
        ('%u', '18446744073709551616', b'18446744073709551615'),
    ]:
        yield dict(name='CSH-079 integer range ' + operand, utility='printf',
                   argv=[fmt + ':%s', operand, 'after'], stdout=output + b':after', status=1,
                   stderr=('{program}: ' + operand + ': ' + diagnostic + '\n').encode(), env={})


def locale_cases(limitations):
    # EUC-JP HIRAGANA LETTER A: JIS X 0208 0x2422 -> U+3042 on glibc.
    # Apple's EUC decoder packs bytes then applies the locale's mask/bits:
    # (0xa4a2 & ~0x8080) | 0x8080 = 0xa4a2, not Unicode. See source
    # provenance and LC_CTYPE configuration in docs/evidence/csh-079/.
    # Use installed locale spelling, but never its output to derive the oracle.
    selected = 'ja_JP.eucJP' if platform.system() == 'Darwin' else 'ja_JP.EUC-JP'
    previous = locale.setlocale(locale.LC_CTYPE)
    try:
        locale.setlocale(locale.LC_CTYPE, selected)
    except locale.Error as error:
        limitations.append(dict(condition='U-035/other-locales', owner='CSH-079',
                                 verdict='UNQUALIFIED', reason=str(error), locale=selected))
        return
    finally:
        locale.setlocale(locale.LC_CTYPE, previous)
    character_value = b'42146' if platform.system() == 'Darwin' else b'12354'
    for utility, argv, output in [
        ('printf', [b'%d:[%.1s][%.2s][%c]', b"'\xa4\xa2", b'\xa4\xa2', b'\xa4\xa2', b'\xa4\xa2'],
         character_value + b':[\xa4][\xa4\xa2][\xa4]'),
        ('printf', [b'%b', b'\xa4\xa2\\000tail'], b'\xa4\xa2\0tail'),
        ('echo', [b'-n', b'\xa4\xa2', b'\\c'], b'-n \xa4\xa2 \\c\n'),
    ]:
        yield dict(name='CSH-079 EUC-JP ' + utility + ' ' + repr(argv[0]), utility=utility,
                   argv=argv, stdout=output, stderr=b'', status=0, env=dict(LC_ALL=selected))


def denied_catalog_cases(catalogs, limitations):
    path = catalogs / 'denied.cat'
    path.write_bytes((catalogs / 'incomplete.cat').read_bytes())
    path.chmod(0)
    try:
        with path.open('rb'):
            pass
    except PermissionError:
        pass
    else:
        limitations.append(dict(condition='U-035/locale-catalogs', owner='CSH-079',
                                 verdict='UNQUALIFIED', reason='Fixture identity can read mode-000 catalog'))
        return
    yield dict(name='CSH-079 unreadable catalog fallback', utility='printf',
               argv=['%d:%s', '12x', 'after'], stdout=b'12:after', status=1,
               stderr=b'{program}: 12x: not completely converted\n',
               env=dict(LC_ALL='fr_FR.UTF-8', NLSPATH=str(path)))


def api_error_cases(shell, prefix, helper):
    # API-return injection, not proof of allocator exhaustion inside libc.
    words = {'ENOMEM': b'Cannot allocate memory', 'EINTR': b'Interrupted system call',
             'EOVERFLOW': (b'Value too large to be stored in data type' if platform.system() == 'Darwin'
                           else b'Value too large for defined data type'), 'zero': b'Input/output error'}
    with tempfile.TemporaryDirectory(prefix='api-error-', dir=prefix.parent) as temporary:
        selected = Path(temporary)
        (selected / 'printf').symlink_to(helper)
        for failure in ('control', *words):
            for mode in ('direct', 'exec'):
                environment = dict(PATH=str(selected) + ':' + os.defpath, LC_ALL='C',
                                   CSH_PRINTF_API_ERROR=failure)
                with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
                    result = run_owned(invocation(shell, selected, 'printf', ['%d%s', '12', 'after'], mode),
                                       environment, out, err)
                    out.seek(0)
                    err.seek(0)
                    output, diagnostic = out.read(65537), err.read(65537)
                expected_out = b'12after' if failure == 'control' else b''
                expected_err = b'' if failure == 'control' else b'printf: write or formatting error: ' + words[failure] + b'\n'
                expected_status = int(failure != 'control')
                ok = (not result['errors'] and result['reaped'] and result['pid_disappeared'] and
                      result['status'] == expected_status and output == expected_out and diagnostic == expected_err)
                yield dict(name='CSH-079 libc API result ' + failure, mode=mode, verdict='PASS' if ok else 'FAIL',
                           invocation=result, expected=dict(status=expected_status, stdout_hex=expected_out.hex(), stderr_hex=expected_err.hex()),
                           actual=dict(status=result['status'], stdout_hex=output.hex(), stderr_hex=diagnostic.hex()))


def interrupt_cases(shell, prefix, helpers):
    with tempfile.TemporaryDirectory(prefix='interrupt-', dir=prefix.parent) as temporary:
        selected = Path(temporary)
        for utility, helper in helpers.items():
            (selected / utility).symlink_to(helper)
        for utility, args in [('printf', ['value']), ('printf', ['%s', 'value']),
                              ('printf', ['%b', 'value']), ('echo', ['value'])]:
            for mode in ('direct', 'exec'):
                for disposition in ('control', 'caught', 'default'):
                    environment = dict(PATH=str(selected) + ':' + os.defpath, LC_ALL='C',
                                       CSH_FORMATTED_INTERRUPT=disposition)
                    with tempfile.TemporaryDirectory(dir=selected) as work:
                        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
                            result = run_owned(invocation(shell, selected, utility, args, mode),
                                               environment, out, err, cwd=work)
                            out.seek(0)
                            err.seek(0)
                            output, diagnostic = out.read(65537), err.read(65537)
                        path = Path(work) / 'interrupt.json'
                        measured = json.loads(path.read_text()) if path.exists() else None
                    expected_out = b'value' + (b'\n' if utility == 'echo' else b'') if disposition == 'control' else b''
                    expected_err = (b'echo: write error\n' if utility == 'echo' else
                                    b'printf: write or formatting error: Interrupted system call\n') if disposition == 'caught' else b''
                    expected_status = {'control': 0, 'caught': 1, 'default': -signal.SIGALRM}[disposition]
                    observed = measured is None if disposition == 'control' else bool(measured and measured['ready'] and measured['filled'] > 0)
                    if disposition == 'caught':
                        observed = bool(observed and measured.get('signals', 0) > 0 and
                                        measured.get('drained') == measured['filled'] and
                                        measured.get('stream_error') == 1 and measured.get('provider_status') == 1)
                    ok = (observed and not result['errors'] and result['reaped'] and result['pid_disappeared'] and
                          result['status'] == expected_status and output == expected_out and diagnostic == expected_err)
                    yield dict(name='CSH-079 interrupted ' + utility + ' ' + args[0] + ' ' + disposition,
                               mode=mode, verdict='PASS' if ok else 'FAIL', invocation=result, measured=measured,
                               expected=dict(status=expected_status, stdout_hex=expected_out.hex(), stderr_hex=expected_err.hex()),
                               actual=dict(status=result['status'], stdout_hex=output.hex(), stderr_hex=diagnostic.hex()))
