"""Additional Issue-8 grammar, state and operand contracts with authored oracles."""
BASE = 'https://pubs.opengroup.org/onlinepubs/9799919799/utilities/'


def cases():
    def case(tool, name, args=(), stdin=b'', out=b'', clauses=(), **kw):
        return dict(id=tool+'/coverage-'+name, utility=tool, args=list(args),
                    stdin=stdin, stdout=out, stderr=b'', status=0,
                    source=BASE+tool+'.html', clauses=list(clauses), **kw)

    bc = [
        ('array-value-parameter', b'define f(a[]) {\na[0]=9\nreturn(a[0])\n}\na[0]=3\nf(a[])\na[0]\n', b'9\n3\n'),
        ('identifier-namespaces', b'a=2\na[0]=3\ndefine a(x) {\nreturn(x+1)\n}\na+a[0]+a(4)\n', b'10\n'),
        ('recursive-auto', b'define f(n) {\nauto x\nx=n\nif(n<=1) return(1)\nreturn(x*f(n-1))\n}\nf(6)\n', b'720\n'),
        ('empty-return', b'define f() {\nreturn()\n}\ndefine g() {\nauto x\nx=9\n}\nf()\ng()\n', b'0\n0\n'),
        ('array-index-truncation', b'a[2.9]=7\na[2]\na[1]\n', b'7\n0\n'),
        ('assignment-associativity', b'a=b=7\na\nb\n2^3^2\n20/2/2\n', b'7\n7\n512\n5\n'),
        ('scale-multiply', b'scale=2\n1.234*2.5\nscale(1.234*2.5)\nscale=5\n1.234*2.5\n', b'3.085\n3\n3.0850\n'),
        ('scale-sum-sqrt', b'scale=3\n1.2+2.345\n7/2\nsqrt(4)\nscale(sqrt(4))\n', b'3.545\n3.500\n2.000\n3\n'),
        ('register-truncation', b'scale=2.9\nscale\nibase=16\nA\nibase=A\n10\nobase=16\n255\n', b'2\n10\n10\nFF\n'),
        ('large-output-base', b'obase=25\n1024\nobase=125\n1024\n', b' 01 15 24\n 008 024\n'),
        ('compound-index-once', b'i=0\na[0]=4\na[i++]+=3\ni\na[0]\n', b'1\n7\n'),
        ('for-break', b'for(i=0;i<5;i++) {\nif(i==3) break\ni\n}\ni\n', b'0\n1\n2\n3\n'),
    ]
    for name, program, out in bc:
        yield case('bc', name, stdin=program, out=out,
                   clauses=['Grammar', 'Operations in bc', 'EXTENDED DESCRIPTION', 'STDOUT'])
    yield case('bc', 'files-before-stdin', ['first', 'second'], stdin=b'a\n', out=b'2\n5\n5\n',
               input_files={'first': b'a=2\na\n', 'second': b'a+=3\na\n'}, clauses=['OPERANDS', 'STDIN'])

    awk = [
        ('short-circuit', 'BEGIN {x=0; a=(0 && ++x); b=(1 || ++x); print x,a,b; c=(1 ? ++x : ++x); print c,x}', b'', b'0 0 1\n1 1\n'),
        ('scalar-value-array-reference', 'function f(x,a) {x=9; a[1]=7; return x} BEGIN {x=3; r=f(x,a); print r,x,a[1]}', b'', b'9 3 7\n'),
        ('field-growth', 'BEGIN {OFS=":"} {$4="z"; print NF,$0; NF=1; print $0}', b'a b\n', b'4:a:b::z\na\n'),
        ('paragraph-records', 'BEGIN {RS=""; FS=":"} {print NR,NF,$1,$2,$3}', b'\na:b\nc\n\nd:e\nf\n\n', b'1 3 a b c\n2 3 d e f\n'),
        ('getline-variable-counts', '{print NR,FNR,$0; r=getline x; print r,NR,FNR,x,$0}', b'one\ntwo\n', b'1 1 one\n1 2 2 two one\n'),
        ('getline-current-record', '{getline; print NR,FNR,$0,NF}', b'one\ntwo words\n', b'2 2 two words 2\n'),
    ]
    for name, program, data, out in awk:
        yield case('awk', name, [program], data, out,
                   clauses=['Expressions in awk', 'Variables and Special Variables', 'Input/Output and General Functions', 'Grammar'])
    yield case('awk', 'operand-assignment-order', ['BEGIN {print x} {print x,$0}', 'x=2', 'first', 'x=3', 'second'],
               out=b'\n2 a\n3 b\n', input_files={'first': b'a\n', 'second': b'b\n'}, clauses=['OPERANDS', 'Special Patterns'])
    yield case('awk', 'file-getline-counts', ['BEGIN {r=getline x < "data"; print r,x,NR,FNR; close("data"); getline y < "data"; print y}'],
               out=b'1 one 0 0\none\n', input_files={'data': b'one\ntwo\n'}, clauses=['Input/Output and General Functions'])

    ed = [
        ('semicolon-address', b'2;.+1p\nQ\n', b'b\nc\n'),
        ('search-wrap-reuse', b'1p\n?c?p\n//p\nQ\n', b'a\nc\nc\n'),
        ('mark-survives-move', b'2ka\n2m$\n\'ap\nQ\n', b'b\n'),
        ('global-undo-unit', b'g/[ab]/s/^/X/\n,p\nu\n,p\nQ\n', b'Xa\nXb\nc\na\nb\nc\n'),
        ('escaped-newline-replacement', b'1s/a/one\\\ntwo/\n,p\nQ\n', b'one\ntwo\nb\nc\n'),
    ]
    for name, commands, out in ed:
        yield case('ed', name, ['-s', 'data'], commands, out,
                   input_files={'data': b'a\nb\nc\n'},
                   clauses=['Addresses in ed', 'Commands in ed', 'Global Command', 'Undo Command', 'Substitute Command', 'Mark Command'])
    yield case('expr', 'stdin-unused', ['2', '+', '3'], stdin=b'not an expression\n', out=b'5\n', clauses=['STDIN', 'EXTENDED DESCRIPTION'])
