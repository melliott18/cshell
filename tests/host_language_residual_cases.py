"""Strict reproducers for obligations outside the selected qualified subset.

These retain normative oracles and failures, never expected-failure allowances.
Run explicitly with host_languages.py --remaining-contracts.
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
