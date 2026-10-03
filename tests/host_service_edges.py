"""Additional clause-derived codec cases; no native host services are invoked."""
import base64
import os
import re
import stat

MODES = ('direct', 'command', 'exec', 'file', 'stdin')
DIAGNOSTIC = re.compile(rb'.+', re.S)


def codec_edges(s, encoded):
    payload = b'edge payload\x00\xff\n'
    for dispatch in MODES:
        with s.directory() as root:
            nested = root / 'nested'; nested.mkdir(mode=0o777); nested.chmod(0o777)
            for mime in (False, True):
                algorithm = 'base64' if mime else 'historical'
                for header_mode, expected_mode in [('000', 0), ('751', 0o751),
                                                  ('u=rw,g=r,o=', 0o640), ('=rw', 0o666)]:
                    target = root / 'decoded'
                    target.unlink(missing_ok=True)
                    def check(a):
                        permissions = stat.S_IMODE(target.stat().st_mode)
                        # 000 is intentionally unreadable until after mode observation.
                        target.chmod(0o600)
                        return permissions == expected_mode and target.read_bytes() == payload
                    s.invoke('edge-decode-mode-' + algorithm + '-' + header_mode, 'uudecode', [],
                             root, dispatch, data=encoded(payload, mode=header_mode, mime=mime), check=check)
                for pathname in ('nested/output', './-', 'portable-_.0123456789'):
                    target = root / pathname
                    target.unlink(missing_ok=True)
                    s.invoke('edge-decode-path-' + algorithm + '-' + pathname, 'uudecode', [],
                             root, dispatch, data=encoded(payload, name=pathname, mime=mime),
                             check=lambda a: target.read_bytes() == payload)
                target = root / 'overwrite'; target.write_bytes(b'old bytes that must disappear'); target.chmod(0o600)
                s.invoke('edge-decode-overwrite-' + algorithm, 'uudecode', [], root, dispatch,
                         data=encoded(payload, name='overwrite', mode='640', mime=mime),
                         check=lambda a: target.read_bytes() == payload and stat.S_IMODE(target.stat().st_mode) == 0o640)
                link = root / 'link'; link.unlink(missing_ok=True); link.symlink_to('overwrite')
                s.invoke('edge-decode-symlink-' + algorithm, 'uudecode', [], root, dispatch,
                         data=encoded(b'followed\n', name='link', mime=mime),
                         check=lambda a: link.is_symlink() and target.read_bytes() == b'followed\n')
                target.chmod(0o400)
                if s.services or os.geteuid() != 0:
                    s.invoke('edge-decode-denied-' + algorithm, 'uudecode', [], root, dispatch,
                             data=encoded(payload, name='overwrite', mime=mime), status='nonzero', stderr=DIAGNOSTIC,
                             check=lambda a: target.read_bytes() == b'followed\n')
                target.chmod(0o600)
                # -- makes an option-looking input filename unambiguous.
                source = root / '-encoded'; source.write_bytes(encoded(payload, name='-', mime=mime))
                s.invoke('edge-decode-option-end-' + algorithm, 'uudecode', ['--', '-encoded'], root,
                         dispatch, stdout=payload)
                source = root / '-binary'; source.write_bytes(payload); source.chmod(0o751)
                s.invoke('edge-encode-mode-path-' + algorithm, 'uuencode',
                         (['-m'] if mime else []) + ['--', '-binary', 'nested/output'], root, dispatch,
                         stdout=re.compile(rb'.*', re.S),
                         check=lambda a: a['stdout'].replace(b'`', b' ') ==
                         encoded(payload, name='nested/output', mode='751', mime=mime).replace(b'`', b' '))
            # Nonalphabet bytes must be ignored, including across Base64 quanta.
            text = base64.b64encode(payload)
            noisy = b'!@#-_'.join(bytes([b]) for b in text)
            for suffix, body in [('noise', noisy), ('split', b'\n'.join(bytes([b]) for b in text))]:
                s.invoke('edge-decode-base64-' + suffix, 'uudecode', [], root, dispatch,
                         data=b'begin-base64 640 -\n' + body + b'\n====\n', stdout=payload)


def service_edges(s, encoded):
    """Linux-only permission, locale and ENOSPC observations in the guarded image."""
    for dispatch in MODES:
        with s.directory() as root:
            for mime in (False, True):
                algorithm = 'base64' if mime else 'historical'
                payload = b'\x00\xffUTF-8: \xc3\xa9\n'
                # Owner differs from the caller, but the existing file is writable.
                foreign = root / 'foreign'; foreign.mkdir(exist_ok=True); foreign.chmod(0o755)
                target = foreign / 'out'; target.write_bytes(b'old'); target.chmod(0o666)
                s.invoke('edge-decode-chmod-denied-' + algorithm, 'uudecode', [], root, dispatch,
                         data=encoded(payload, name='foreign/out', mode='400', mime=mime),
                         check=lambda a: target.read_bytes() == payload and target.stat().st_uid == 0
                         and stat.S_IMODE(target.stat().st_mode) == 0o666)
                environment = {'LC_ALL': 'fr_FR.UTF-8'}
                s.invoke('edge-decode-utf8-' + algorithm, 'uudecode', [], root, dispatch,
                         env=environment, data=encoded(payload, name='-', mime=mime), stdout=payload)
                source = root / 'binary'; source.write_bytes(payload); source.chmod(0o640)
                s.invoke('edge-encode-utf8-' + algorithm, 'uuencode',
                         (['-m'] if mime else []) + ['binary', 'decoded'], root, dispatch, env=environment,
                         stdout=re.compile(rb'.*', re.S), check=lambda a:
                         a['stdout'].replace(b'`', b' ') == encoded(payload, mime=mime).replace(b'`', b' '))
                for utility, args, data in [
                    ('uuencode', (['-m'] if mime else []) + ['decoded'], payload),
                    ('uudecode', [], encoded(payload, name='-', mime=mime))]:
                    with open('/dev/full', 'wb', buffering=0) as full:
                        s.invoke('edge-full-output-' + utility + '-' + algorithm, utility,
                                 args, root, dispatch, data=data, stdout_fd=full.fileno(),
                                 status='nonzero', stderr=DIAGNOSTIC)
            with open('/dev/full', 'wb', buffering=0) as full:
                s.invoke('edge-full-output-date', 'date', ['+output'], root, dispatch,
                         stdout_fd=full.fileno(), status='nonzero', stderr=DIAGNOSTIC)
            for utility in ('uuencode', 'uudecode', 'date'):
                s.invoke('edge-localized-diagnostic-' + utility, utility, ['-@'], root,
                         dispatch, env={'LC_ALL': 'fr_FR.UTF-8'}, status='nonzero', stderr=DIAGNOSTIC)


def date_edges(s, fake):
    # Expected civil times are explicit; datetime is used only to convert the
    # independent UTC input fields to an epoch for the read-only clock fixture.
    from datetime import datetime, timezone
    cases = [
        ('leap-century', (2000, 2, 29, 0, 0, 0), 'UTC0', b'2000-02-29 00:00:00 +0000'),
        ('nonleap-century', (2100, 3, 1, 0, 0, 0), 'UTC0', b'2100-03-01 00:00:00 +0000'),
        ('year-end', (2015, 12, 31, 23, 59, 59), 'UTC0', b'2015-12-31 23:59:59 +0000'),
        ('year-start', (2016, 1, 1, 0, 0, 0), 'UTC0', b'2016-01-01 00:00:00 +0000'),
        ('dst-spring-before', (2024, 3, 10, 6, 59, 59), 'EST5EDT,M3.2.0/2,M11.1.0/2', b'2024-03-10 01:59:59 -0500'),
        ('dst-spring-after', (2024, 3, 10, 7, 0, 0), 'EST5EDT,M3.2.0/2,M11.1.0/2', b'2024-03-10 03:00:00 -0400'),
        ('dst-fall-before', (2024, 11, 3, 5, 59, 59), 'EST5EDT,M3.2.0/2,M11.1.0/2', b'2024-11-03 01:59:59 -0400'),
        ('dst-fall-after', (2024, 11, 3, 6, 0, 0), 'EST5EDT,M3.2.0/2,M11.1.0/2', b'2024-11-03 01:00:00 -0500'),
    ]
    for dispatch in MODES:
        with s.directory() as root:
            for name, civil, zone, expected in cases:
                epoch = int(datetime(*civil, tzinfo=timezone.utc).timestamp())
                s.invoke('edge-date-' + name, 'date', ['+%F %T %z'], root, dispatch,
                         env={'LD_PRELOAD': fake, 'CSH078_CLOCK_EPOCH': str(epoch), 'TZ': zone}, stdout=expected+b'\n')
            for civil, expected in [((2016, 1, 1), b'2015 53 5'), ((2016, 1, 4), b'2016 01 1')]:
                epoch = int(datetime(*civil, tzinfo=timezone.utc).timestamp())
                s.invoke('edge-date-iso-week-' + str(civil[2]), 'date', ['+%G %V %u'], root, dispatch,
                         env={'LD_PRELOAD': fake, 'CSH078_CLOCK_EPOCH': str(epoch)}, stdout=expected+b'\n')
            s.invoke('edge-date-alternative-modifiers', 'date',
                     ['+%EC|%Ey|%EY|%Od|%Oe|%OH|%OI|%Om|%OM|%OS|%Ou|%OU|%OV|%Ow|%OW|%Oy'],
                     root, dispatch, env={'LD_PRELOAD': fake},
                     stdout=b'20|24|2024|29|29|12|12|02|34|56|4|08|09|4|09|24\n')
            for suffix, environment, expected in [
                ('french', {'LC_ALL': '', 'LC_TIME': 'fr_FR.UTF-8'}, 'jeudi|février'),
                ('all-over-time', {'LC_ALL': 'C', 'LC_TIME': 'fr_FR.UTF-8'}, 'Thursday|February')]:
                s.invoke('edge-date-locale-' + suffix, 'date', ['+%A|%B'], root, dispatch,
                         env={'LD_PRELOAD': fake, **environment}, stdout=(expected+'\n').encode())
