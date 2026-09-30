"""Strict regressions for repaired M4 provider contracts.

These retain normative oracles and historical stock-provider failures.
They are required in the default suite; --provider-regressions selects only them.
"""
from host_language_cases import BASE


def cases():
    def m4(name, source, output=b'', status=0, error=b''):
        return dict(id='m4/' + name, utility='m4', args=[], stdin=source,
                    stdout=output, stderr=error, status=status,
                    clauses=['EXTENDED DESCRIPTION', 'EXIT STATUS'],
                    source=BASE + 'm4.html')

    yield m4('wrap-order', b"m4wrap(`first')m4wrap(`second')dnl\n", b'firstsecond')
    # Failure avoids guessing a random filename, and requires continued input
    # processing, an empty expansion, a diagnostic and nonzero final status.
    yield m4('mkstemp-failure', b"mkstemp(`absent/fileXXXXXX')after\n",
             b'after\n', 'nonzero', 'nonempty')
    yield m4('substr-nonnumeric', b"substr(`abc',`invalid')\n",
             b'\n', 'nonzero', 'nonempty')

    yield m4('wrap-rescan-order', b"m4wrap(`define(`later',`expanded')')m4wrap(`later')dnl\n", b'expanded')
    yield m4('wrap-many', b''.join(b"m4wrap(`" + str(i).encode() + b";')" for i in range(64)) + b'dnl\n',
             b''.join(str(i).encode()+b';' for i in range(64)))
    row = m4('mkstemp-unique', b"define(`first',mkstemp(`temporaryXXXXXX'))define(`second',mkstemp(`temporaryXXXXXX'))dnl\n")
    row['clauses'].append('OUTPUT FILES')
    row['file_rules'] = [dict(pattern='temporary??????', count=2, data=b'', mode=0o600)]
    yield row
