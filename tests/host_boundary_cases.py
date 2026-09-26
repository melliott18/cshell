"""CSH-056 residual conditions; no reference executable supplies an oracle."""
import shlex


def cases(helper, echo_policy, numeric_locale, block_device, permission_denial):
    def case(name, script, out=b'', status=0, err=b'', **kw):
        return dict(name=name, script=script + '\n', stdout=out, status=status,
                    stderr=err, **kw)

    yield case('U-035 numbered missing', "printf '%2$s:%1$s\\n' a", alternatives=[
        dict(stdout=b':a\n', stderr=b'', status=0),
        dict(stdout='any', stderr='nonempty', status='nonzero')])
    for operand, value in [('invalid', '0'), ('12x', '12'),
                           ('999999999999999999999999999999', '9223372036854775807'),
                           ('-999999999999999999999999999999', '-9223372036854775808')]:
        yield case('U-035 conversion continuation ' + operand,
                   "printf '%d:%s\\n' " + operand + ' after',
                   (value + ':after\n').encode(), 'nonzero', 'nonempty')
    if numeric_locale:
        env = dict(LC_ALL='', LC_NUMERIC=numeric_locale, LC_MESSAGES=numeric_locale)
        yield case('U-035 non-C numeric', "printf '%.2f\\n' 1,5", b'1,50\n', env=env)
        # LC_MESSAGES may legitimately fall back when the utility has no catalog.
        yield case('U-035 non-C diagnostic continuation', "printf '%d:%s\\n' 12x after",
                   b'12:after\n', 'nonzero', 'nonempty', env=env)
        yield case('U-040 non-C eight bit input', 'cat binary >bytes',
                   files={'bytes': bytes(range(256))}, env=env)
        yield case('U-040 non-C operand order', 'cat second first', b'second\nfirst\n', env=env)
    for operand, gnu, darwin in [
            (r"-e 'a\nb'", b'-e a\nb\n', b'-e a\nb\n'),
            (r"-n 'a\nb'", b'a\nb', b'-n a\nb\n'),
            (r"'a\nb'", b'a\nb\n', b'a\nb\n')]:
        yield case('U-036 POSIXLY_CORRECT ' + operand, 'echo ' + operand,
                   gnu if echo_policy == 'gnu' else darwin, env={'POSIXLY_CORRECT': '1'})
    for utility in ('test', '['):
        end = ' ]' if utility == '[' else ''
        if permission_denial:
            for predicate in ('r', 'w', 'x'):
                yield case(f'U-037 {utility} denied {predicate}',
                           utility + ' -' + predicate + ' denied' + end, status=1)
        if block_device:
            yield case(f'U-037 {utility} positive block device',
                       utility + ' -b ' + shlex.quote(block_device) + end)
    # Close fd 1 after the shell's redirections, so failure is in the utility.
    # The helper execs it, preserving the failure status observed by cshell.
    for command in ('printf value', 'echo value', 'cat data', 'head -n 1 data',
                    "sed -n '1p' data", 'ls tree', 'find tree -type f'):
        yield case('U-040 closed stdout ' + command,
                   helper + ' closed-stdout ' + command, status='nonzero', err='nonempty')
    for command in ('cat absent', 'head absent', 'sed -n 1p absent', 'cmp data absent',
                    'chmod 600 absent', 'rm absent', 'find absent', 'ls absent',
                    'env /missing-csh-command', 'sh /missing-csh-script', 'sleep invalid'):
        yield case('U-040 host error ' + command, command, status='nonzero', err='nonempty')
    # Synchronize after exec: kill the owned sleep only once it is running.
    # The supervisor records readiness before delivering SIGTERM and reaps it.
    yield case('U-040 host interruption sleep', helper + ' interrupt sleep 30', status=143)
    yield case('U-040 long line cat', 'cat long >bytes', files={'bytes': b'x' * 8192 + b'\n'})
    yield case('U-040 long line sed', "sed -n '1p' long >bytes", files={'bytes': b'x' * 8192 + b'\n'})
