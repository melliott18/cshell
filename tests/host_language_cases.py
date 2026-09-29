"""CSH-074 bounded, independently authored POSIX.1-2024 witnesses.

No utility output is used to construct an oracle. Clauses are normative heading
names in host_language_contracts.json; a witness never qualifies its whole page.
"""
import json
import sys
from pathlib import Path

UTILITIES = ('awk', 'bc', 'ed', 'expr', 'grep', 'm4', 'patch', 'xargs')
BASE = 'https://pubs.opengroup.org/onlinepubs/9799919799/utilities/'


def cases():
    def case(utility, name, args=(), stdin=b'', out=b'', status=0, err=b'',
             clauses=(), **kw):
        return dict(id=utility + '/' + name, utility=utility, args=list(args),
                    stdin=stdin, stdout=out, stderr=err, status=status,
                    clauses=list(clauses), source=BASE + utility + '.html', **kw)

    yield case('awk', 'records-fields', ['-F', ':', '{print NR, NF, $2}'],
               b'a:b\nx:y:z\n', b'1 2 b\n2 3 y\n', clauses=['OPTIONS', 'EXTENDED DESCRIPTION'])
    yield case('awk', 'variables', ['-v', 'n=3', 'BEGIN {print n+2}'], out=b'5\n', clauses=['OPTIONS', 'Variables and Special Variables'])
    yield case('awk', 'program-files', ['-f', 'program', 'data'], out=b'6\n',
               input_files={'program': b'{s += $1} END {print s}\n', 'data': b'2\n4\n'}, clauses=['OPERANDS', 'INPUT FILES'])
    yield case('awk', 'arrays-loops', ['BEGIN {a["a"]=2; a["b"]=3; for (k in a) s+=a[k]; print s; delete a["a"]; print ("a" in a)}'], out=b'5\n0\n', clauses=['Expressions in awk', 'Actions'])
    yield case('awk', 'function-control', ['function f(x) {return x*x} BEGIN {for(i=1;i<=4;i++) {if(i==2) continue; if(i==4) break; print f(i)}}'], out=b'1\n9\n', clauses=['Actions', 'User-Defined Functions'])
    yield case('awk', 'ere-range', ['/^start$/,/^end$/ {print}'], b'no\nstart\ninside\nend\nno\n', b'start\ninside\nend\n', clauses=['Patterns', 'Regular Expressions'])
    yield case('awk', 'strings', ['BEGIN {s="ab12ab"; print gsub(/ab/,"X",s),s; print substr("abcd",2,2),index("abcd","bc"),length("abc"); n=split("a:b",a,":"); print n,a[2]}'], out=b'2 X12X\nbc 2 3\n2 b\n', clauses=['String Functions'])
    yield case('awk', 'format-math', ['BEGIN {printf "%04d %.1f\\n",int(3.9),sqrt(9)}'], out=b'0003 3.0\n', clauses=['Arithmetic Functions', 'Output Statements'])
    yield case('awk', 'getline-output', ['BEGIN {getline x < "data"; print x > "result"; close("result")}'], input_files={'data': b'copied\n'}, files={'result': b'copied\n'}, clauses=['Input/Output and General Functions', 'OUTPUT FILES'])
    yield case('awk', 'exit-end', ['BEGIN {exit 7} END {print "end"}'], out=b'end\n', status=7, clauses=['EXIT STATUS', 'Actions'])
    yield case('awk', 'missing-file', ['{print}', 'missing'], status='nonzero', err='nonempty', clauses=['CONSEQUENCES OF ERRORS', 'STDERR'])

    yield case('bc', 'arithmetic', stdin=b'2+3*4\n(2+3)*4\n2^10\n17%5\n', out=b'14\n20\n1024\n2\n', clauses=['Operations in bc'])
    yield case('bc', 'scale', stdin=b'scale=3\n1/8\nsqrt(4)\nscale(1.25)\nlength(1234)\n', out=b'.125\n2.000\n2\n4\n', clauses=['Operations in bc'])
    yield case('bc', 'bases', stdin=b'obase=16\n255\nobase=10\nibase=16\nFF\n', out=b'FF\n255\n', clauses=['Operations in bc'])
    yield case('bc', 'function-loop-array', stdin=b'define f(n) {\nauto i,s\ns=0\nfor(i=1;i<=n;i++) s+=i\nreturn(s)\n}\na[2]=f(4)\na[2]\n', out=b'10\n', clauses=['Operations in bc'])
    yield case('bc', 'file-then-stdin', ['program'], b'3+4\n', b'3\n7\n', input_files={'program': b'1+2\n'}, clauses=['OPERANDS', 'STDIN', 'INPUT FILES'])
    yield case('bc', 'math-library', ['-l'], b'scale=3\ns(0)\nc(0)\ne(0)\nl(1)\na(0)\n', b'0\n1.000\n1.000\n0\n0\n', clauses=['OPTIONS', 'Operations in bc'])
    yield case('bc', 'quit', stdin=b'9\nquit\n10\n', out=b'9\n', clauses=['Operations in bc'])
    # Error exit value is explicitly unspecified; only a normal exit plus the
    # required diagnostic and lack of further execution are asserted.
    yield case('bc', 'missing-file', ['missing'], b'99\n', status='normal', err='nonempty', clauses=['CONSEQUENCES OF ERRORS', 'STDERR'])

    yield case('ed', 'substitute-write', ['-s', 'data'], b'2s/old/new/\nw result\nq\n', input_files={'data': b'first\nold\n'}, files={'data': b'first\nold\n', 'result': b'first\nnew\n'}, clauses=['Substitute Command', 'Write Command', 'OUTPUT FILES'])
    yield case('ed', 'append-insert-change-delete', ['-s'], b'a\none\ntwo\n.\n1i\nzero\n.\n2c\nONE\n.\n3d\n,p\nQ\n', b'zero\nONE\n', clauses=['Append Command', 'Insert Command', 'Change Command', 'Delete Command'])
    yield case('ed', 'copy-move-join-undo', ['-s'], b'a\na\nb\nc\n.\n1t$\n4m0\n1,2j\nu\n,p\nQ\n', b'a\na\nb\nc\n', clauses=['Copy Command', 'Move Command', 'Join Command', 'Undo Command'])
    yield case('ed', 'addresses-mark-number', ['-s'], b'a\na\nb\nc\n.\n2ka\n\'ap\n$=\n1,2n\nQ\n', b'b\n3\n1\ta\n2\tb\n', clauses=['Addresses in ed', 'Mark Command', 'Number Command', 'Line Number Command'])
    yield case('ed', 'global-bre', ['-s'], b'a\nab\nxx\nabb\n.\ng/^ab/p\nv/^ab/p\nQ\n', b'ab\nabb\nxx\n', clauses=['Regular Expressions in ed', 'Global Command', 'Global Non-Matched Command'])
    yield case('ed', 'read-edit-filename', ['-s', 'data'], b'f result\nf\nr other\n,p\nE other\n,p\nq\n', b'result\nresult\none\ntwo\ntwo\n', input_files={'data': b'one\n', 'other': b'two\n'}, clauses=['Filename Command', 'Read Command', 'Edit Without Checking Command'])
    yield case('ed', 'list', ['-s'], b'a\nx\ty\n.\nl\nQ\n', b'x\\ty$\n', clauses=['List Command'])
    yield case('ed', 'bad-address', ['-s'], b'1p\n', b'?\n', status='nonzero', clauses=['CONSEQUENCES OF ERRORS', 'EXIT STATUS'])
    yield case('ed', 'write-failure', ['-s', 'data'], b'w absent/result\n', b'?\n', status='nonzero', err='optional-diagnostic', input_files={'data': b'safe\n'}, files={'data': b'safe\n'}, clauses=['Write Command', 'CONSEQUENCES OF ERRORS'])
    yield case('ed', 'bounded-buffer', ['-s'], b'a\n'+b'x'*4096+b'\n.\n1p\nQ\n', b'x'*4096+b'\n', clauses=['EXTENDED DESCRIPTION'])

    exprs = [('precedence', ['2','+','3','*','4'], b'14\n',0),
             ('parentheses',['(','2','+','3',')','*','4'],b'20\n',0),
             ('zero',['3','-','3'],b'0\n',1),
             ('comparison',['4','>=','3'],b'1\n',0),
             ('or',['0','|','right'],b'right\n',0),
             ('and',['left','&','yes'],b'left\n',0),
             ('match-length',['abc123',':','[a-z]*'],b'3\n',0),
             ('match-capture',['abc123',':','[a-z]*\\([0-9]*\\)'],b'123\n',0),
             ('match-empty',['abc',':','x\\(.*\\)'],b'\n',1)]
    for name,args,out,status in exprs:
        yield case('expr',name,args,out=out,status=status,clauses=['EXTENDED DESCRIPTION','STDOUT','EXIT STATUS'])
    yield case('expr','invalid',['1','+'],status=2,err='nonempty',clauses=['CONSEQUENCES OF ERRORS','STDERR','EXIT STATUS'])

    data=b'Alpha\nbeta\na.b\naab\n'
    for name,args,out,status in [
        ('bre',['^a.b$'],b'a.b\naab\n',0),
        ('ere',['-E','^(Alpha|beta)$'],b'Alpha\nbeta\n',0),
        ('fixed',['-F','a.b'],b'a.b\n',0),
        ('ignore-case',['-i','^alpha$'],b'Alpha\n',0),
        ('invert-number',['-n','-v','^a'],b'1:Alpha\n2:beta\n',0),
        ('count',['-c','^a'],b'2\n',0),
        ('quiet',['-q','beta'],b'',0),
        ('whole-line',['-x','bet'],b'',1),
        ('multiple-patterns',['-e','^Alpha$','-e','^beta$'],b'Alpha\nbeta\n',0)]:
        yield case('grep',name,args,data,out,status,clauses=['OPTIONS','STDIN','STDOUT','EXIT STATUS'])
    yield case('grep','pattern-file',['-f','patterns','data'],out=b'Alpha\nbeta\n',input_files={'patterns':b'^Alpha$\n^beta$\n','data':data},clauses=['INPUT FILES','OPERANDS'])
    yield case('grep','file-prefix',['beta','one','two'],out=b'one:beta\ntwo:beta\n',input_files={'one':data,'two':data},clauses=['STDOUT'])
    yield case('grep','file-list',['-l','beta','one','two'],out=b'one\ntwo\n',input_files={'one':data,'two':data},clauses=['OPTIONS','STDOUT'])
    yield case('grep','missing-file',['x','missing'],status='error',err='nonempty',clauses=['STDERR','EXIT STATUS','CONSEQUENCES OF ERRORS'])
    yield case('grep','invalid-bre',['['],b'x\n',status='error',err='nonempty',clauses=['STDERR','EXIT STATUS'])
    yield case('grep','silent-missing',['-s','x','missing'],status='error',clauses=['OPTIONS','EXIT STATUS'])

    yield case('m4','define-arguments',stdin=b"define(`pair',`$2:$1')dnl\npair(`a',`b')\n",out=b'b:a\n',clauses=['EXTENDED DESCRIPTION'])
    yield case('m4','define-option',['-D','word=value'],b'word\n',b'value\n',clauses=['OPTIONS'])
    yield case('m4','undefine-option',['-D','word=value','-U','word'],b'word\n',b'word\n',clauses=['OPTIONS'])
    yield case('m4','arithmetic-string',stdin=b"eval(2+3*4) len(`abcd') substr(`abcd',1,2) index(`abcd',`bc') translit(`abc',`ac',`XZ')\n",out=b'14 4 bc 1 XbZ\n',clauses=['EXTENDED DESCRIPTION'])
    yield case('m4','conditionals-stack',stdin=b"define(`v',`old')pushdef(`v',`new')dnl\nv\npopdef(`v')dnl\nv\nifdef(`v',`yes',`no') ifelse(`a',`a',`same',`different')\n",out=b'new\nold\nyes same\n',clauses=['EXTENDED DESCRIPTION'])
    yield case('m4','diversion',stdin=b'divert(1)one\ndivert(0)zero\nundivert(1)dnl\n',out=b'zero\none\n',clauses=['EXTENDED DESCRIPTION','STDOUT'])
    yield case('m4','include',stdin=b"include(`part')dnl\nsinclude(`missing')dnl\n",out=b'included\n',input_files={'part':b'included\n'},clauses=['EXTENDED DESCRIPTION','INPUT FILES'])
    yield case('m4','exit',stdin=b'm4exit(7)ignored\n',status=7,clauses=['EXIT STATUS'])
    yield case('m4','missing-file',['missing'],status='nonzero',err='nonempty',clauses=['CONSEQUENCES OF ERRORS','STDERR'])

    normal=b'2c2\n< old\n---\n> new\n'
    unified=b'--- data\n+++ data\n@@ -1,2 +1,2 @@\n first\n-old\n+new\n'
    context=b'*** old\n--- data\n***************\n*** 1,2 ****\n  first\n! old\n--- 1,2 ----\n  first\n! new\n'
    for name,args,delta in [('normal',['-s','data'],normal),('unified',['-s','-u','data'],unified),('context',['-s','-c','data'],context)]:
        yield case('patch',name,args,delta,input_files={'data':b'first\nold\n'},files={'data':b'first\nnew\n'},clauses=['OPTIONS','STDIN','INPUT FILES','OUTPUT FILES'])
    yield case('patch','reverse',['-s','-R','data'],normal,input_files={'data':b'first\nnew\n'},files={'data':b'first\nold\n'},clauses=['OPTIONS'])
    yield case('patch','input-output',['-s','-i','delta','-o','result','data'],input_files={'delta':normal,'data':b'first\nold\n'},files={'data':b'first\nold\n','result':b'first\nnew\n'},clauses=['OPTIONS','OUTPUT FILES'])
    yield case('patch','reject',['-s','-r','reject','data'],normal,status=1,stdout_rule='nonempty',input_files={'data':b'first\nother\n'},files={'data':b'first\nother\n'},nonempty_files=['reject'],clauses=['EXIT STATUS','CONSEQUENCES OF ERRORS'])

    helper=[sys.executable,str(Path(__file__).with_name('host_language_helper.py').resolve()),'argv']
    def vectors(*groups):
        return ''.join(json.dumps(list(g),ensure_ascii=True)+'\n' for g in groups).encode()
    yield case('xargs','quoting',['-n','3']+helper,b"one 'two words' three\\ four\n",vectors(['one','two words','three four']),clauses=['STDIN','OPTIONS'])
    yield case('xargs','batch-count',['-n','2']+helper,b'a b c d e\n',vectors(['a','b'],['c','d'],['e']),clauses=['OPTIONS'])
    yield case('xargs','logical-lines',['-L','1']+helper,b'a b\nc d\n',vectors(['a','b'],['c','d']),clauses=['OPTIONS'])
    yield case('xargs','replace',['-I','{}']+helper+['pre{}post'],b'a b\nc\n',vectors(['prea bpost'],['precpost']),clauses=['OPTIONS'])
    yield case('xargs','eof',['-E','STOP','-n','1']+helper,b'first\nSTOP\nlast\n',vectors(['first']),clauses=['OPTIONS'])
    yield case('xargs','default-echo',stdin=b'a b\n',out=b'a b\n',clauses=['OPERANDS','STDOUT'])
    yield case('xargs','trace',['-t']+helper,b'a\n',vectors(['a']),err='nonempty',clauses=['OPTIONS','STDERR'])
    yield case('xargs','missing-utility',['csh074-no-such-utility'],b'x\n',status=127,err='nonempty',clauses=['EXIT STATUS','CONSEQUENCES OF ERRORS'])
    yield case('xargs','not-executable',['./blocked'],b'x\n',status=126,err='nonempty',input_files={'blocked':b'not executable\n'},clauses=['EXIT STATUS','CONSEQUENCES OF ERRORS'])
    yield case('xargs','unmatched-quote',helper,b"'unterminated\n",status='xargs-error',err='nonempty',clauses=['STDIN','CONSEQUENCES OF ERRORS'])
    yield case('xargs','size-rejection',['-x','-s','256']+helper,b'x'*1024+b'\n',status='xargs-error',err='nonempty',clauses=['OPTIONS','CONSEQUENCES OF ERRORS'])
    for code in (1,255):
        yield case('xargs','child-exit-'+str(code),['-n','1']+helper[:-1]+['exit',str(code)],b'a\nb\n',status='xargs-error',err='nonempty' if code==255 else b'',files={'calls':b'a\n' if code==255 else b'a\nb\n'},clauses=['EXIT STATUS','CONSEQUENCES OF ERRORS'])
