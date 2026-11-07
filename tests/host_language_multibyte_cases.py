"""Issue 8 character semantics in the supplied en_US UTF-8 locale."""
import json
from pathlib import Path
import sys

BASE = 'https://pubs.opengroup.org/onlinepubs/9799919799/utilities/'


def cases():
    def case(tool, name, args=(), stdin='', stdout='', clauses=(), **kw):
        return dict(id=tool+'/multibyte-'+name, utility=tool, args=list(args),
                    stdin=stdin.encode(), stdout=stdout.encode(), stderr=b'', status=0,
                    env={'LC_ALL': 'en_US.UTF-8'}, clauses=list(clauses)+['ENVIRONMENT VARIABLES'],
                    source=BASE+tool+'.html', **kw)
    yield case('awk', 'length-substr-index', ['BEGIN {s="é界z"; print length(s),substr(s,2,1),index(s,"z")}'],
               stdout='3 界 3\n', clauses=['String Functions'])
    yield case('awk', 'match-positions', ['BEGIN {match("é界z",/界/); print RSTART,RLENGTH}'],
               stdout='2 1\n', clauses=['String Functions', 'Regular Expressions'])
    yield case('awk', 'global-dot', ['{n=gsub(/./,"X"); print n,$0}'], stdin='é界\n', stdout='2 XX\n',
               clauses=['String Functions', 'Regular Expressions'])
    yield case('bc', 'literal-string', stdin='"é界"\n', stdout='é界', clauses=['Lexical Conventions in bc'])
    yield case('ed', 'substitute-dot', ['-s'], stdin='a\né界z\n.\ns/^./X/\np\nQ\n', stdout='X界z\n',
               clauses=['Regular Expressions in ed', 'Substitute Command'])
    yield case('ed', 'backreference', ['-s'], stdin='a\néé界\n.\ns/\\(.\\)\\1/[\\1]/\np\nQ\n', stdout='[é]界\n',
               clauses=['Regular Expressions in ed', 'Substitute Command'])
    yield case('expr', 'match-length', ['é界', ':', '..'], stdout='2\n', clauses=['Matching Expression'])
    yield case('expr', 'capture', ['é界', ':', '.\\(.\\)'], stdout='界\n', clauses=['Matching Expression'])
    yield case('grep', 'ere-interval', ['-E', '^.{2}$'], stdin='é界\né\n界zz\n', stdout='é界\n', clauses=['DESCRIPTION','OPTIONS'])
    yield case('grep', 'case-fold', ['-i', '^é$'], stdin='É\né\nx\n', stdout='É\né\n', clauses=['DESCRIPTION','OPTIONS'])
    for name, program, expected in [
        ('length', "len(`é界')\n", '2\n'),
        ('combining-count', "len(`é界')\n", '3\n'),
        ('index', "index(`é界z',`z') index(`é界z',`界')\n", '2 1\n'),
        ('index-missing-empty', "index(`é界',`x') index(`é界',`')\n", '-1 0\n'),
        ('substring', "substr(`é界z',1,1)|substr(`é界z',2)|substr(`é界',9,1)\n", '界|z|\n'),
        ('substring-large-count', "substr(`é界z',1,2147483647)\n", '界z\n'),
        ('transliteration', "translit(`é界éz',`é界',`AB')\n", 'ABAz\n'),
        ('transliteration-wide', "translit(`a界az',`a界',`é語')\n", 'é語éz\n'),
        ('transliteration-edge-hyphen', "translit(`é-界',`-é界',`語字-')\n", '字語-\n'),
        ('transliteration-delete', "translit(`é界éz',`é界',`A')\n", 'AAz\n'),
    ]:
        yield case('m4', name, stdin=program, stdout=expected, clauses=['EXTENDED DESCRIPTION'])
    row = case('m4', 'substring-large-count-C', stdin="substr(`abc',1,2147483647)\n",
               stdout='bc\n', clauses=['EXTENDED DESCRIPTION'])
    row['env'] = {'LC_ALL': 'C'}
    yield row
    helper=[sys.executable,str(Path(__file__).with_name('host_language_helper.py').resolve()),'argv']
    yield case('xargs', 'quoted-arguments', helper, stdin='"é 界" 語\\ 字\n',
               stdout=json.dumps(['é 界','語 字'])+'\n', clauses=['DESCRIPTION','STDIN'])
