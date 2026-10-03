"""CSH-074 operation-level language, regex, editor and argv contracts.

Oracles are literal bytes or arithmetic over authored fixture data, never output
from another implementation. Undefined/unspecified inputs are deliberately absent.
"""
import json
from pathlib import Path
import sys


def cases():
    from host_language_cases import BASE

    def case(utility, name, args=(), stdin=b'', out=b'', status=0, err=b'',
             clauses=('EXTENDED DESCRIPTION',), **kw):
        return dict(id=utility+'/'+name, utility=utility, args=list(args), stdin=stdin,
                    stdout=out, stderr=err, status=status, clauses=list(clauses),
                    source=BASE+utility+'.html', **kw)

    def awk(name, program, out, stdin=b'', **kw):
        return case('awk', name, [program], stdin, out, **kw)

    yield awk('lexical-escapes', r'BEGIN { # comment'+'\n'+r'printf "%s\n", "\101\t\042\\" }', b'A\t"\\\n', clauses=['Lexical Conventions','Grammar'])
    yield awk('operators', 'BEGIN {x=3; print ++x,x++,x; x+=2; x*=3; x/=7; x%=2; print x,2^3,!(3<2),(3==3 && 4!=5), (0 ? "bad" : "ok"),"a" "b"}', b'4 4 5\n1 8 1 1 ok ab\n', clauses=['Expressions in awk','Grammar'])
    yield awk('while-do', 'BEGIN {i=0; while(i<2) {print i; i++} do {print i; i--} while(i>0)}', b'0\n1\n2\n1\n', clauses=['Actions','Grammar'])
    yield awk('next-default-action', 'BEGIN {print "begin"} NR==1 {next} /keep/; END {print NR}', b'begin\nkeep\n3\n', b'skip\nkeep\nother\n', clauses=['Overall Program Structure','Special Patterns','Expression Patterns','Patterns','Actions'])
    yield awk('range-reset', '/^a$/,/^b$/', b'a\nx\nb\na\nb\n', b'no\na\nx\nb\nno\na\nb\n', clauses=['Pattern Ranges','STDIN'])
    yield case('awk','file-counters',['{print FILENAME,FNR,NR} END {print ARGC}', 'one','two'],out=b'one 1 1\ntwo 1 2\n3\n',input_files={'one':b'a\n','two':b'b\n'},clauses=['Variables and Special Variables','OPERANDS'])
    yield awk('field-rebuild','BEGIN {OFS=":"} {$2="X"; print NF,$0; NF=2; print $0}',b'3:a:X:c\na:X\n',b'a b c\n',clauses=['Variables and Special Variables'])
    yield awk('record-separator','BEGIN {RS=":"; ORS="|"} {print $0}',b'a|b|',b'a:b:',clauses=['Variables and Special Variables','STDIN'])
    yield awk('multidimensional-array','BEGIN {a[1,2]=7; print a[1,2], ((1,2) in a); delete a[1,2]; print ((1,2) in a)}',b'7 1\n0\n',clauses=['Expressions in awk'])
    yield awk('match-state','BEGIN {print match("abc12",/[0-9]+/),RSTART,RLENGTH; print match("abc",/[0-9]/),RSTART,RLENGTH}',b'4 4 2\n0 0 -1\n',clauses=['Regular Expressions','String Functions'])
    yield awk('remaining-functions','BEGIN {print toupper("ab"),tolower("CD"),sprintf("%03d",7); print int(-2.9),sin(0),cos(0),exp(0),log(1),atan2(0,1); srand(7); x=rand(); srand(7); print (rand()==x)}',b'AB cd 007\n-2 0 1 1 0 0\n1\n',clauses=['Functions','Arithmetic Functions','String Functions'])
    yield awk('array-parameter','function f(a) {a[1]=9} BEGIN {f(x); print x[1]}',b'9\n',clauses=['User-Defined Functions'])
    yield awk('environment','BEGIN {print ENVIRON["CSH074_WORD"]}',b'visible\n',env={'CSH074_WORD':'visible'},clauses=['Variables and Special Variables','ENVIRONMENT VARIABLES'])
    yield awk('pipe-system-status',r'BEGIN {"printf piped" | getline x; close("printf piped"); print x; print system("exit 7")}',b'piped\n7\n',clauses=['Input/Output and General Functions'])

    yield case('bc','large-integer',stdin=b'2^64\n',out=b'18446744073709551616\n',clauses=['Operations in bc'])
    yield case('bc','lexical-continuation',stdin=b'/* comment */\n12\\\n34\n"literal"\n',out=b'1234\nliteral',clauses=['Lexical Conventions in bc','Grammar'])
    yield case('bc','assignment-increment',stdin=b'a=2\na+=3\na*=2\na/=2\na^=2\na%=7\na\n++a\na++\na\n-a\n',out=b'4\n5\n5\n6\n-6\n',clauses=['Operations in bc','Grammar'])
    yield case('bc','condition-while-break',stdin=b'a=0\nwhile(a<4) {\na=a+1\nif(a==3) break\na\n}\n',out=b'1\n2\n',clauses=['Operations in bc'])
    yield case('bc','array-parameter',stdin=b'define f(a[]) {\nreturn(a[1])\n}\na[1]=7\nf(a[])\n',out=b'7\n',clauses=['Operations in bc','Grammar'])
    yield case('bc','automatic-locals',stdin=b'a=8\ndefine f(x) {\nauto a\na=x+1\nreturn(a)\n}\nf(2)\na\n',out=b'3\n8\n',clauses=['Operations in bc'])

    yield case('ed','default-counts',['data'],b'1p\nw result\nq\n',b'4\none\n4\n',input_files={'data':b'one\n'},files={'result':b'one\n'},clauses=['OPTIONS','OPERANDS','INPUT FILES','Print Command','Write Command'])
    yield case('ed','edit-clean',['-s','data'],b'e other\n,p\nq\n',b'two\n',input_files={'data':b'one\n','other':b'two\n'},clauses=['Edit Command','Quit Command'])
    yield case('ed','interactive-global',['-s'],b'a\na1\na2\nb1\n.\nG/^a/\ns/a/A/\n&\nV/^A/\ns/b/B/\n,p\nQ\n',b'a1\na2\nb1\nA1\nA2\nB1\n',clauses=['Interactive Global Command','Interactive Global Not-Matched Command','Quit Without Checking Command'])
    yield case('ed','null-address-search',['-s'],b'a\na\nb\nc\n.\n1\n\n?^a?\n.+1p\nQ\n',b'a\nb\na\nb\n',clauses=['Null Command','Addresses in ed','Commands in ed'])
    yield case('ed','prompt-toggle',['-s','-p','>'],b'P\nP\nQ\n',b'>>',clauses=['OPTIONS','Prompt Command'])
    yield case('ed','shell-read-write',['-s'],b'r !printf "one\\ntwo\\n"\nw !cat >copy\nQ\n',files={'copy':b'one\ntwo\n'},clauses=['Read Command','Write Command','Shell Escape Command'])
    yield case('ed','substitute-backref',['-s'],b'a\nab12 ab34\n.\ns/ab\\([0-9][0-9]\\)/[\\1]/g\np\nQ\n',b'[12] [34]\n',clauses=['Substitute Command','Regular Expressions in ed'])
    yield case('ed','substitute-occurrence',['-s'],b'a\nx x x\n.\ns/x/Y/2p\nQ\n',b'x Y x\n',clauses=['Substitute Command'])
    yield case('ed','write-range',['-s','data'],b'2w result\nq\n',input_files={'data':b'one\ntwo\n'},files={'result':b'two\n'},clauses=['Write Command'])
    for fault in ('create','write'):
        yield case('ed','temp-'+fault+'-failure',['-s','original'],b'Q\n',status='nonzero',err='nonempty',
                   input_files={'original':b'preserved\n'},files={'original':b'preserved\n','ed.hup':None},
                   fault_provider=True,env={'CSH_ED_FAULT':fault},clauses=['CONSEQUENCES OF ERRORS','OUTPUT FILES'])
    yield case('ed','temp-fault-control',['-s','original'],b',p\nq\n',b'preserved\n',fault_provider=True,input_files={'original':b'preserved\n'},files={'original':b'preserved\n'},clauses=['INPUT FILES','STDIN'])

    expressions=[('negative-division',['-7','/','2'],b'-3\n',0),('remainder',['7','%','3'],b'1\n',0),
        ('left-associative',['9','-','3','-','2'],b'4\n',0),('string-comparison',['abc','<','abd'],b'1\n',0),
        ('numeric-comparison',['02','=','2'],b'1\n',0),('and-false',['text','&','0'],b'0\n',1),
        ('or-empty',['','|',''],b'0\n',1),('anchored-match',['ba',':','a'],b'0\n',1),
        ('match-interval',['aaa',':','a\\{2,3\\}'],b'3\n',0),
        ('nested-groups',['(']*32+['1']+[')']*32,b'1\n',0)]
    for name,args,out,status in expressions:
        yield case('expr',name,args,out=out,status=status,clauses=['Matching Expression'] if 'match' in name else ['Identification as Integer or String','EXTENDED DESCRIPTION'])
    yield case('expr','operand-terminator',['--','-word'],out=b'-word\n',clauses=['OPTIONS','OPERANDS'])

    # The BRE engines must preserve grouping, backreferences and interval counts;
    # the ERE engine has distinct grouping, alternation and repetition syntax.
    for name,flags,pattern,data,out in [
        ('bre-backref',[],r'^\([ab]\)\1$',b'aa\nab\nbb\n',b'aa\nbb\n'),
        ('bre-interval',[],r'^a\{2,3\}$',b'a\naa\naaa\naaaa\n',b'aa\naaa\n'),
        ('ere-repeat',['-E'],r'^(ab)+c?$',b'ab\nabab\nababc\nac\n',b'ab\nabab\nababc\n'),
        ('bracket-classes',[],r'^[[:digit:]][^[:digit:]]$',b'1a\na1\n22\n',b'1a\n'),
        ('bracket-literals',[],r'^[]-]$',b']\n-\na\n',b']\n-\n'),
        ('longest-subexpression',['-E'],r'^(a|aa)+$',b'aaaa\nab\n',b'aaaa\n')]:
        yield case('grep',name,flags+[pattern],data,out,clauses=['DESCRIPTION','OPTIONS'])
    yield case('grep','empty-pattern',[''],b'a\n\nb\n',b'a\n\nb\n',clauses=['OPERANDS','STDIN'])
    yield case('grep','empty-pattern-file',['-f','patterns'],b'a\n',status=1,input_files={'patterns':b''},clauses=['OPTIONS','INPUT FILES'])
    yield case('grep','stdin-operand',['x','-'],b'x\ny\n',b'x\n',clauses=['OPERANDS','STDIN'])
    yield case('grep','utf8-character',['-x','.'], 'é\nxx\n'.encode(), 'é\n'.encode(),env={'LC_ALL':'en_US.UTF-8'},clauses=['ENVIRONMENT VARIABLES','DESCRIPTION'])

    yield case('m4','quoted-rescan',stdin=b"define(`x',`expanded')dnl\n`x' x\ndefine(`show',`$#:$1:$2')dnl\nshow(`a,b',`c')\n",out=b'x expanded\n2:a,b:c\n')
    yield case('m4','quote-comment-delimiters',stdin=b"changequote(`[',`]')dnl\ndefine([x],[yes])dnl\n[x] x\nchangecom([/*],[*/])dnl\n/* x */ x\n",out=b'x yes\n/* x */ yes\n')
    yield case('m4','defn-shift-undefine',stdin=b"define(`x',`$1:$2')define(`y',defn(`x'))dnl\ny(shift(`omit',`a',`b'))\nundefine(`x')dnl\nifdef(`x',`bad',`gone')\n",out=b'a:b\ngone\n')
    yield case('m4','eval-radix-padding',stdin=b'eval(15,16,4) incr(9) decr(0) eval(1<<3)\n',out=b'000f 10 -1 8\n')
    yield case('m4','divnum-discard',stdin=b'divert(-1)discard\ndivert(2)two\ndivert(0)divnum\nundivert(2)undivert(2)dnl\n',out=b'0\ntwo\n')
    yield case('m4','wrap',stdin=b"m4wrap(`last')dnl\nfirst\n",out=b'first\nlast')
    yield case('m4','syscmd-status',stdin=b"syscmd(`printf raw; exit 7')sysval\n",out=b'raw7\n')
    yield case('m4','errprint',stdin=b"errprint(`diagnostic')dnl\n",err=b'diagnostic',clauses=['STDERR'])
    yield case('m4','trace-dump',stdin=b"define(`x',`yes')traceon(`x')dnl\nx\ntraceoff(`x')dumpdef(`x')dnl\n",out=b'yes\n',err='nonempty',clauses=['STDERR','EXTENDED DESCRIPTION'])
    yield case('m4','stdin-operand',['-'],b'literal\n',b'literal\n',clauses=['OPERANDS','STDIN'])
    yield case('m4','file-order',['one','two'],out=b'first\nsecond\n',input_files={'one':b'first\n','two':b'second\n'},clauses=['OPERANDS','INPUT FILES'])

    normal=b'2c2\n< old\n---\n> new\n'
    yield case('patch','ed-format',['-s','-e','data'],b'2c\nnew\n.\n',input_files={'data':b'first\nold\n'},files={'data':b'first\nnew\n'},clauses=['OPTIONS','Patch File Format'])
    yield case('patch','explicit-normal-backup',['-s','-n','-b','data'],normal,input_files={'data':b'first\nold\n'},files={'data':b'first\nnew\n','data.orig':b'first\nold\n'},clauses=['OPTIONS','OUTPUT FILES'])
    yield case('patch','strip-directory',['-s','-d','tree','-p','1'],b'--- a/data\n+++ b/data\n@@ -1 +1 @@\n-old\n+new\n',input_files={'tree/data':b'old\n'},files={'tree/data':b'new\n'},clauses=['Filename Determination','OPTIONS'])
    yield case('patch','blank-insensitive',['-s','-l','data'],b'1c1\n< a b\n---\n> new\n',input_files={'data':b'a\t b\n'},files={'data':b'new\n'},clauses=['OPTIONS','Patch Application'])
    yield case('patch','offset-context',['-s','data'],b'--- data\n+++ data\n@@ -1,2 +1,2 @@\n anchor\n-old\n+new\n',input_files={'data':b'prefix\nanchor\nold\n'},files={'data':b'prefix\nanchor\nnew\n'},clauses=['Patch Application'])
    yield case('patch','two-files',['-s','-p','0'],b'--- one\n+++ one\n@@ -1 +1 @@\n-a\n+A\n--- two\n+++ two\n@@ -1 +1 @@\n-b\n+B\n',input_files={'one':b'a\n','two':b'b\n'},files={'one':b'A\n','two':b'B\n'},clauses=['DESCRIPTION','Filename Determination','Patch Application'])
    yield case('patch','missing-input',['-i','missing'],status='error',err='nonempty',clauses=['STDERR','CONSEQUENCES OF ERRORS'])

    helper=[sys.executable,str(Path(__file__).with_name('host_language_helper.py').resolve()),'argv']
    def vectors(*groups):
        return ''.join(json.dumps(list(g),ensure_ascii=True)+'\n' for g in groups).encode()
    yield case('xargs','nul-input',['-0']+helper,b"a b\0'quoted'\0back\\slash\0\0",vectors(['a b',"'quoted'",'back\\slash','']),clauses=['OPTIONS','STDIN'])
    yield case('xargs','empty-invoke',helper,b'',vectors([]),clauses=['DESCRIPTION'])
    yield case('xargs','empty-suppress',['-r']+helper,clauses=['OPTIONS','DESCRIPTION'])
    yield case('xargs','empty-quotes',helper,b"'' \"\" nonempty\n",vectors(['','','nonempty']),clauses=['STDIN'])
    yield case('xargs','disable-eof',['-E','']+helper,b'_\n',vectors(['_']),clauses=['OPTIONS'])
    yield case('xargs','initial-args',['-n','2']+helper+['fixed'],b'a b c\n',vectors(['fixed','a','b'],['fixed','c']),clauses=['OPERANDS','OPTIONS'])
    # Include every argument and terminator in the independently calculated size.
    size=sum(len(a.encode())+1 for a in helper)+6
    yield case('xargs','size-batches',['-s',str(size)]+helper,b'a bb ccc\n',vectors(['a','bb'],['ccc']),clauses=['DESCRIPTION','OPTIONS'])
    yield case('xargs','minimum-command-size',['-s','2048']+helper,b'a'*1024+b'\n',vectors(['a'*1024]),clauses=['DESCRIPTION','OPTIONS'])

    yield case('xargs','strict-size-boundary',['-s',str(size-1)]+helper,b'a bb\n',vectors(['a'],['bb']),clauses=['OPTIONS'])
    yield case('xargs','oversized-size',['-s','9'*50]+helper,b'a\n',vectors(['a']),clauses=['OPTIONS'])
    yield case('xargs','exit-size-no-count',['-x']+helper,b'a b\n',vectors(['a','b']),clauses=['OPTIONS'])
    yield case('xargs','single-empty-nul',['-0']+helper,b'\0',vectors(['']),clauses=['OPTIONS','STDIN'])
    yield case('xargs','blank-only-input',helper,b' \t\n',vectors([]),clauses=['STDIN','DESCRIPTION'])
    yield case('xargs','blank-only-suppressed',['-r']+helper,b' \t\n',clauses=['STDIN','OPTIONS'])
    yield case('xargs','carry-partial-argument',['-s',str(sum(len(a.encode())+1 for a in helper)+12)]+helper,b'a 1234567890\n',vectors(['a'],['1234567890']),clauses=['OPTIONS','DESCRIPTION'])
