/* CSH-070 selected base-profile policy: every argument is literal, including
 * -n, -e, -E and backslashes. No XSI escape interpretation is selected. */
#include <locale.h>
#include <nl_types.h>
#include <stdio.h>

int main(int argc, char **argv)
{
    int index, status = 0;
    nl_catd messages;
    (void)setlocale(LC_ALL, "");
    messages = catopen("cshell-echo", NL_CAT_LOCALE);
    for (index = 1; index < argc; index++) {
        if (index > 1) putchar(' ');
        fputs(argv[index], stdout);
    }
    putchar('\n');
    if (fflush(stdout) == EOF || ferror(stdout)) {
        fputs(catgets(messages, 1, 11, "echo: write error\n"), stderr);
        status = 1;
    }
    if (messages != (nl_catd)-1) (void)catclose(messages);
    return status;
}
