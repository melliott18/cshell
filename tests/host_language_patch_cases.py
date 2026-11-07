"""Patch option interactions; permitted preprocessor spellings are explicit."""


def cases():
    def case(name, args, delta, **kw):
        return dict(id='patch/'+name, utility='patch', args=args, stdin=delta,
                    stdout=b'', stderr=b'', status=0,
                    source='https://pubs.opengroup.org/onlinepubs/9799919799/utilities/patch.html',
                    clauses=['OPTIONS', 'OUTPUT FILES', 'Patch Application'], **kw)

    delta = b'2c2\n< old\n---\n> new\n'
    original, changed = b'head\nold\ntail\n', b'head\nnew\ntail\n'
    # Both orientations of the mandated conditional are valid. Check all
    # source bytes and directive nesting; no provider output supplies the oracle.
    conditional = (rb'head\n(?:#ifndef FEATURE\nold\n#else\nnew\n|'
                   rb'#ifdef FEATURE\nnew\n#else\nold\n)'
                   rb'#endif(?: /\* FEATURE \*/)?\ntail\n')
    yield case('define-replacement', ['-s', '-D', 'FEATURE', 'data'], delta,
               input_files={'data': original},
               file_rules=[dict(pattern='data', count=1, data={'regex': conditional})])
    yield case('backup-output-existing', ['-s', '-b', '-o', 'result', 'data'], delta,
               input_files={'data': original, 'result': b'previous output\n'},
               files={'data': original, 'result': changed, 'result.orig': b'previous output\n'},
               file_rules=[dict(pattern='data.orig', count=0)])
    yield case('backup-output-new', ['-s', '-b', '-o', 'result', 'data'], delta,
               input_files={'data': original}, files={'data': original, 'result': changed},
               file_rules=[dict(pattern='*.orig', count=0)])
    yield case('backup-overwrite', ['-s', '-b', 'data'], delta,
               input_files={'data': original, 'data.orig': b'older backup\n'},
               files={'data': changed, 'data.orig': original})
    yield case('backup-first-patch-only', ['-s', '-b', '-p', '0'],
               b'--- data\n+++ data\n@@ -1 +1 @@\n-old\n+middle\n'
               b'--- data\n+++ data\n@@ -1 +1 @@\n-middle\n+new\n',
               input_files={'data': b'old\n'}, files={'data': b'new\n', 'data.orig': b'old\n'})
    row = case('operand-overrides-header', ['-s', '-p', '0', 'target'],
               b'--- data\n+++ data\n@@ -1 +1 @@\n-old\n+new\n',
               input_files={'target': b'old\n', 'data': b'old\n'},
               files={'target': b'new\n', 'data': b'old\n'})
    row['clauses'] += ['OPERANDS', 'Filename Determination']
    yield row
