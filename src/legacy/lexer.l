%option noyywrap noinput nounput

%{
    #include "cshell/legacy.h"

    static char *_args[1024];
    static unsigned _argcount = 0;
    static int _bufpos = 0;
    static int _ypos = 0;
    static char _linebuf[4096];
%}

WORD    [a-zA-Z_0-9\/\.-]+
SPECIAL [()><|&;*]+
QUOTE   (\'[^\']*\')|(\"[^\"]*\")

%%
	_argcount = 0; _bufpos = 0; _args[0] = NULL;

{WORD}|{SPECIAL}|{QUOTE}	{
    if (_argcount < (unsigned)(sizeof (_args) / sizeof (_args[0])) - 1) {
        _args[_argcount++] = _linebuf + _bufpos;
        _args[_argcount] = NULL;
        for (_ypos = 0; yytext[_ypos] != '\0'; _ypos++) {
            _linebuf[_bufpos++] = yytext[_ypos];
        }
        _linebuf[_bufpos++] = '\0';
    }
}

\n	return 1;

[ \t]+

.

%%

char **legacy_read_args(void)
{
    yylex();
    return _args;
}

