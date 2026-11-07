"""Issue 8 character semantics in the supplied en_US UTF-8 locale."""
import json
from pathlib import Path
import sys

BASE = 'https://pubs.opengroup.org/onlinepubs/9799919799/utilities/'


def cases():
    def case(tool, name, args=(), stdin='', stdout='', clauses=(), status=0, env=None, **kw):
        return dict(id=tool+'/multibyte-'+name, utility=tool, args=list(args),
                    stdin=stdin.encode(), stdout=stdout.encode(), stderr=b'', status=status,
                    env=env or {'LC_ALL': 'en_US.UTF-8'}, clauses=list(clauses)+['ENVIRONMENT VARIABLES'],
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

    yield case('awk', 'combining-positions',
               ['BEGIN {s="é界"; print length(s),substr(s,2,1),index(s,"界")}'],
               stdout='3 ́ 3\n', clauses=['String Functions'])
    yield case('awk', 'field-separator', ['-F', '界', '{print NF,$1,$2,$3}'],
               stdin='é界語界z\n', stdout='3 é 語 z\n', clauses=['OPTIONS','Variables and Special Variables'])
    yield case('awk', 'split-ere', ['BEGIN {n=split("aébé界c",a,/[é界]/); print n,"<" a[3] ">",a[4]}'],
               stdout='4 <> c\n', clauses=['String Functions','Regular Expressions'])
    yield case('awk', 'global-replacement', ['{n=gsub(/é+/,"[&]"); print n,$0}'],
               stdin='éé界é\n', stdout='2 [éé]界[é]\n', clauses=['String Functions','Regular Expressions'])
    yield case('awk', 'decimal-comma-input', ['{printf "%.1f\\n",$1+$2}'],
               stdin='1,5 2,5\n', stdout='4,0\n', env={'LC_ALL':'fr_FR.UTF-8'},
               clauses=['STDIN','Output Statements'])
    yield case('awk', 'decimal-comma-source', ['BEGIN {printf "%.1f\\n",1.5}'],
               stdout='1,5\n', env={'LC_ALL':'fr_FR.UTF-8'}, clauses=['Lexical Conventions','Output Statements'])
    yield case('awk', 'system-exit-status',
               ['BEGIN {print system("exit 0"),system("exit 1"),system("exit 127"),system("exit 255")}'],
               stdout='0 1 127 255\n', clauses=['Input/Output and General Functions'])
    yield case('expr', 'combining-match-length', ['é界',':','...'], stdout='3\n', clauses=['Matching Expression'])
    yield case('expr', 'backreference', ['éé界',':',r'\(.\)\1'], stdout='é\n', clauses=['Matching Expression'])
    yield case('expr', 'empty-capture', ['é',':',r'\(x*\)'], stdout='\n', status=1, clauses=['Matching Expression','EXIT STATUS'])
    yield case('expr', 'longest-capture', ['éé界',':',r'\(.*\)界'], stdout='éé\n', clauses=['Matching Expression'])
    yield case('expr', 'interval-match-length', ['éé界',':',r'é\{2\}界'], stdout='3\n', clauses=['Matching Expression'])
    yield case('ed', 'backreference-lines', ['-s'],
               stdin='a\néé界\n語語z\n.\n1,$s/\\(.\\)\\1/[\\1]/g\n1,$p\nQ\n',
               stdout='[é]界\n[語]z\n', clauses=['Regular Expressions in ed','Substitute Command'])
    yield case('ed', 'nested-captures', ['-s'],
               stdin='a\néé界\n.\ns/\\(é*\\)\\(界\\)/\\2[\\1]/\np\nQ\n', stdout='界[éé]\n',
               clauses=['Regular Expressions in ed','Substitute Command'])
    yield case('ed', 'numbered-occurrence', ['-s'], stdin='a\né界語\n.\ns/./X/2\np\nQ\n',
               stdout='éX語\n', clauses=['Regular Expressions in ed','Substitute Command'])
