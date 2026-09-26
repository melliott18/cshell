"""CSH-032 Issue 8 options: explicit outcomes, never a reference-shell oracle."""
import errno
import os

OPTIONS = ('allexport', 'notify', 'noclobber', 'errexit', 'noglob', 'hashall',
           'monitor', 'noexec', 'nounset', 'verbose', 'xtrace', 'pipefail',
           'ignoreeof', 'nolog')

def report(*enabled, reusable=False):
    return ''.join((f"set {'-' if name in enabled else '+'}o {name}\n" if reusable else
                    f"{name} {'on' if name in enabled else 'off'}\n") for name in OPTIONS)

def add_option_cases(cross, helper):
    def case(name, script, stdout='', status=0, stderr='', **kw):
        if 'files' in kw:
            kw['files'] = {k: {'type': 'absent'} if v is None else {'type': 'file', 'content': v}
                           for k, v in kw['files'].items()}
        cross('options: ' + name, script, stdout=stdout, status=status, stderr=stderr, **kw)
    case('O-001 defaults report', 'set -o\n', report())
    case('O-001 report with terminator', 'set -- old; set -o --; echo "$#"\n', report() + '0\n')
    case('O-001 reusable report', 'set +o\n', report(reusable=True))
    case('O-001 round trip', 'saved=$(set +o); set -afuhC -o pipefail -o nolog; eval "$saved"; echo "$-"; set -o\n', '\n' + report())
    case('O-001 grouped and named', 'set -afuhC; echo "$-"; set +a +o noglob +h +C; echo "$-"; set +u\n', 'aCfhu\nu\n')
    case('O-001 keep and replace positionals', 'set -- old; set -f; echo "$#:$1"; set +f new two; echo "$#:$1:$2"; set --; echo "$#"; set -- -e +x --; echo "$#:$1:$2:$3"\n', '1:old\n2:new:two\n0\n3:-e:+x:--\n')
    case('O-001 invalid option', 'set -z; echo never\n', status=1, stderr='cshell: set: invalid option\n')
    case('O-001 invalid name', 'set -o missing; echo never\n', status=1, stderr='cshell: set: invalid option\n')
    case('O-001 invalid preserves state', 'set -- old; command set -afz -- new; echo "$-:$1:$?"\n', ':old:1\n', stderr='cshell: set: invalid option\n')
    case('O-001 plus alone operand', 'set -- old; set +; echo "$1"\n', '+\n')
    case('O-002 all assignment sources', f'unset a b c d opt OPTARG OPTIND PWD OLDPWD; set -a; a=syntax; : ${{b:=expanded}}; : $((c=3)); read d <data; getopts x: opt -x arg; cd .; {helper} environment a b c d opt OPTARG OPTIND; {helper} environment PWD OLDPWD >record; {{ read current; read previous; }} <record; test "$current" = "PWD=$PWD"; test "$previous" = "OLDPWD=$OLDPWD"; echo "$?"\n', 'a=syntax\nb=expanded\nc=3\nd=read\nopt=x\nOPTARG=arg\nOPTIND=3\n0\n', setup={'data':'read\n'})
    case('O-002 disable and temporary', "set -a; a=yes; set +a; b=no; c=prefix /bin/sh -c 'echo \"$a/${b-missing}/$c\"'; /bin/sh -c 'echo \"$a/${b-missing}/${c-missing}\"'\n", 'yes/missing/prefix\nyes/missing/missing\n')
    case('O-005 plain failure', 'set -e; false; echo never\n', status=1)
    case('O-005 final AND failure', 'set -e; true && (exit 7); echo never\n', status=7)
    case('O-005 final OR failure', 'set -e; false || (exit 8); echo never\n', status=8)
    case('O-005 tested contexts', 'set -e; false && echo never; true || echo never; if false; then echo never; elif true; then echo if; fi; while false; do echo never; done; until true; do echo never; done; ! true; echo ok\n', 'if\nok\n')
    case('O-005 compound exempt status', 'set -e; { false && echo never; }; echo ok\n', 'ok\n')
    case('O-005 subshell exception', 'set -e; (false && echo never); echo never\n', status=1)
    case('O-005 function status after exempt body', 'set -e; f() { false && :; }; f; echo never\n', status=1)
    case('O-005 eval status after exempt body', 'set -e; eval "false && :"; echo never\n', status=1)
    case('O-005 dot status after exempt body', 'set -e; . ./source; echo never\n', status=1, setup={'source':'false && :\n'})
    case('O-005 loop retains body exemption', 'x=; while { set -e; test "$x" != done; }; do set +e; x=done; false; done; echo never\n', status=1)
    case('O-005 function stops', 'f() { false; echo never; }; set -e; f; echo never\n', status=1)
    case('O-005 function tested', 'f() { set -e; false; echo body; }; f && echo yes; echo after\n', 'body\nyes\nafter\n')
    case('O-005 negated function', 'set -e; f() { false; echo body; }; ! f; echo after\n', 'body\nafter\n')
    case('O-005 loop body', 'set -e; for x in one; do false; echo never; done; echo never\n', status=1)
    case('O-005 while body', 'set -e; while true; do false; echo never; done\n', status=1)
    case('O-005 case body', 'set -e; case x in x) false; echo never;; esac\n', status=1)
    case('O-005 pipeline child environment', 'set -e; (false; echo never) | cat; echo after\n', 'after\n')
    case('O-005 pipeline function child', 'set -e; f() { false; echo never; }; f | cat; echo after\n', 'after\n')
    case('O-005 negated pipeline descendants', 'set -e; ! { false; echo body; } | cat; echo after\n', 'body\nafter\n')
    case('O-005 substitution argument', 'set -e; echo "$(false; echo never)"; echo after\n', '\nafter\n')
    case('O-005 substitution assignment', 'set -e; value=$(exit 9); echo never\n', status=9)
    case('O-005 substitution tested', 'set -e; value=$(false; echo body) && echo "$value"; echo after\n', 'body\nafter\n')
    case('O-005 substitution isolated toggle', 'set -e; value=$(set +e; false; echo body); echo "$value:$-"; false; echo never\n', 'body:e\n', status=1)
    case('O-005 eval and dot exempt', "set -e; eval 'false; echo eval' || echo never; . ./source && echo after\n", 'eval\ndot\nafter\n', setup={'source':'false; echo dot\n'})
    case('O-005 eval exit', "set -e; eval 'false; echo never'; echo never\n", status=1)
    case('O-005 dot exit', 'set -e; . ./source; echo never\n', status=1, setup={'source':'false\necho never\n'})
    case('O-005 alias exit', "alias fail='false'\nset -e\nfail\necho never\n", status=1)
    case('O-013 last rightmost nonzero', 'set -o pipefail; (exit 7) | (exit 4) | true; echo "$?"; true | true; echo "$?"; ! (exit 7) | true; echo "$?"; ! true | true; echo "$?"\n', '4\n0\n0\n1\n')
    case('O-013 errexit integration', 'set -eo pipefail; (exit 7) | true; echo never\n', status=7)
    case('O-013 tested integration', 'set -eo pipefail; if false | true; then echo never; else echo if; fi; false | true && echo never; ! true | true; echo after\n', 'if\nafter\n')
    case('O-013 start snapshot', 'false | set -o pipefail; echo "$?"; set -o pipefail; false | set +o pipefail; echo "$?"; echo "$-"\n', '0\n1\n\n')
    case('O-013 background retained snapshot', 'set -o pipefail; (exit 7) | true & set +o pipefail; wait "$!"; echo "$?"; false | true & set -o pipefail; wait "$!"; echo "$?"\n', '7\n0\n')
    case('O-013 background immediate status', 'set -eo pipefail; (exit 6) | true & echo "$?"; wait "$!"; echo never\n', '0\n', status=6)
    case('O-013 negated async descendants', 'set -e; ! { false; echo body; } | cat >out & wait "$!" || :; cat out\n', 'body\n')
    case('O-012 nounset parameter', 'unset csh_absent; set -u; echo "$csh_absent"; echo never\n', status=2, stderr='cshell: csh_absent\n')
    case('O-012 nounset positional', 'set --; set -u; echo "$1"; echo never\n', status=2, stderr='cshell: 1\n')
    case('O-012 nounset arithmetic', 'unset csh_absent; set -u; echo "$((csh_absent+1))"; echo never\n', status=2, stderr='cshell: arithmetic expansion failed\n')
    case('O-012 exempt default and empty', 'unset a b; set --; set -u; echo "$@" "$*" "${a-default}" "${a+alternate}" "${b:=value}"; a=; echo "${a}:${#a}:$b"\n', ' default  value\n:0:value\n')
    case('O-012 contexts', 'unset absent; set -u; if echo "$absent"; then echo never; fi; echo never\n', status=2, stderr='cshell: absent\n')
    case('O-012 here document', 'unset absent; set -u; cat <<EOF\n$absent\nEOF\necho never\n', status=2, stderr='cshell: absent\n')
    case('O-012 glob and case errors', 'unset absent; set -u; case "$absent" in *) echo never;; esac\n', status=2, stderr='cshell: absent\n')
    case('O-006 splitting still active', 'pattern="*.txt *.missing"; set -f; printf "<%s>\\n" $pattern; set +f; printf "<%s>\\n" $pattern\n', '<*.txt>\n<*.missing>\n<a.txt>\n<b.txt>\n<*.missing>\n', setup={'a.txt':'','b.txt':''})
    case('O-006 patterns still active', 'set -f; case foo in f*) echo yes;; esac; a=food; echo "${a%od}"\n', 'yes\nfo\n')
    denied = 'cshell: cannot apply redirection: ' + os.strerror(errno.EEXIST) + '\n'
    case('O-004 refuse and override', 'set -C; echo bad >out; echo "$?"; cat out; echo good >|out; echo more >>out; cat out\n', '1\nold\ngood\nmore\n', stderr=denied, setup={'out':'old\n'}, files={'out':'good\nmore\n'})
    case('O-004 special builtin fatal', 'set -C; : >out; echo never\n', status=1, stderr=denied, setup={'out':'old\n'}, files={'out':'old\n'})
    case('O-004 create and dev null', 'set -C; echo new >out; echo discarded >/dev/null; cat out\n', 'new\n', files={'out':'new\n'})
    case('O-004 symlink and dangling', 'ln -s out link; ln -s absent dangling; set -C; echo bad >link; echo "$?"; echo bad >dangling; echo "$?"; cat out\n', '1\n1\nold\n', stderr=denied+'cshell: cannot apply redirection: '+os.strerror(errno.ENOENT)+'\n', setup={'out':'old\n'}, files={'out':'old\n','absent':None})
    case('O-004 ordered redirects', 'set -C; echo bad 2>error >out; echo after\n', 'after\n', setup={'out':'old\n'}, files={'out':'old\n','error':denied})
    case('O-004 concurrent exclusive creation', 'set -C; for x in 1 2 3 4 5 6 7 8; do (echo winner >race && echo success >>wins) 2>/dev/null & done; wait; cat race wins\n', 'winner\nsuccess\n', files={'race':'winner\n','wins':'success\n'})
    case('O-004 fifo is writable', 'mkfifo fifo; cat <fifo >out & set -C; echo payload >fifo; wait; cat out\n', 'payload\n', files={'out':'payload\n'})
    case('O-009 loop activation', 'while true; do set -n; echo never; done; echo never\n')
    case('O-009 condition activation', 'while set -n; do echo never; done; echo never\n')
    case('O-009 async activation', 'set -n; echo never >out & wait\n', files={'out':None})
    case('O-009 eval continues parsing', "eval 'set -n\nif'\n", status=2, stderr='cshell: unterminated command group\n')
    case('O-009 no effects on same line', 'set -n; echo never >out; value=$(touch other); set +n; echo never\n', files={'out':None,'other':None})
    case('O-009 still parses later input', 'set -n\necho never >out\nif\n', status=2, stderr='cshell: @SOURCE@: 3:1: unterminated command group\n', files={'out':None})
    case('O-009 eval no effects', "eval 'set -n; echo never >out'; echo never\n", files={'out':None})
    case('O-009 child isolation', '(set -n; echo never >out); echo after\n', 'after\n', files={'out':None})
    case('O-014 input timing alias eval dot', "set -v\n# comment\nalias say='echo alias'\nsay\neval 'echo eval'\n. ./source\nset +v\necho after\n", 'alias\neval\ndot\nafter\n', stderr="# comment\nalias say='echo alias'\nsay\neval 'echo eval'\necho eval. ./source\necho dot\nset +v\n", setup={'source':'echo dot\n'})
    case('O-016 closed trace descriptor', 'set -x; : 2>&-\n')
    case('O-001 report both descriptors closed', 'set -o >&- 2>&-\n', status=1)
    case('O-016 expanded trace', "PS4='trace:${tag-T}> '; set -x; a='two words'; echo \"$a\" >out\n", stderr="trace:T> a='two words'\ntrace:T> echo 'two words'\n", files={'out':'two words\n'})
    case('O-016 stderr destination', 'set -x; echo yes 2>trace\n', 'yes\n', files={'trace':'+ echo yes\n'})
    case('O-016 substitution trace', 'set -x; echo "$(echo nested)"\n', 'nested\n', stderr='+ echo nested\n+ echo nested\n')
    case('O-016 eval alias trace', "alias say='echo alias'\nset -x\neval say\n", 'alias\n', stderr='+ eval say\n+ echo alias\n')
    case('O-017 function shares options', 'f() { set -f; }; f; echo "$-"; (set +f; echo "$-"); echo "$-"; v=$(set +f; echo "$-"); echo "$v:$-"\n', 'f\n\nf\n:f\n')
    case('O-017 eval dot alias state', "alias enable='set -f'\neval enable\necho \"$-\"\n. ./source\necho \"$-\"\n", 'f\n\n', setup={'source':'set +f\n'})
    case('O-007 hashall and O-011 nolog', 'set -h -o nolog; hash echo; echo one; set +h +o nolog; echo two\n', 'one\ntwo\n')

    case('O-002 loop and child assignments', f'unset item child; set -a; for item in value; do :; done; ({helper} environment item; child=local; {helper} environment child); {helper} environment child\n', 'item=value\nchild=local\nchild=<unset>\n')
    case('O-005 until body fails', 'set -e; until false; do false; echo never; done; echo never\n', status=1)
    case('O-005 elif and loop tested functions', 'set -e; f() { false; echo tested; }; if false; then :; elif f; then echo elif; fi; while f && false; do echo never; done; until f; do echo never; done; echo after\n', 'tested\nelif\ntested\ntested\nafter\n')
    case('O-005 last substitution status succeeds', 'set -e; a=$(exit 7) b=$(true); echo after\n', 'after\n')
    case('O-005 last substitution status fails', 'set -e; a=$(true) b=$(exit 7); echo never\n', status=7)
    case('O-006 other expansion stages', 'HOME=/chosen; set -f; value="*.txt two"; printf "<%s>\\n" ~ "$((1+2))" "$(echo four)" $value "$value"\n', '</chosen>\n' + '<3>\n<four>\n<*.txt>\n<two>\n<*.txt two>\n', setup={'a.txt':''})
    case('O-012 braced positional exemptions', 'set --; set -u; printf "<%s>\\n" ${@} ${*} "${@}" "${*}"\n', '<>\n')
    case('O-012 unset length', 'unset absent; set -u; echo "${#absent}"; echo never\n', status=2, stderr='cshell: absent\n')
    case('O-012 unset pattern removal', 'unset absent; set -u; echo "${absent%pattern}"; echo never\n', status=2, stderr='cshell: absent\n')
    case('O-012 subshell error stays local', 'unset absent; set -u; (echo "$absent"; echo never); echo "$?:after"\n', '2:after\n', stderr='cshell: absent\n')
    case('O-012 substitution error stays local', 'unset absent; set -u; value=$(echo "$absent"; echo never); echo "$?:after:$value"\n', '2:after:\n', stderr='cshell: substitution: absent\n')
    case('O-014 physical continuations and heredoc', 'set -v\necho one\\\ntwo\ncat <<EOF\n$((1+2))\nEOF\n', 'onetwo\n3\n', stderr='echo one\\\ntwo\ncat <<EOF\n$((1+2))\nEOF\n')
    case('O-014 noexec still reads', 'set -vn\necho never >out\n', stderr='echo never >out\n', files={'out':None})
    case('O-016 trace precedes execution', 'set -x; echo "$((1+1))" >&2\n', stderr='+ echo 2\n2\n')
    case('O-016 PS4 expansions', "tag=T; PS4='$(printf p)$((1+1)):${tag}> '; set -x; echo value\n", 'value\n', stderr='p2:T> echo value\n')
    case('O-016 disabling has no later trace', 'set -x; set +x 2>/dev/null; echo after\n', 'after\n')


def invocation_cases():
    cases = []
    def add(name, args, stdin='', stdout='', stderr='', status=0, setup=None):
        cases.append(dict(name='options: invocation '+name, args=args, stdin=stdin,
                          setup=setup or {}, expect=dict(stdout=stdout, stderr=stderr, status=status)))
    for mode in ('string', 'file', 'stdin'):
        script = 'printf "%s:%s:%s\\n" "$-" "$1" "$2"\n'
        args = ['-afuhC', '+a', '+o', 'nounset', '-o', 'pipefail', '+h']
        args += ['-c', script, 'name', 'one', 'two'] if mode == 'string' else ['script','one','two'] if mode == 'file' else ['-s','--','one','two']
        add('mapping '+mode, args, stdin=script if mode == 'stdin' else '',
            setup={'script':script} if mode == 'file' else {}, stdout='Cf:one:two\n')
    add('errexit', ['-ec','exit 7; echo never'], status=7)
    add('errexit disabled', ['-e','+e','-c','false; echo after'], stdout='after\n')
    add('notify retained', ['-b','-c','echo "$-"'], stdout='b\n')
    add('noexec', ['-nc','echo never >out; value=$(echo never); exit 7'])
    add('verbose', ['-vc','# comment\necho yes'], stdout='yes\n', stderr='# comment\necho yes')
    add('xtrace', ['-xc','echo yes'], stdout='yes\n', stderr='+ echo yes\n')
    add('named attached', ['-ofnoglob','-c',':'], status=2, stderr='cshell: -ofnoglob: unsupported shell option\n')
    add('named valid attached', ['-onoglob','-c','echo "$-"'], stdout='f\n')
    add('missing name', ['-o'], status=2, stderr='cshell: -o: -o requires an option name\n')
    add('bad named', ['+o','missing','-c',':'], status=2, stderr='cshell: missing: unsupported shell option\n')
    add('unsupported vi profile', ['-o','vi','-c',':'], status=2, stderr='cshell: vi: unsupported shell option\n')
    add('unavailable monitor', ['-mc',':'], status=2, stderr='cshell: job control unavailable\n')
    add('double dash source', ['--','-script'], setup={'-script':'echo ok\n'}, stdout='ok\n')
    add('double dash command', ['-c','--','echo "$0:$1"','name','-e'], stdout='name:-e\n')
    add('interactive error atomicity', ['-ic','set -- old; set -afz -- new; echo "$-:$1"'], stdout='i:old\n', stderr='cshell: set: invalid option\n')
    return cases
